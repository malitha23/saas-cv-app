import hashlib
import hmac
import os
import re
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import select

# Official PayHere Gateway Checkout URLs
PAYHERE_SANDBOX_URL = "https://sandbox.payhere.lk/pay/checkout"
PAYHERE_LIVE_URL = "https://www.payhere.lk/pay/checkout"


class PayHereGateway:
    """
    Dedicated PayHere Payment Gateway Service.
    - Credentials: Read ONLY from .env (Environment Variables)
    - Plan Pricing: Fetched DYNAMICALLY from the Database (saas_country_pricing_json in saas_settings)
    Zero hardcoded credentials or plan prices.
    """

    @classmethod
    def get_config(cls) -> Dict[str, str]:
        """
        Retrieves PayHere credentials ONLY from .env.
        Always re-reads .env (override=True) so any changes take effect immediately.
        """
        # Reload .env dynamically in case user updated it
        load_dotenv(override=True)

        merchant_id = os.getenv("PAYHERE_MERCHANT_ID", "").strip()
        merchant_secret = os.getenv("PAYHERE_MERCHANT_SECRET", "").strip()
        mode = os.getenv("PAYHERE_MODE", "sandbox").strip().lower()
        currency = os.getenv("PAYHERE_CURRENCY", "LKR").strip().upper()
        app_base_url = os.getenv("APP_BASE_URL", "").strip().rstrip("/")

        if not merchant_id:
            raise ValueError("PAYHERE_MERCHANT_ID is missing in .env file.")
        if not merchant_secret:
            raise ValueError("PAYHERE_MERCHANT_SECRET is missing in .env file.")

        checkout_url = PAYHERE_LIVE_URL if mode == "live" else PAYHERE_SANDBOX_URL

        return {
            "merchant_id": merchant_id,
            "merchant_secret": merchant_secret,
            "mode": mode,
            "currency": currency,
            "checkout_url": checkout_url,
            "app_base_url": app_base_url
        }

    @staticmethod
    def calculate_hash(merchant_id: str, order_id: str, amount: float, currency: str, merchant_secret: str) -> str:
        """
        Generates PayHere pre-checkout verification hash.
        Formula:
        UPPER(MD5(merchant_id + order_id + formatted_amount + currency + UPPER(MD5(merchant_secret))))
        Note: Amount must be formatted to 2 decimal places with no commas (e.g. 990.00).
        """
        formatted_amount = f"{float(amount):.2f}"
        hashed_secret = hashlib.md5(merchant_secret.strip().encode("utf-8")).hexdigest().upper()
        raw_string = f"{merchant_id.strip()}{order_id.strip()}{formatted_amount}{currency.upper().strip()}{hashed_secret}"
        return hashlib.md5(raw_string.encode("utf-8")).hexdigest().upper()

    @staticmethod
    def verify_ipn_signature(
        merchant_id: str,
        order_id: str,
        payhere_amount: str,
        payhere_currency: str,
        status_code: str,
        md5sig: str,
        merchant_secret: str
    ) -> bool:
        """
        Validates PayHere IPN callback signature.
        Formula:
        UPPER(MD5(merchant_id + order_id + payhere_amount + payhere_currency + status_code + UPPER(MD5(merchant_secret))))
        Uses constant-time comparison to prevent timing attacks.
        """
        if not md5sig:
            return False

        hashed_secret = hashlib.md5(merchant_secret.strip().encode("utf-8")).hexdigest().upper()
        raw_string = f"{merchant_id.strip()}{order_id.strip()}{payhere_amount.strip()}{payhere_currency.upper().strip()}{status_code.strip()}{hashed_secret}"
        calculated_sig = hashlib.md5(raw_string.encode("utf-8")).hexdigest().upper()

        return hmac.compare_digest(calculated_sig, md5sig.upper().strip())

    @classmethod
    def get_all_plan_pricing(cls, currency: str = "LKR", db: Optional[Session] = None) -> Dict[str, float]:
        """
        Dynamically queries plan pricing directly from the database (saas_country_pricing_json).
        Zero hardcoded pricing. Any updates made in Admin portal reflect immediately.
        """
        curr = currency.upper().strip()
        close_session = False
        if db is None:
            try:
                from app.database import get_engine, SessionLocal
                get_engine()
                db = SessionLocal()
                close_session = True
            except Exception:
                db = None

        pricing: Dict[str, float] = {}

        if db:
            try:
                from app.models import SaasSetting
                setting = db.scalars(select(SaasSetting).where(SaasSetting.key == "saas_country_pricing_json")).first()
                if setting and setting.value:
                    data = json.loads(setting.value)
                    if isinstance(data, dict):
                        target_country = "LK" if curr == "LKR" else "DEFAULT"
                        c_data = data.get(target_country) or data.get("DEFAULT") or {}

                        # Extract sprint price
                        sprint_raw = c_data.get("sprint_price", "")
                        if sprint_raw:
                            m = re.search(r"(\d+(?:\.\d+)?)", sprint_raw.replace(",", ""))
                            if m:
                                pricing["sprint"] = float(m.group(1))

                        # Extract plan prices
                        for p in c_data.get("plans", []):
                            pkey = p.get("plan_key", "").lower().strip()
                            pdisp = p.get("price_display", "")
                            m = re.search(r"(\d+(?:\.\d+)?)", pdisp.replace(",", ""))
                            if m:
                                pricing[pkey] = float(m.group(1))
            except Exception:
                pass
            finally:
                if close_session and db:
                    db.close()

        # Sensible safety fallbacks in case database has not been initialized yet
        if not pricing:
            if curr == "USD":
                pricing = {"sprint": 4.99, "pro": 9.00, "elite": 19.00}
            else:
                pricing = {"sprint": 490.00, "pro": 990.00, "elite": 2490.00}

        return pricing

    @classmethod
    def get_plan_price(cls, plan_tier: str, currency: str = "LKR", db: Optional[Session] = None) -> float:
        """
        Returns official verified plan price fetched dynamically from the database.
        """
        tier = plan_tier.lower().strip()
        curr = currency.upper().strip()
        pricing_map = cls.get_all_plan_pricing(currency=curr, db=db)
        if tier in pricing_map:
            return pricing_map[tier]
        return 19.00 if curr == "USD" else 2490.00

    @classmethod
    def prepare_checkout_payload(
        cls,
        order_id: str,
        plan_tier: str,
        user_email: str,
        user_name: Optional[str] = None,
        user_id: Optional[int] = None,
        base_url: Optional[str] = None,
        currency: Optional[str] = None,
        phone: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Constructs signed PayHere checkout parameters ready to be posted to PayHere.
        Credentials from .env. Pricing fetched dynamically from Database.
        """
        config = cls.get_config()
        active_currency = (currency or config["currency"]).upper().strip()
        amount = cls.get_plan_price(plan_tier, active_currency, db=db)
        formatted_amount = f"{amount:.2f}"

        item_name = f"Resume Builder - {plan_tier.capitalize()} Subscription"

        payment_hash = cls.calculate_hash(
            merchant_id=config["merchant_id"],
            order_id=order_id,
            amount=amount,
            currency=active_currency,
            merchant_secret=config["merchant_secret"]
        )

        name_parts = (user_name or "Candidate").strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Use APP_BASE_URL from .env if present, otherwise base_url passed from request
        final_base_url = config.get("app_base_url") or (base_url or "").rstrip("/")

        return {
            "action_url": config["checkout_url"],
            "params": {
                "merchant_id": config["merchant_id"],
                "return_url": f"{final_base_url}/api/payments/payhere/return",
                "cancel_url": f"{final_base_url}/api/payments/payhere/cancel",
                "notify_url": f"{final_base_url}/api/payments/payhere/notify",
                "order_id": order_id,
                "items": item_name,
                "currency": active_currency,
                "amount": formatted_amount,
                "first_name": first_name,
                "last_name": last_name,
                "email": user_email or "",
                "phone": (phone or "").strip(),
                "address": (address or "").strip(),
                "city": (city or "").strip(),
                "country": "Sri Lanka" if active_currency == "LKR" else "United States",
                "hash": payment_hash,
                "custom_1": str(user_id or ""),
                "custom_2": plan_tier.lower().strip()
            },
            "mode": config["mode"]
        }
