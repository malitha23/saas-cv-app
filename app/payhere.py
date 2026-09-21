import hashlib
import hmac
import os
import re
import json
import base64
import time
from typing import Dict, Any, Optional
import httpx
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import select

# Official PayHere Gateway Checkout URLs
PAYHERE_SANDBOX_URL = "https://sandbox.payhere.lk/pay/checkout"
PAYHERE_LIVE_URL = "https://www.payhere.lk/pay/checkout"

# Official PayHere Merchant API Endpoints (OAuth 2.0 & Refund)
PAYHERE_OAUTH_SANDBOX_URL = "https://sandbox.payhere.lk/merchant/v1/oauth/token"
PAYHERE_OAUTH_LIVE_URL = "https://www.payhere.lk/merchant/v1/oauth/token"
PAYHERE_REFUND_SANDBOX_URL = "https://sandbox.payhere.lk/merchant/v1/payment/refund"
PAYHERE_REFUND_LIVE_URL = "https://www.payhere.lk/merchant/v1/payment/refund"
PAYHERE_SEARCH_SANDBOX_URL = "https://sandbox.payhere.lk/merchant/v1/payment/search"
PAYHERE_SEARCH_LIVE_URL = "https://www.payhere.lk/merchant/v1/payment/search"
PAYHERE_SUBSCRIPTION_SANDBOX_URL = "https://sandbox.payhere.lk/merchant/v1/subscription"
PAYHERE_SUBSCRIPTION_LIVE_URL = "https://www.payhere.lk/merchant/v1/subscription"


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

    @classmethod
    def get_base_url(cls, fallback: str = "http://localhost:8000") -> str:
        """Retrieves base URL from .env (APP_BASE_URL) or fallback."""
        load_dotenv(override=True)
        return (os.getenv("APP_BASE_URL", "").strip() or fallback).rstrip("/")

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
    def get_billing_discounts(cls, db: Optional[Session] = None) -> Dict[str, Any]:
        """
        Retrieves configurable multi-duration discounts from saas_settings.
        """
        default_discounts = {
            "3m": {"discount_percent": 15, "badge": "Save 15%"},
            "6m": {"discount_percent": 25, "badge": "Save 25%"},
            "12m": {"discount_percent": 40, "badge": "Save 40% • Best Value"},
            "lifetime": {
                "pro_price_lkr": 14900.0,
                "elite_price_lkr": 24900.0,
                "pro_price_usd": 149.0,
                "elite_price_usd": 249.0,
                "badge": "Forever Access • 0 Renewals"
            }
        }
        close_session = False
        if db is None:
            try:
                from app.database import get_engine, SessionLocal
                get_engine()
                db = SessionLocal()
                close_session = True
            except Exception:
                db = None

        if db:
            try:
                from app.models import SaasSetting
                setting = db.scalars(select(SaasSetting).where(SaasSetting.key == "billing_discounts_json")).first()
                if setting and setting.value:
                    data = json.loads(setting.value)
                    if isinstance(data, dict):
                        return data
            except Exception:
                pass
            finally:
                if close_session and db:
                    db.close()

        return default_discounts

    @classmethod
    def get_plan_price(
        cls,
        plan_tier: str,
        currency: str = "LKR",
        billing_cycle: str = "1m",
        db: Optional[Session] = None
    ) -> float:
        """
        Returns official verified plan price dynamically calculated from base database pricing,
        duration multiplier, and active discount percentages.
        """
        tier = plan_tier.lower().strip()
        curr = currency.upper().strip()
        cycle = (billing_cycle or "1m").lower().strip()

        pricing_map = cls.get_all_plan_pricing(currency=curr, db=db)
        base_monthly = pricing_map.get(tier, 19.00 if curr == "USD" else 2490.00)

        # Sprint is always a 7-day pass
        if tier == "sprint":
            return pricing_map.get("sprint", 4.99 if curr == "USD" else 490.00)

        # 1 Month standard price
        if cycle == "1m":
            return base_monthly

        discounts = cls.get_billing_discounts(db=db)

        if cycle == "3m":
            pct = float(discounts.get("3m", {}).get("discount_percent", 15))
            return round(base_monthly * 3.0 * (1.0 - (pct / 100.0)), 2)

        if cycle == "6m":
            pct = float(discounts.get("6m", {}).get("discount_percent", 25))
            return round(base_monthly * 6.0 * (1.0 - (pct / 100.0)), 2)

        if cycle == "12m":
            pct = float(discounts.get("12m", {}).get("discount_percent", 40))
            return round(base_monthly * 12.0 * (1.0 - (pct / 100.0)), 2)

        if cycle == "lifetime":
            lt = discounts.get("lifetime", {})
            if curr == "USD":
                return float(lt.get(f"{tier}_price_usd", 149.0 if tier == "pro" else 249.0))
            else:
                return float(lt.get(f"{tier}_price_lkr", 14900.0 if tier == "pro" else 24900.0))

        return base_monthly

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
        billing_cycle: str = "1m",
        phone: Optional[str] = None,
        address: Optional[str] = None,
        city: Optional[str] = None,
        amount_override: Optional[float] = None,
        db: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Constructs signed PayHere checkout parameters ready to be posted to PayHere.
        Credentials from .env. Pricing fetched dynamically from Database with billing cycle discounts.
        """
        config = cls.get_config()
        active_currency = (currency or config["currency"]).upper().strip()
        cycle = (billing_cycle or "1m").lower().strip()
        if amount_override is not None and amount_override > 0:
            amount = round(float(amount_override), 2)
        else:
            amount = cls.get_plan_price(plan_tier, active_currency, billing_cycle=cycle, db=db)
        formatted_amount = f"{amount:.2f}"

        cycle_labels = {
            "1m": "1 Month",
            "3m": "3 Months Pass",
            "6m": "6 Months Pass",
            "12m": "1 Year Access",
            "lifetime": "Lifetime Pass"
        }
        cycle_name = cycle_labels.get(cycle, "1 Month")
        item_name = f"Resume Builder - {plan_tier.capitalize()} ({cycle_name})"

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
                "custom_2": plan_tier.lower().strip(),
                "custom_3": cycle
            },
            "mode": config["mode"]
        }

    # In-memory OAuth2 Token Cache with Expiry Buffer
    _cached_token: Optional[str] = None
    _token_expires_at: float = 0.0

    @classmethod
    def get_oauth_config(cls) -> Dict[str, str]:
        """
        Retrieves PayHere App ID and Secret strictly from .env for Merchant APIs.
        """
        load_dotenv(override=True)
        app_id = os.getenv("PAYHERE_APP_ID", "").strip()
        app_secret = os.getenv("PAYHERE_APP_SECRET", "").strip()
        mode = os.getenv("PAYHERE_MODE", "sandbox").strip().lower()

        if not app_id or not app_secret:
            raise ValueError(
                "PAYHERE_APP_ID or PAYHERE_APP_SECRET is missing in .env. "
                "Please generate an API Key in your PayHere account under Settings -> API Keys "
                "(with 'Automated Charging API' permission) and add PAYHERE_APP_ID and PAYHERE_APP_SECRET to .env."
            )

        token_url = PAYHERE_OAUTH_LIVE_URL if mode == "live" else PAYHERE_OAUTH_SANDBOX_URL
        refund_url = PAYHERE_REFUND_LIVE_URL if mode == "live" else PAYHERE_REFUND_SANDBOX_URL

        return {
            "app_id": app_id,
            "app_secret": app_secret,
            "mode": mode,
            "token_url": token_url,
            "refund_url": refund_url
        }

    @classmethod
    def get_access_token(cls, force_refresh: bool = False) -> str:
        """
        Retrieves a valid OAuth 2.0 Bearer Access Token from PayHere.
        Implements in-memory token caching with an expiry buffer to prevent rate-limit throttling (max 20 req / 10s).
        """
        now = time.time()
        # Return cached token if valid for at least another 60 seconds
        if not force_refresh and cls._cached_token and now < (cls._token_expires_at - 60):
            return cls._cached_token

        cfg = cls.get_oauth_config()
        app_id = cfg["app_id"]
        app_secret = cfg["app_secret"]

        # Basic Auth: Base64(AppID:AppSecret)
        raw_cred = f"{app_id}:{app_secret}"
        encoded_cred = base64.b64encode(raw_cred.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {encoded_cred}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}

        with httpx.Client(timeout=15.0) as client:
            resp = client.post(cfg["token_url"], headers=headers, data=data)

        if resp.status_code != 200:
            error_body = resp.text
            raise RuntimeError(f"PayHere OAuth Authentication failed (HTTP {resp.status_code}): {error_body}")

        token_data = resp.json()
        token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 599)

        if not token:
            raise RuntimeError(f"No access_token returned by PayHere: {token_data}")

        cls._cached_token = token
        cls._token_expires_at = now + float(expires_in)
        return token

    @classmethod
    def process_refund(
        cls,
        payment_id: str,
        description: str,
        amount: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes a monetary refund via PayHere's official RESTful Refund API.
        Secured with OAuth Bearer Token and automatic 401 retry.
        """
        cfg = cls.get_oauth_config()
        token = cls.get_access_token()

        payload: Dict[str, Any] = {
            "payment_id": str(payment_id).strip(),
            "description": description.strip()
        }
        if amount is not None and amount > 0:
            payload["amount"] = f"{amount:.2f}"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        with httpx.Client(timeout=20.0) as client:
            resp = client.post(cfg["refund_url"], headers=headers, json=payload)

            # If token expired unexpectedly, refresh once and retry
            if resp.status_code == 401:
                new_token = cls.get_access_token(force_refresh=True)
                headers["Authorization"] = f"Bearer {new_token}"
                resp = client.post(cfg["refund_url"], headers=headers, json=payload)

        try:
            res_data = resp.json()
        except Exception:
            raise RuntimeError(f"Invalid non-JSON response from PayHere refund endpoint (HTTP {resp.status_code}): {resp.text}")

        # PayHere returns status: 1 for success, 0 or -1 or -2 for failure
        status_code = res_data.get("status")
        msg = res_data.get("msg", "Error processing refund")
        refund_id = res_data.get("data")

        if status_code == 1:
            return {
                "success": True,
                "refund_id": str(refund_id or ""),
                "msg": msg or "Successfully processed the refund"
            }
        else:
            return {
                "success": False,
                "refund_id": None,
                "msg": f"PayHere Refund Error ({status_code}): {msg}"
            }

    @classmethod
    def retrieve_order_payment(cls, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Queries PayHere's official Retrieval API to verify real-time payment status.
        Protects against dropped/delayed webhooks and provides zero-delay verification.
        """
        try:
            cfg = cls.get_oauth_config()
            token = cls.get_access_token()
            search_url = PAYHERE_SEARCH_LIVE_URL if cfg["mode"] == "live" else PAYHERE_SEARCH_SANDBOX_URL
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            with httpx.Client(timeout=15.0) as client:
                resp = client.get(f"{search_url}?order_id={order_id.strip()}", headers=headers)
                if resp.status_code == 401:
                    new_token = cls.get_access_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {new_token}"
                    resp = client.get(f"{search_url}?order_id={order_id.strip()}", headers=headers)

            if resp.status_code != 200:
                return None

            data = resp.json()
            if data.get("status") == 1 and data.get("data") and len(data["data"]) > 0:
                # Return the latest payment entry for this order_id
                return data["data"][0]
            return None
        except Exception as e:
            logger.warning("Error querying PayHere Retrieval API for order %s: %s", order_id, str(e))
            return None

    # ═══════════════════════════════════════════════════════════════════
    # PAYHERE SUBSCRIPTION MANAGER API (RECURRING SUBSCRIPTIONS)
    # ═══════════════════════════════════════════════════════════════════

    @classmethod
    def get_subscription_endpoint(cls) -> str:
        cfg = cls.get_oauth_config()
        return PAYHERE_SUBSCRIPTION_LIVE_URL if cfg["mode"] == "live" else PAYHERE_SUBSCRIPTION_SANDBOX_URL

    @classmethod
    def list_subscriptions(cls) -> Dict[str, Any]:
        """
        Retrieves all recurring subscriptions from PayHere Subscription Manager API.
        """
        try:
            token = cls.get_access_token()
            url = cls.get_subscription_endpoint()
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 401:
                    new_token = cls.get_access_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {new_token}"
                    resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                return {"status": -1, "msg": f"HTTP {resp.status_code}: {resp.text}", "data": []}
            return resp.json()
        except Exception as e:
            logger.error("Error listing PayHere subscriptions: %s", str(e))
            return {"status": -1, "msg": f"Failed to connect to Subscription Manager: {str(e)}", "data": []}

    @classmethod
    def get_subscription(cls, subscription_id: str) -> Dict[str, Any]:
        """
        Retrieves details for a single PayHere recurring subscription.
        """
        try:
            token = cls.get_access_token()
            url = f"{cls.get_subscription_endpoint()}/{subscription_id.strip()}"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 401:
                    new_token = cls.get_access_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {new_token}"
                    resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                return {"status": -1, "msg": f"HTTP {resp.status_code}: {resp.text}", "data": None}
            return resp.json()
        except Exception as e:
            return {"status": -1, "msg": str(e), "data": None}

    @classmethod
    def get_subscription_payments(cls, subscription_id: str) -> Dict[str, Any]:
        """
        Retrieves payments audit log for a specific PayHere recurring subscription.
        """
        try:
            token = cls.get_access_token()
            url = f"{cls.get_subscription_endpoint()}/{subscription_id.strip()}/payments"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            with httpx.Client(timeout=20.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 401:
                    new_token = cls.get_access_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {new_token}"
                    resp = client.get(url, headers=headers)
            if resp.status_code != 200:
                return {"status": -1, "msg": f"HTTP {resp.status_code}: {resp.text}", "data": []}
            return resp.json()
        except Exception as e:
            return {"status": -1, "msg": str(e), "data": []}

    @classmethod
    def retry_subscription(cls, subscription_id: str) -> Dict[str, Any]:
        """
        Retries charging a failed subscription via PayHere Subscription Manager API.
        """
        try:
            token = cls.get_access_token()
            url = f"{cls.get_subscription_endpoint()}/retry"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            sub_val = int(subscription_id) if subscription_id.strip().isdigit() else subscription_id.strip()
            payload = {"subscription_id": sub_val}
            with httpx.Client(timeout=25.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 401:
                    new_token = cls.get_access_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {new_token}"
                    resp = client.post(url, headers=headers, json=payload)
            return resp.json()
        except Exception as e:
            return {"status": -1, "msg": f"Failed to retry subscription: {str(e)}", "data": None}

    @classmethod
    def cancel_subscription(cls, subscription_id: str) -> Dict[str, Any]:
        """
        Cancels an active recurring subscription via PayHere Subscription Manager API.
        """
        try:
            token = cls.get_access_token()
            url = f"{cls.get_subscription_endpoint()}/cancel"
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            sub_val = int(subscription_id) if subscription_id.strip().isdigit() else subscription_id.strip()
            payload = {"subscription_id": sub_val}
            with httpx.Client(timeout=25.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 401:
                    new_token = cls.get_access_token(force_refresh=True)
                    headers["Authorization"] = f"Bearer {new_token}"
                    resp = client.post(url, headers=headers, json=payload)
            return resp.json()
        except Exception as e:
            return {"status": -1, "msg": f"Failed to cancel subscription: {str(e)}", "data": None}


