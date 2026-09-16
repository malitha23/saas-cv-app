import os
import uuid
import time
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Form, File, UploadFile, Response, BackgroundTasks, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta
from app.database import get_db
from app.models import User, BankPaymentSlip, OnlinePaymentOrder
from app.schemas import (
    SubscriptionUpgradeRequest, SubscriptionStatusResponse, UserResponse,
    PayHereInitiateRequest, PayHereInitiateResponse, CheckoutRequest,
    PlansConfigResponse, CountryPricingResponse, PlanItemConfig,
    UserRefundRequest
)
from app.auth import (
    get_current_user, check_and_update_subscription, get_saas_setting,
    DEFAULT_FREE_DAILY_AI_LIMIT, DEFAULT_FREE_DAILY_PDF_LIMIT
)
from app.state import build_user_response
from app.pricing import DEFAULT_COUNTRY_PRICING_DATA, DEFAULT_PLANS_CONFIG_DATA, _get_country_pricing_dict
from app.payhere import PayHereGateway
from app.email_service import (
    send_user_subscription_confirmed, send_admin_subscription_alert,
    send_admin_chargeback_alert, send_admin_user_refund_request
)

logger = logging.getLogger("dreemfolio.payments")

router = APIRouter(tags=["Payments & Subscriptions"])


@router.post("/api/subscription/upgrade", response_model=UserResponse)
async def upgrade_subscription(
    req: SubscriptionUpgradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cryptographically secure subscription upgrade endpoint.
    Activates Pro, Elite, or Sprint Pass, updates database quotas, validity days, and returns updated user profile.
    """
    tier = req.plan_tier.lower()
    if tier not in ["pro", "elite", "sprint"]:
        raise HTTPException(status_code=400, detail="Invalid plan tier. Allowed options: 'pro', 'elite', 'sprint'.")

    now = datetime.utcnow()

    if tier == "sprint":
        days = 7
        actual_tier = "pro"  # Sprint Pass activates Pro features for 7 calendar days
    else:
        months = max(1, min(req.duration_months, 12))
        days = months * 30
        actual_tier = tier

    current_user.plan_tier = actual_tier
    current_user.subscription_status = "active"
    current_user.subscription_started_at = now
    current_user.subscription_expires_at = now + timedelta(days=days)
    db.commit()
    db.refresh(current_user)

    return build_user_response(current_user, db)


@router.get("/api/subscription/status", response_model=SubscriptionStatusResponse)
async def get_subscription_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Return detailed subscription quota, validity days remaining, and expiration status."""
    check_and_update_subscription(current_user, db)
    u_resp = build_user_response(current_user, db)

    tier = current_user.plan_tier or "free"
    ai_limit_str = get_saas_setting(db, "free_daily_ai_limit", str(DEFAULT_FREE_DAILY_AI_LIMIT))
    try:
        ai_limit = int(ai_limit_str)
    except ValueError:
        ai_limit = DEFAULT_FREE_DAILY_AI_LIMIT

    pdf_limit_str = get_saas_setting(db, "free_daily_pdf_limit", str(DEFAULT_FREE_DAILY_PDF_LIMIT))
    try:
        pdf_limit = int(pdf_limit_str)
    except ValueError:
        pdf_limit = DEFAULT_FREE_DAILY_PDF_LIMIT

    features = {
        "ai_tailoring": "Unlimited" if tier in ["pro", "elite"] else f"{ai_limit} runs/day",
        "ats_pdf_download": "Unlimited" if tier in ["pro", "elite"] else f"{pdf_limit} ATS PDF/day",
        "visual_cv_formats": ["classic", "indigo_banner", "emerald_prestige", "tech_noir"] if tier in ["pro", "elite"] else ["classic"],
        "cloud_autosave": tier in ["pro", "elite"],
        "ai_cover_letter": tier in ["pro", "elite"],
        "portfolio_themes": 8 if tier == "elite" else (1 if tier in ["pro", "sprint"] else 0),
        "custom_domain_support": tier == "elite",
        "code_export": tier == "elite",
        "job_hunter": "Unlimited" if tier in ["pro", "elite"] else "Basic (4 vacancies)",
        "application_copilot": "Unlimited" if tier in ["pro", "elite"] else "1 Free Kit / day",
        "job_tracker": "Unlimited" if tier in ["pro", "elite"] else "Up to 3 Jobs",
        "career_copilot_chat": "Unlimited 24/7" if tier in ["pro", "elite"] else "3 Messages / day",
        "voice_mock_interview": "Unlimited Full Studio" if tier in ["pro", "elite"] else "1 Practice Session / day"
    }

    return SubscriptionStatusResponse(
        plan_tier=tier,
        subscription_status=u_resp.subscription_status,
        is_active=current_user.is_active,
        subscription_started_at=u_resp.subscription_started_at,
        subscription_expires_at=u_resp.subscription_expires_at,
        subscription_days_remaining=u_resp.subscription_days_remaining,
        subscription_validity_label=u_resp.subscription_validity_label,
        daily_ai_generations_count=u_resp.daily_ai_generations_count,
        daily_generations_limit=None if tier in ["pro", "elite"] else ai_limit,
        daily_generations_remaining=u_resp.daily_generations_remaining,
        daily_pdf_downloads_count=u_resp.daily_pdf_downloads_count,
        daily_pdf_downloads_limit=None if tier in ["pro", "elite"] else pdf_limit,
        daily_pdf_downloads_remaining=u_resp.daily_pdf_downloads_remaining,
        lifetime_ats_downloads_count=u_resp.lifetime_ats_downloads_count,
        lifetime_ats_downloads_limit=None if tier in ["pro", "elite"] else 2,
        lifetime_ats_downloads_remaining=u_resp.lifetime_ats_downloads_remaining,
        lifetime_visual_downloads_count=u_resp.lifetime_visual_downloads_count,
        lifetime_visual_downloads_limit=None if tier in ["pro", "elite"] else 1,
        lifetime_visual_downloads_remaining=u_resp.lifetime_visual_downloads_remaining,
        lifetime_cover_letter_downloads_count=u_resp.lifetime_cover_letter_downloads_count,
        lifetime_cover_letter_downloads_limit=None if tier in ["pro", "elite"] else 3,
        lifetime_cover_letter_downloads_remaining=u_resp.lifetime_cover_letter_downloads_remaining,
        has_pending_order=u_resp.has_pending_order,
        pending_order=u_resp.pending_order,
        has_pending_slip=u_resp.has_pending_slip,
        features=features
    )


@router.get("/api/payments/bank-transfer/config")
async def get_bank_transfer_config(db: Session = Depends(get_db)):
    """Return configured bank account details and instructions for direct deposit."""
    enabled_val = get_saas_setting(db, "bank_transfer_enabled", "true")
    return {
        "enabled": enabled_val.lower() in ["true", "1", "yes"],
        "bank_name": get_saas_setting(db, "bank_name", "Commercial Bank of Ceylon"),
        "account_name": get_saas_setting(db, "bank_account_name", "Malitha Sayuranga"),
        "account_number": get_saas_setting(db, "bank_account_number", "800123456789"),
        "branch": get_saas_setting(db, "bank_branch", "Colombo Main Branch"),
        "instructions": get_saas_setting(db, "bank_transfer_instructions", "Please deposit or transfer the exact amount and enter your registered email or phone number as the payment reference or remark. Upload a clear screenshot or photo of the payment slip below.")
    }


@router.post("/api/payments/bank-transfer/upload")
async def upload_bank_payment_slip(
    file: UploadFile = File(...),
    target_plan: str = Form(...),
    amount_paid: float = Form(...),
    currency: str = Form("LKR"),
    billing_cycle: str = Form("1m"),
    bank_reference: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Candidate uploads bank deposit / online mobile transfer receipt (JPG, PNG, WEBP, PDF).
    Validates file integrity, saves safely to static/uploads/slips/, and creates a pending slip record.
    """
    plan = target_plan.lower().strip()
    if plan not in ["pro", "elite", "sprint"]:
        raise HTTPException(status_code=400, detail="Invalid plan tier. Allowed options: 'pro', 'elite', 'sprint'.")

    valid_cycles = ["1m", "3m", "6m", "12m", "lifetime"]
    cycle = (billing_cycle or "1m").lower().strip()
    if cycle not in valid_cycles:
        cycle = "1m"

    # Read up to 5MB + 1 byte
    max_slip_size = 5 * 1024 * 1024
    content = await file.read(max_slip_size + 1)
    if len(content) > max_slip_size:
        raise HTTPException(status_code=413, detail="Receipt file size exceeds the 5MB limit. Please upload a smaller image.")
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded slip file is empty.")

    filename = (file.filename or "slip.png").strip()
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".webp", ".pdf"]:
        raise HTTPException(status_code=400, detail="Invalid receipt format. Please upload PNG, JPG, WEBP, or PDF.")

    # Ensure uploads/slips directory exists
    slips_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "slips")
    os.makedirs(slips_dir, exist_ok=True)

    safe_filename = f"slip_u{current_user.id}_{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}"
    dest_path = os.path.join(slips_dir, safe_filename)
    with open(dest_path, "wb") as f:
        f.write(content)

    slip_url = f"/static/uploads/slips/{safe_filename}"

    slip = BankPaymentSlip(
        user_id=current_user.id,
        target_plan=plan,
        billing_cycle=cycle,
        amount_paid=float(amount_paid),
        currency=currency.upper().strip(),
        slip_image_url=slip_url,
        bank_reference=bank_reference.strip() if bank_reference else None,
        status="pending"
    )
    db.add(slip)
    db.commit()
    db.refresh(slip)

    return {
        "success": True,
        "message": "Payment slip submitted successfully! Our team will verify and activate your subscription within 1-2 hours.",
        "slip_id": slip.id,
        "status": "pending",
        "slip_url": slip_url
    }


@router.get("/api/payments/bank-transfer/my-slips")
async def get_my_bank_payment_slips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve all submitted bank payment slips for the authenticated candidate."""
    slips = db.scalars(
        select(BankPaymentSlip)
        .where(BankPaymentSlip.user_id == current_user.id)
        .order_by(BankPaymentSlip.id.desc())
    ).all()

    return [
        {
            "id": s.id,
            "target_plan": s.target_plan,
            "amount_paid": s.amount_paid,
            "currency": s.currency,
            "slip_image_url": s.slip_image_url,
            "bank_reference": s.bank_reference,
            "status": s.status,
            "admin_notes": s.admin_notes,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else None,
            "reviewed_at": s.reviewed_at.strftime("%Y-%m-%d %H:%M") if s.reviewed_at else None
        }
        for s in slips
    ]


@router.get("/api/payments/my-history")
async def get_my_payment_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns complete unified payment & subscription history for the authenticated candidate:
    - Online orders (PayHere gateway transactions)
    - Direct bank transfer slips
    """
    online_orders = db.scalars(
        select(OnlinePaymentOrder)
        .where(OnlinePaymentOrder.user_id == current_user.id)
        .order_by(OnlinePaymentOrder.id.desc())
    ).all()

    bank_slips = db.scalars(
        select(BankPaymentSlip)
        .where(BankPaymentSlip.user_id == current_user.id)
        .order_by(BankPaymentSlip.id.desc())
    ).all()

    orders_list = []
    for o in online_orders:
        orders_list.append({
            "id": o.id,
            "order_id": o.order_id,
            "target_plan": o.target_plan,
            "amount": o.amount,
            "currency": o.currency,
            "gateway": o.gateway or "payhere",
            "status": o.status,
            "status_code": o.status_code,
            "status_message": o.status_message,
            "payhere_payment_id": o.payhere_payment_id,
            "payment_method": o.payment_method,
            "card_no_masked": o.card_no_masked,
            "refund_requested": bool(getattr(o, "refund_requested", False)),
            "refund_requested_at": o.refund_requested_at.strftime("%Y-%m-%d %H:%M") if getattr(o, "refund_requested_at", None) else None,
            "refund_request_reason": getattr(o, "refund_request_reason", None),
            "payhere_refund_id": o.payhere_refund_id,
            "refunded_at": o.refunded_at.strftime("%Y-%m-%d %H:%M") if o.refunded_at else None,
            "billing_cycle": getattr(o, "billing_cycle", "1m") or "1m",
            "created_at": o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else None,
            "status_url": f"/payment/status?order_id={o.order_id}&status={o.status}",
            "can_request_refund": (o.status == "success" and not o.payhere_refund_id and not getattr(o, "refund_requested", False))
        })

    slips_list = []
    for s in bank_slips:
        slips_list.append({
            "id": s.id,
            "target_plan": s.target_plan,
            "billing_cycle": getattr(s, "billing_cycle", "1m") or "1m",
            "amount_paid": s.amount_paid,
            "currency": s.currency,
            "slip_image_url": s.slip_image_url,
            "bank_reference": s.bank_reference,
            "status": s.status,
            "admin_notes": s.admin_notes,
            "created_at": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else None,
            "reviewed_at": s.reviewed_at.strftime("%Y-%m-%d %H:%M") if s.reviewed_at else None
        })

    return {
        "online_orders": orders_list,
        "bank_slips": slips_list,
        "total_transactions": len(orders_list) + len(slips_list)
    }


@router.get("/api/payments/billing/discounts")
async def get_public_billing_discounts(db: Session = Depends(get_db)):
    """Returns active multi-duration discounts config for user pricing calculators."""
    return PayHereGateway.get_billing_discounts(db=db)



@router.post("/api/payments/orders/{order_id}/request-refund")
async def request_order_refund(
    order_id: str,
    req: UserRefundRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enables authenticated candidates to request a refund for an eligible paid order.
    Logs request reason, updates order state, and notifies administration immediately.
    """
    order = db.scalars(
        select(OnlinePaymentOrder)
        .where(
            OnlinePaymentOrder.order_id == order_id.strip(),
            OnlinePaymentOrder.user_id == current_user.id
        )
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found or you do not have permission to view it.")

    if order.status != "success":
        raise HTTPException(
            status_code=400,
            detail=f"Only successfully completed payments can be refunded. Current status is '{order.status}'."
        )

    if order.payhere_refund_id or order.status == "refunded":
        raise HTTPException(status_code=400, detail="This order has already been refunded.")

    if getattr(order, "refund_requested", False):
        raise HTTPException(
            status_code=409,
            detail="A refund request has already been submitted for this order and is under review."
        )

    reason = req.reason.strip()
    order.refund_requested = True
    order.refund_requested_at = datetime.utcnow()
    order.refund_request_reason = reason
    db.commit()
    db.refresh(order)

    # Dispatch administrative alert email asynchronously
    send_admin_user_refund_request(
        user_email=current_user.email,
        full_name=current_user.full_name or "Customer",
        order_id=order.order_id,
        payment_id=order.payhere_payment_id or "N/A",
        amount=order.amount,
        currency=order.currency,
        target_plan=order.target_plan,
        reason=reason,
        base_url=PayHereGateway.get_base_url(),
        db=db,
        background_tasks=background_tasks
    )

    logger.info("Candidate %s submitted refund request for order %s (Reason: %s)", current_user.email, order.order_id, reason)

    return {
        "success": True,
        "message": "Refund request submitted successfully. Our finance team will review and process your refund shortly.",
        "order_id": order.order_id,
        "refund_requested": True,
        "refund_requested_at": order.refund_requested_at.strftime("%Y-%m-%d %H:%M")
    }


@router.post("/api/payments/payhere/initiate", response_model=PayHereInitiateResponse)
async def initiate_payhere_payment(
    req: PayHereInitiateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generates a secure, cryptographically signed PayHere checkout session.
    Calculates MD5 hash on server. Prevents client-side price tampering.
    """

    # -----------------------------------------
    # Cleanup abandoned PayHere orders older than 15 mins
    # -----------------------------------------
    now = datetime.utcnow()
    cutoff_time = now - timedelta(minutes=15)

    db.query(OnlinePaymentOrder).filter(
        OnlinePaymentOrder.gateway == "payhere",
        OnlinePaymentOrder.status == "initiated",
        OnlinePaymentOrder.created_at < cutoff_time
    ).update(
        {
            OnlinePaymentOrder.status: "expired",
            OnlinePaymentOrder.status_message: "Payment initiation expired after 15 minutes."
        },
        synchronize_session=False
    )
    db.commit()

    # -----------------------------------------
    # Double Payment & Double Charge Shield
    # -----------------------------------------
    active_cutoff = now - timedelta(minutes=15)
    existing_active = db.scalars(
        select(OnlinePaymentOrder)
        .where(
            OnlinePaymentOrder.user_id == current_user.id,
            OnlinePaymentOrder.status.in_(["initiated", "pending"]),
            OnlinePaymentOrder.created_at >= active_cutoff
        )
        .order_by(OnlinePaymentOrder.id.desc())
    ).first()

    if existing_active and not req.force:
        plan_name = existing_active.target_plan.upper()
        raise HTTPException(
            status_code=409,
            detail={
                "error": "payment_in_progress",
                "message": f"You already have a payment in progress for {plan_name} (Order: {existing_active.order_id}). Please check its status before starting a new payment.",
                "order_id": existing_active.order_id,
                "status": existing_active.status,
                "target_plan": existing_active.target_plan,
                "status_url": f"/payment/status?order_id={existing_active.order_id}&status={existing_active.status}",
                "can_force": True
            }
        )

    if req.force:
        # User explicitly requested a fresh checkout; supersede previous in-flight initiated orders
        db.query(OnlinePaymentOrder).filter(
            OnlinePaymentOrder.user_id == current_user.id,
            OnlinePaymentOrder.status == "initiated"
        ).update(
            {
                OnlinePaymentOrder.status: "superseded",
                OnlinePaymentOrder.status_message: "Candidate explicitly requested a fresh checkout session."
            },
            synchronize_session=False
        )
        db.commit()
    
    plan = req.plan.lower().strip()
    if plan not in ["pro", "elite", "sprint"]:
        raise HTTPException(status_code=400, detail="Invalid subscription plan. Only 'pro', 'elite', and 'sprint' are supported.")

    billing_cycle = (req.billing_cycle or "1m").lower().strip()
    if billing_cycle not in ["1m", "3m", "6m", "12m", "lifetime"]:
        billing_cycle = "1m"

    currency = req.currency.upper().strip() if req.currency else "LKR"
    if currency not in ["LKR", "USD"]:
        currency = "LKR"

    verified_amount = PayHereGateway.get_plan_price(plan, currency, billing_cycle=billing_cycle, db=db)

    # Unique Order Reference
    order_id = f"ORD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    # Determine Base URL
    env_base = os.getenv("APP_BASE_URL")
    if env_base and env_base.strip():
        base_url = env_base.strip().rstrip("/")
    else:
        base_url = str(request.base_url).rstrip("/")

    # Prepare signed payload
    payload = PayHereGateway.prepare_checkout_payload(
        order_id=order_id,
        plan_tier=plan,
        user_email=current_user.email,
        user_name=current_user.full_name or "Candidate",
        user_id=current_user.id,
        base_url=base_url,
        currency=currency,
        billing_cycle=billing_cycle,
        phone=req.phone,
        address=req.address,
        city=req.city,
        db=db
    )

    # Record order in database
    order = OnlinePaymentOrder(
        order_id=order_id,
        user_id=current_user.id,
        target_plan=plan,
        billing_cycle=billing_cycle,
        amount=verified_amount,
        currency=currency,
        gateway="payhere",
        status="initiated"
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return PayHereInitiateResponse(
        success=True,
        order_id=order_id,
        action_url=payload["action_url"],
        params=payload["params"],
        mode=payload["mode"],
        amount=verified_amount,
        currency=currency,
        plan=plan,
        billing_cycle=billing_cycle
    )


@router.post("/api/payments/payhere/notify")
async def payhere_ipn_notify(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    PayHere Instant Payment Notification (IPN) Webhook Callback.
    1. Verifies md5sig cryptographic signature with constant-time comparison.
    2. Validates amount & currency against database order.
    3. Handles status codes: 2 (Success), 0 (Pending), -1 (Canceled), -2/-3 (Failed/Chargedback).
    4. Automatically upgrades user subscription upon verified success.
    """
    form_data = await request.form()
    data = dict(form_data)
    logger.info("PayHere IPN Webhook Received: %s", {k: v for k, v in data.items() if k != "md5sig"})

    merchant_id = str(data.get("merchant_id", "")).strip()
    order_id = str(data.get("order_id", "")).strip()
    payment_id = str(data.get("payment_id", "")).strip()
    payhere_amount = str(data.get("payhere_amount", "")).strip()
    payhere_currency = str(data.get("payhere_currency", "")).strip().upper()
    status_code_str = str(data.get("status_code", "")).strip()
    md5sig = str(data.get("md5sig", "")).strip()
    method = str(data.get("method", "")).strip()
    status_message = str(data.get("status_message", "")).strip()
    card_holder_name = str(data.get("card_holder_name", "")).strip()
    card_no = str(data.get("card_no", "")).strip()

    if card_no:
      if len(card_no) > 4:
        card_no_masked = "*" * (len(card_no) - 4) + card_no[-4:]
      else:
        card_no_masked = "****"
    else:
        card_no_masked = None

    if not order_id or not status_code_str or not md5sig:
        logger.error("PayHere IPN missing mandatory fields: order_id=%s, status_code=%s", order_id, status_code_str)
        raise HTTPException(status_code=400, detail="Missing required IPN fields.")

    config = PayHereGateway.get_config()
    merchant_secret = config["merchant_secret"]

    # 1. Cryptographic Signature Verification
    is_valid_sig = PayHereGateway.verify_ipn_signature(
        merchant_id=merchant_id,
        order_id=order_id,
        payhere_amount=payhere_amount,
        payhere_currency=payhere_currency,
        status_code=status_code_str,
        md5sig=md5sig,
        merchant_secret=merchant_secret
    )

    if not is_valid_sig:
        logger.critical("Security Alert: PayHere IPN signature verification failed! order_id=%s, received_sig=%s", order_id, md5sig)
        raise HTTPException(status_code=400, detail="Invalid cryptographic IPN signature.")

    # 2. Lookup existing order
    order = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == order_id)).first()
    if not order:
        logger.error("PayHere IPN received for non-existent order: %s", order_id)
        raise HTTPException(status_code=404, detail="Order reference not found.")

    # 3. Anti-Tampering Check: Compare paid amount and currency with database
    try:
        paid_amount_float = float(payhere_amount)
    except (ValueError, TypeError):
        paid_amount_float = 0.0

    if abs(paid_amount_float - order.amount) > 0.01 or payhere_currency != order.currency:
        logger.critical(
            "Price Tampering Detected! Order %s expected %s %s, received %s %s",
            order_id, order.currency, order.amount, payhere_currency, paid_amount_float
        )
        order.status = "amount_tampered"
        order.status_message = f"Tampered: Paid {payhere_currency} {payhere_amount} vs Expected {order.currency} {order.amount}"
        sanitized_tamper = {k: v for k, v in data.items() if k not in ["merchant_secret", "md5sig"]}
        if "card_no" in sanitized_tamper:
            sanitized_tamper["card_no"] = card_no_masked
        order.raw_ipn_data = json.dumps(sanitized_tamper)
        db.commit()
        raise HTTPException(status_code=400, detail="Payment amount or currency mismatch.")

    try:
        status_code_int = int(status_code_str)
    except ValueError:
        status_code_int = -99

    # Idempotency check: If order is already success, don't duplicate upgrades or emails
    if status_code_int == 2 and order.status == "success":
        logger.info(
            "Duplicate PayHere success IPN ignored (idempotent): order_id=%s payment_id=%s",
            order_id,
            payment_id
        )
        return Response(content="OK", status_code=200, media_type="text/plain")

    # Sanitize raw IPN data (never store raw secrets or unmasked cards in audit logs)
    sanitized_ipn = {k: v for k, v in data.items() if k not in ["merchant_secret", "md5sig"]}
    if "card_no" in sanitized_ipn:
        sanitized_ipn["card_no"] = card_no_masked

    order.payhere_payment_id = payment_id
    order.payment_method = method
    order.card_holder_name = card_holder_name
    order.card_no_masked = card_no_masked
    order.status_code = status_code_int
    order.status_message = status_message
    order.raw_ipn_data = json.dumps(sanitized_ipn)
    order.updated_at = datetime.utcnow()

    # 4. Status Code Processing
    if status_code_int == 2:
        # STATUS: SUCCESS (2)
        order.status = "success"
        candidate = db.get(User, order.user_id)
        if candidate:
            now = datetime.utcnow()
            cycle = (getattr(order, "billing_cycle", "1m") or "1m").lower().strip()
            if order.target_plan == "sprint":
                duration_days = 7
                plan_title = "7-Day Sprint Pass"
                candidate.plan_tier = "pro"
                candidate.subscription_expires_at = now + timedelta(days=7)
            else:
                candidate.plan_tier = order.target_plan
                if cycle == "3m":
                    duration_days = 90
                    plan_title = f"{order.target_plan.capitalize()} Plan (3 Months Pass)"
                elif cycle == "6m":
                    duration_days = 180
                    plan_title = f"{order.target_plan.capitalize()} Plan (6 Months Pass)"
                elif cycle == "12m":
                    duration_days = 365
                    plan_title = f"{order.target_plan.capitalize()} Plan (1 Year Access)"
                elif cycle == "lifetime":
                    duration_days = 36500
                    plan_title = f"{order.target_plan.capitalize()} Plan (Lifetime Access)"
                else:
                    duration_days = 30
                    plan_title = f"{order.target_plan.capitalize()} Plan (30 Days)"

                candidate.subscription_expires_at = now + timedelta(days=duration_days)

            candidate.subscription_status = "active"
            candidate.subscription_started_at = now
            logger.info("Candidate %s successfully upgraded to %s via PayHere (Order %s, Payment ID %s, Cycle %s)", candidate.email, candidate.plan_tier.upper(), order_id, payment_id, cycle)

            # Auto-supersede any pending bank transfer slips for this candidate
            pending_slips = db.scalars(
                select(BankPaymentSlip)
                .where(BankPaymentSlip.user_id == candidate.id, BankPaymentSlip.status == "pending")
            ).all()
            for ps in pending_slips:
                ps.admin_notes = f"Superseded: User activated {order.target_plan.upper()} ({cycle}) via PayHere card payment (Order: {order.order_id})"

            base_url = PayHereGateway.get_base_url()

            # Dispatch non-blocking background emails to customer & admin
            send_user_subscription_confirmed(
                to_email=candidate.email,
                full_name=candidate.full_name or "Customer",
                plan_title=plan_title,
                amount=order.amount,
                currency=order.currency,
                order_id=order.order_id,
                payment_id=payment_id,
                duration_days=duration_days,
                base_url=base_url,
                background_tasks=background_tasks
            )
            send_admin_subscription_alert(
                user_email=candidate.email,
                full_name=candidate.full_name or "Customer",
                plan_title=plan_title,
                amount=order.amount,
                currency=order.currency,
                order_id=order.order_id,
                payment_id=payment_id,
                method=method,
                base_url=base_url,
                db=db,
                background_tasks=background_tasks
            )

    elif status_code_int == 0:
        # STATUS: PENDING (0)
        order.status = "pending"
        order.status_message = status_message or "Payment is pending clearance from issuing bank or PayHere."
        logger.info("PayHere Payment Pending (0): Order %s", order_id)

    elif status_code_int == -1:
        # STATUS: CANCELED (-1)
        order.status = "canceled"
        order.status_message = status_message or "Payment was canceled by candidate on PayHere portal."
        logger.info("PayHere Payment Canceled (-1): Order %s", order_id)

    elif status_code_int == -2:
        # STATUS: FAILED (-2)
        order.status = "failed"
        order.status_message = status_message or "Payment failed or declined by card network."
        logger.warning("PayHere Payment Failed (-2): Order %s, Reason: %s", order_id, order.status_message)

    elif status_code_int == -3:
        # STATUS: CHARGEDBACK (-3)
        order.status = "chargedback"
        order.status_message = status_message or "Chargeback or dispute filed by cardholder."
        candidate = db.get(User, order.user_id)
        if candidate:
            now = datetime.utcnow()
            expected_plan = "pro" if order.target_plan == "sprint" else order.target_plan
            if candidate.plan_tier == expected_plan:
                candidate.plan_tier = "free"
                candidate.subscription_status = "expired"
                candidate.subscription_expires_at = now
                logger.warning(
                    "User %s subscription immediately revoked to FREE following chargeback on order %s",
                    candidate.email, order.order_id
                )

            # Dispatch urgent security alert to administrators
            send_admin_chargeback_alert(
                user_email=candidate.email,
                full_name=candidate.full_name or "Customer",
                order_id=order.order_id,
                payment_id=payment_id,
                amount=order.amount,
                currency=order.currency,
                target_plan=order.target_plan,
                base_url=PayHereGateway.get_base_url(),
                db=db,
                background_tasks=background_tasks
            )
        logger.critical("SECURITY AUDIT: PayHere Payment Charged Back (-3): Order %s, Payment ID %s", order_id, payment_id)

    db.commit()
    return Response(content="OK", status_code=200, media_type="text/plain")


def sync_order_status_from_payhere(
    order: OnlinePaymentOrder,
    db: Session,
    background_tasks: Optional[BackgroundTasks] = None
) -> str:
    """
    Directly queries PayHere Retrieval API to check if an initiated/pending order has succeeded.
    Provides bulletproof fallback against delayed, dropped, or blocked webhook notifications.
    """
    if order.status == "success":
        return "success"

    try:
        payment_data = PayHereGateway.retrieve_order_payment(order.order_id)
    except Exception as err:
        logger.warning("Retrieval sync warning for %s: %s", order.order_id, err)
        payment_data = None

    if not payment_data:
        return order.status

    payhere_status = str(payment_data.get("status", "")).upper()
    payment_id = str(payment_data.get("payment_id", "")).strip()
    method_data = payment_data.get("payment_method") or {}
    method = method_data.get("method") or "PayHere Gateway"
    card_no = method_data.get("card_no") or ""
    card_name = method_data.get("card_customer_name") or ""

    if payhere_status in ["RECEIVED", "SUCCESS", "COMPLETED"]:
        order.status = "success"
        order.status_code = 2
        order.status_message = "Payment verified via PayHere Retrieval API"
        order.payhere_payment_id = payment_id
        order.payment_method = method
        order.card_no_masked = card_no
        order.card_holder_name = card_name
        order.updated_at = datetime.utcnow()

        candidate = db.get(User, order.user_id)
        if candidate:
            now = datetime.utcnow()
            duration_days = 7 if order.target_plan == "sprint" else 30
            if order.target_plan == "sprint":
                candidate.plan_tier = "pro"
                candidate.subscription_expires_at = now + timedelta(days=7)
            else:
                candidate.plan_tier = order.target_plan
                candidate.subscription_expires_at = now + timedelta(days=30)
            candidate.subscription_status = "active"
            candidate.subscription_started_at = now
            logger.info("Candidate %s successfully upgraded to %s via PayHere Retrieval Sync (Order %s, Payment ID %s)", candidate.email, candidate.plan_tier.upper(), order.order_id, payment_id)

            plan_names = {
                "sprint": "7-Day Sprint Pass",
                "pro": "Pro Career Plan (30 Days)",
                "elite": "Executive Elite (30 Days)"
            }
            plan_title = plan_names.get((order.target_plan or "pro").lower(), f"{order.target_plan.title()} Plan")
            base_url = PayHereGateway.get_base_url()

            send_user_subscription_confirmed(
                to_email=candidate.email,
                full_name=candidate.full_name or "Customer",
                plan_title=plan_title,
                amount=order.amount,
                currency=order.currency,
                order_id=order.order_id,
                payment_id=payment_id,
                duration_days=duration_days,
                base_url=base_url,
                background_tasks=background_tasks
            )
            send_admin_subscription_alert(
                user_email=candidate.email,
                full_name=candidate.full_name or "Customer",
                plan_title=plan_title,
                amount=order.amount,
                currency=order.currency,
                order_id=order.order_id,
                payment_id=payment_id,
                method=method,
                base_url=base_url,
                db=db,
                background_tasks=background_tasks
            )

        db.commit()
        return "success"
    elif payhere_status in ["FAILED", "CHARGEBACK"]:
        order.status = "failed"
        order.status_code = -2
        order.status_message = f"Status: {payhere_status}"
        order.updated_at = datetime.utcnow()
        db.commit()
        return "failed"
    elif payhere_status in ["CANCELED", "CANCELLED"]:
        order.status = "canceled"
        order.status_code = -1
        order.status_message = "Canceled by user"
        order.updated_at = datetime.utcnow()
        db.commit()
        return "canceled"

    return order.status


@router.api_route("/api/payments/payhere/return", methods=["GET", "POST"])
async def payhere_return_redirect(
    request: Request,
    background_tasks: BackgroundTasks,
    order_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    PayHere return redirect URL. Handles both GET and POST requests.
    Directly queries PayHere Retrieval API to resolve status immediately without waiting for webhook.
    """
    effective_order_id = order_id
    if not effective_order_id and request.method == "POST":
        try:
            form_data = await request.form()
            effective_order_id = form_data.get("order_id")
        except Exception:
            pass

    status = "success"
    if effective_order_id:
        order = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == effective_order_id)).first()
        if order:
            if order.status in ["initiated", "pending"]:
                status = sync_order_status_from_payhere(order, db, background_tasks)
            else:
                status = order.status

    return RedirectResponse(url=f"/payment/status?order_id={effective_order_id or ''}&status={status}", status_code=303)


@router.api_route("/api/payments/payhere/cancel", methods=["GET", "POST"])
async def payhere_cancel_redirect(
    request: Request,
    order_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    PayHere cancel redirect URL. Handles both GET and POST requests.
    Marks initiated order as canceled and redirects candidate to /payment/status with reason.
    """
    effective_order_id = order_id
    if not effective_order_id and request.method == "POST":
        try:
            form_data = await request.form()
            effective_order_id = form_data.get("order_id")
        except Exception:
            pass

    if effective_order_id:
        order = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == effective_order_id)).first()
        if order and order.status in ["initiated", "pending"]:
            order.status = "canceled"
            order.status_message = "Payment canceled by user during PayHere checkout."
            db.commit()

    return RedirectResponse(url=f"/payment/status?order_id={effective_order_id or ''}&status=canceled", status_code=303)


@router.get("/api/payments/orders/{order_id}/status")
async def get_payment_order_status(
    order_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Returns verified status for a specific payment order.
    Actively checks PayHere Retrieval API if status is still initiated or pending.
    """
    order = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order reference not found")

    if order.status in ["initiated", "pending"]:
        sync_order_status_from_payhere(order, db, background_tasks)
        db.refresh(order)

    return {
        "order_id": order.order_id,
        "status": order.status,
        "target_plan": order.target_plan,
        "amount": order.amount,
        "currency": order.currency,
        "status_code": order.status_code,
        "status_message": order.status_message,
        "payhere_payment_id": order.payhere_payment_id,
        "payment_method": order.payment_method,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "updated_at": order.updated_at.isoformat() if order.updated_at else None
    }


@router.post("/api/checkout")
async def create_checkout(req: CheckoutRequest):
    """Lemon Squeezy checkout session / credit simulation."""
    tier_map = {
        "single": ("Single ATS Pass ($3)", "$3"),
        "monthly": ("Monthly Pro Unlimited + Live Portfolio ($9/mo)", "$9/mo"),
        "lifetime": ("Lifetime Career Pass + Custom Domain ($29)", "$29")
    }
    tier_info = tier_map.get(req.tier, ("Monthly Pro Pass ($9/mo)", "$9/mo"))
    return {
        "success": True,
        "tier": req.tier,
        "plan_name": tier_info[0],
        "checkout_url": "https://lemonsqueezy.com/checkout/demo",
        "mock_unlocked": True,
        "message": f"Successfully activated {tier_info[0]}. Unlimited ATS Downloads, Custom Private Domains & Live Hosted Portfolio Unlocked!"
    }


@router.get("/api/plans", response_model=PlansConfigResponse)
async def get_subscription_plans(db: Session = Depends(get_db)):
    """Fetch default dynamically configured subscription plans."""
    country_dict = _get_country_pricing_dict(db)
    default_plans = country_dict.get("DEFAULT", {}).get("plans", DEFAULT_PLANS_CONFIG_DATA)
    return PlansConfigResponse(plans=[PlanItemConfig(**p) for p in default_plans])


@router.get("/api/subscription/plans", response_model=CountryPricingResponse)
async def get_country_subscription_plans(
    request: Request,
    country: Optional[str] = None,
    currency: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Public Endpoint: Dynamic Purchasing Power Parity (PPP) Pricing Engine.
    Detects user's country from query param, Cloudflare header, or IP headers.
    Returns tailored currency and price displays.
    """
    target_country = (country or "").strip().upper()
    if not target_country:
        target_country = request.headers.get("CF-IPCountry", "").strip().upper()
    if not target_country:
        target_country = request.headers.get("X-Country-Code", "").strip().upper()
    if not target_country:
        target_country = "LK"  # Default fallback

    all_countries = _get_country_pricing_dict(db)

    matched_config = all_countries.get(target_country)
    if not matched_config:
        if (currency or "").strip().upper() == "LKR" and "LK" in all_countries:
            matched_config = all_countries["LK"]
        else:
            matched_config = all_countries.get("DEFAULT", DEFAULT_COUNTRY_PRICING_DATA["DEFAULT"])

    available_countries_list = [
        {"code": k, "name": v.get("country_name", k), "currency": v.get("currency_code", "USD"), "symbol": v.get("currency_symbol", "$")}
        for k, v in all_countries.items()
    ]

    return CountryPricingResponse(
        country_code=matched_config.get("country_code", "DEFAULT"),
        detected_country=matched_config.get("country_code", "DEFAULT"),
        currency=matched_config.get("currency_code", "USD"),
        active_currency=matched_config.get("currency_code", "USD"),
        currency_symbol=matched_config.get("currency_symbol", "$"),
        active_currency_symbol=matched_config.get("currency_symbol", "$"),
        sprint_price=matched_config.get("sprint_price", "$4.99"),
        plans=[PlanItemConfig(**p) for p in matched_config.get("plans", [])],
        available_countries=available_countries_list
    )
