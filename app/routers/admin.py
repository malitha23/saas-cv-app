import json
import datetime
import logging
from typing import Optional, Dict, List, Any
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import User, UserResume, SaasSetting, BankPaymentSlip, OnlinePaymentOrder, PromoCode, PromoCodeUsage, QueuedEmail
from app.schemas import (
    AdminOverviewResponse, AdminSettingItem, AdminUpdateSettingsRequest,
    AdminUserListItem, AdminUpdateUserPlanRequest,
    AdminRefundRequest, AdminRefundResponse,
    AdminUpdateCountryPricingRequest, UpdatePlansConfigRequest,
    AdminCreatePromoCodeRequest, AdminPromoCodeItem,
    QueuedEmailItem, EmailQueueListResponse, EmailQueueStatsResponse
)
from app.auth import require_admin, get_saas_setting
from app.state import build_user_response
from app.pricing import _get_country_pricing_dict
from app.payhere import PayHereGateway
from app.email_service import (
    send_user_refund_processed, send_admin_refund_alert,
    process_email_queue, retry_single_queued_email, retry_all_queued_emails
)

logger = logging.getLogger("dreemfolio.admin")

router = APIRouter(tags=["Admin Control Center"])


@router.get("/api/admin/overview", response_model=AdminOverviewResponse)
async def get_admin_overview(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Administrator metrics: users count, plan breakdown, estimated MRR, and saved resumes."""
    users = db.scalars(select(User)).all()
    total_users = len(users)
    free_users = sum(1 for u in users if (u.plan_tier or "free") == "free")
    pro_users = sum(1 for u in users if (u.plan_tier or "free") == "pro")
    elite_users = sum(1 for u in users if (u.plan_tier or "free") == "elite")
    admin_users = sum(1 for u in users if u.is_admin)

    try:
        pro_price = float(get_saas_setting(db, "pro_monthly_price", "9"))
    except (ValueError, TypeError):
        pro_price = 9.0
    try:
        elite_price = float(get_saas_setting(db, "elite_monthly_price", "29"))
    except (ValueError, TypeError):
        elite_price = 29.0

    estimated_mrr = (pro_users * pro_price) + (elite_users * elite_price)
    saved_resumes_count = len(db.scalars(select(UserResume.id)).all())

    return AdminOverviewResponse(
        total_users=total_users,
        free_users=free_users,
        pro_users=pro_users,
        elite_users=elite_users,
        admin_users=admin_users,
        estimated_mrr_usd=round(estimated_mrr, 2),
        total_saved_resumes=saved_resumes_count
    )


@router.get("/api/admin/settings", response_model=List[AdminSettingItem])
async def get_admin_settings(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retrieve all configurable SaaS subscription limits, feature flags, and pricing."""
    settings = db.scalars(select(SaasSetting).order_by(SaasSetting.id.asc())).all()
    return [
        AdminSettingItem(
            key=s.key,
            value=s.value,
            description=s.description or ""
        )
        for s in settings
    ]


@router.post("/api/admin/settings/update")
async def update_admin_settings(
    req: AdminUpdateSettingsRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Update subscription limits, download quotas, or pricing rules with validation."""
    updated_count = 0
    for key, val in req.settings.items():
        val_str = str(val).strip()
        if key in ["free_daily_ai_limit", "free_daily_pdf_limit"]:
            try:
                num = int(val_str)
                if num < 0 or num > 100:
                    raise HTTPException(status_code=400, detail=f"{key} must be between 0 and 100")
            except ValueError:
                raise HTTPException(status_code=400, detail=f"{key} must be an integer")
        elif key in ["free_allow_visual_download", "free_allow_cloud_restore"]:
            val_str = "true" if val_str.lower() in ["true", "1", "yes"] else "false"
        elif key in ["pro_monthly_price", "elite_monthly_price", "sprint_price"]:
            try:
                price = float(val_str)
                if price < 0:
                    raise HTTPException(status_code=400, detail=f"{key} cannot be negative")
            except ValueError:
                raise HTTPException(status_code=400, detail=f"{key} must be a number")

        stmt = select(SaasSetting).where(SaasSetting.key == key)
        setting = db.scalars(stmt).first()
        if setting:
            setting.value = val_str
            setting.updated_at = datetime.datetime.utcnow()
            updated_count += 1
        else:
            new_s = SaasSetting(key=key, value=val_str, description="")
            db.add(new_s)
            updated_count += 1

    db.commit()
    return {"success": True, "message": f"{updated_count} settings successfully updated!"}


@router.get("/api/admin/users", response_model=List[AdminUserListItem])
async def get_admin_users(
    search: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retrieve full user list for administrative audit, role management, and plan overrides."""
    stmt = select(User).order_by(User.id.desc())
    users = db.scalars(stmt).all()
    now = datetime.datetime.utcnow()
    today_str = datetime.date.today().isoformat()

    results = []
    for u in users:
        if search:
            s_low = search.lower()
            if s_low not in u.email.lower() and s_low not in (u.full_name or "").lower():
                continue

        days_left = None
        if u.subscription_expires_at:
            delta = u.subscription_expires_at - now
            sec = delta.total_seconds()
            days_left = max(1, int(sec // 86400) + (1 if (sec % 86400) > 0 else 0)) if sec > 0 else 0

        started_str = u.subscription_started_at.strftime("%b %d, %Y") if u.subscription_started_at else None
        exp_str = u.subscription_expires_at.strftime("%b %d, %Y") if u.subscription_expires_at else None

        daily_ai = u.daily_ai_generations_count or 0 if u.last_generation_date == today_str else 0
        daily_pdf = u.daily_pdf_downloads_count or 0 if u.last_generation_date == today_str else 0

        results.append(
            AdminUserListItem(
                id=u.id,
                email=u.email,
                full_name=u.full_name or "",
                plan_tier=u.plan_tier or "free",
                subscription_status=u.subscription_status or "active",
                is_admin=bool(u.is_admin),
                subscription_started_at=started_str,
                subscription_expires_at=exp_str,
                subscription_days_remaining=days_left,
                daily_ai_generations_count=daily_ai,
                daily_pdf_downloads_count=daily_pdf,
                created_at=u.created_at.strftime("%b %d, %Y")
            )
        )
    return results


@router.post("/api/admin/users/{user_id}/plan")
async def admin_override_user_plan(
    user_id: int,
    req: AdminUpdateUserPlanRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Override a user's subscription tier, extend validity days, or toggle admin privileges."""
    stmt = select(User).where(User.id == user_id)
    user = db.scalars(stmt).first()
    if not user:
        raise HTTPException(status_code=404, detail="Target user not found.")

    tier = req.plan_tier.lower()
    if tier not in ["free", "pro", "elite", "sprint"]:
        raise HTTPException(status_code=400, detail="Invalid plan tier. Choose from: 'free', 'pro', 'elite', 'sprint'.")

    now = datetime.datetime.utcnow()
    user.plan_tier = tier
    if tier == "free":
        user.subscription_expires_at = None
        user.subscription_status = "active"
    else:
        days = max(1, req.duration_days)
        if user.subscription_expires_at and user.subscription_expires_at > now:
            user.subscription_expires_at = user.subscription_expires_at + datetime.timedelta(days=days)
        else:
            user.subscription_started_at = now
            user.subscription_expires_at = now + datetime.timedelta(days=days)
        user.subscription_status = "active"

    if req.is_admin is not None:
        user.is_admin = bool(req.is_admin)

    db.commit()
    db.refresh(user)

    return {
        "success": True,
        "message": f"Successfully updated User #{user.id} ({user.email}) to {tier.upper()} plan!",
        "user": build_user_response(user, db)
    }


@router.get("/api/admin/bank-slips")
async def admin_get_bank_slips(
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin retrieves submitted bank transfer receipts with candidate information."""
    stmt = select(BankPaymentSlip).order_by(BankPaymentSlip.id.desc())
    if status and status.lower() in ["pending", "approved", "rejected"]:
        stmt = stmt.where(BankPaymentSlip.status == status.lower())

    slips = db.scalars(stmt).all()
    results = []
    for s in slips:
        candidate = db.get(User, s.user_id)
        results.append({
            "id": s.id,
            "user_id": s.user_id,
            "user_email": candidate.email if candidate else "Unknown",
            "user_name": candidate.full_name if candidate else "Candidate",
            "current_user_tier": candidate.plan_tier if candidate else "free",
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
    return results


@router.post("/api/admin/bank-slips/{slip_id}/approve")
async def admin_approve_bank_slip(
    slip_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    1-Click Admin Approval:
    Instantly upgrades candidate's account to target plan (Pro/Elite/Sprint),
    activates subscription, sets expiration date based on billing_cycle, and marks slip approved.
    """
    slip = db.get(BankPaymentSlip, slip_id)
    if not slip:
        raise HTTPException(status_code=404, detail="Bank payment slip not found.")

    candidate = db.get(User, slip.user_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Associated candidate user account not found.")

    tier = slip.target_plan.lower().strip()
    cycle = (getattr(slip, "billing_cycle", "1m") or "1m").lower().strip()
    now = datetime.datetime.utcnow()
    if tier == "sprint":
        days = 7
        actual_tier = "pro"
    else:
        actual_tier = tier
        if cycle == "3m":
            days = 90
        elif cycle == "6m":
            days = 180
        elif cycle == "12m":
            days = 365
        elif cycle == "lifetime":
            days = 36500
        else:
            days = 30

    candidate.plan_tier = actual_tier
    candidate.subscription_status = "active"
    candidate.subscription_started_at = now
    candidate.subscription_expires_at = now + datetime.timedelta(days=days)

    slip.status = "approved"
    slip.reviewed_by = current_user.id
    slip.reviewed_at = now
    slip.admin_notes = f"Approved by admin ({current_user.email}) on {now.strftime('%Y-%m-%d %H:%M UTC')}"

    db.commit()
    db.refresh(candidate)
    db.refresh(slip)

    return {
        "success": True,
        "message": f"Successfully activated {actual_tier.upper()} plan for {candidate.email} (+{days} days)! Slip marked approved.",
        "user_id": candidate.id,
        "user_email": candidate.email,
        "new_tier": candidate.plan_tier,
        "expires_at": candidate.subscription_expires_at.strftime("%Y-%m-%d")
    }


@router.post("/api/admin/bank-slips/{slip_id}/reject")
async def admin_reject_bank_slip(
    slip_id: int,
    req: Dict[str, Any] = {},
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin marks slip rejected with explanation note."""
    slip = db.get(BankPaymentSlip, slip_id)
    if not slip:
        raise HTTPException(status_code=404, detail="Bank payment slip not found.")

    reason = req.get("reason", "Payment verification could not be confirmed.")
    slip.status = "rejected"
    slip.reviewed_by = current_user.id
    slip.reviewed_at = datetime.datetime.utcnow()
    slip.admin_notes = reason

    db.commit()
    db.refresh(slip)
    return {"success": True, "message": "Slip marked as rejected.", "slip_id": slip.id}


@router.post("/api/admin/bank-transfer/config")
async def admin_update_bank_config(
    req: Dict[str, Any],
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin updates bank details and deposit instructions."""
    fields = [
        "bank_transfer_enabled", "bank_name", "bank_account_name",
        "bank_account_number", "bank_branch", "bank_transfer_instructions"
    ]
    updated = 0
    for f in fields:
        if f in req:
            val_str = str(req[f]).strip()
            stmt = select(SaasSetting).where(SaasSetting.key == f)
            setting = db.scalars(stmt).first()
            if setting:
                setting.value = val_str
                setting.updated_at = datetime.datetime.utcnow()
            else:
                db.add(SaasSetting(key=f, value=val_str, description="Bank transfer setting"))
            updated += 1

    db.commit()
    return {"success": True, "message": f"{updated} bank transfer settings updated!"}


@router.get("/api/admin/payhere/config")
async def admin_get_payhere_config(
    current_user: User = Depends(require_admin)
):
    """Returns active PayHere credentials read directly from .env (secret masked)."""
    try:
        config = PayHereGateway.get_config()
        secret = config["merchant_secret"]
        masked_secret = f"{secret[:3]}...{secret[-3:]}" if len(secret) > 6 else "***"
        return {
            "merchant_id": config["merchant_id"],
            "merchant_secret_masked": masked_secret,
            "mode": config["mode"],
            "currency": config["currency"],
            "checkout_url": config["checkout_url"],
            "app_base_url": config.get("app_base_url", "")
        }
    except Exception as e:
        return {
            "merchant_id": "",
            "merchant_secret_masked": "",
            "mode": "sandbox",
            "currency": "LKR",
            "checkout_url": "",
            "app_base_url": "",
            "error": str(e)
        }


@router.get("/api/admin/payhere/orders")
async def admin_get_payhere_orders(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lists online gateway payment orders with user, refund, and status details."""
    orders = db.scalars(select(OnlinePaymentOrder).order_by(OnlinePaymentOrder.id.desc()).limit(100)).all()
    results = []
    for o in orders:
        user = db.get(User, o.user_id)
        results.append({
            "id": o.id,
            "order_id": o.order_id,
            "user_id": o.user_id,
            "user_email": user.email if user else "Unknown",
            "target_plan": o.target_plan,
            "billing_cycle": getattr(o, "billing_cycle", "1m") or "1m",
            "amount": o.amount,
            "currency": o.currency,
            "status": o.status,
            "payhere_payment_id": o.payhere_payment_id,
            "payment_method": o.payment_method,
            "card_no_masked": o.card_no_masked,
            "payhere_refund_id": o.payhere_refund_id,
            "refund_reason": o.refund_reason,
            "refunded_at": o.refunded_at.strftime("%Y-%m-%d %H:%M") if o.refunded_at else None,
            "refunded_by_admin": o.refunded_by_admin,
            "refund_requested": bool(o.refund_requested),
            "refund_requested_at": o.refund_requested_at.strftime("%Y-%m-%d %H:%M") if o.refund_requested_at else None,
            "refund_request_reason": o.refund_request_reason,
            "created_at": o.created_at.strftime("%Y-%m-%d %H:%M") if o.created_at else None,
            "updated_at": o.updated_at.strftime("%Y-%m-%d %H:%M") if o.updated_at else None
        })
    return results


@router.post("/api/admin/payhere/refund", response_model=AdminRefundResponse)
async def admin_process_payhere_refund(
    req: AdminRefundRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Super Admin Endpoint to process a monetary refund via PayHere Refund API.
    100% Secure Architecture:
    1. Super Admin Authentication (RBAC): require_admin verified JWT.
    2. Anti-Double-Refund Concurrency Shield: Prevents multiple clicks or concurrent requests.
    3. Zero Exposure: App ID & Secret handled server-side only via .env.
    4. Automated Plan Revocation: Immediately downgrades candidate to Free plan upon confirmed refund.
    5. Database Audit Logging: Records admin email, refund reference, timestamp, and reason.
    6. Instant Transactional Email Dispatch to customer & administrators.
    """
    order = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == req.order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Payment order reference not found.")

    if order.status == "refunded":
        raise HTTPException(
            status_code=400,
            detail=f"Order {order.order_id} has already been refunded (Refund #{order.payhere_refund_id or 'Processed'})."
        )

    if order.status == "refund_processing":
        raise HTTPException(
            status_code=400,
            detail="A refund is currently in-flight for this order. Please wait a moment."
        )

    if order.status != "success":
        raise HTTPException(
            status_code=400,
            detail=f"Only successfully verified orders can be refunded. Current status is '{order.status}'."
        )

    if not order.payhere_payment_id:
        raise HTTPException(
            status_code=400,
            detail="Order is missing the PayHere Payment ID required by the gateway to process the refund."
        )

    # 1. Anti-Double-Refund Concurrency Lock
    order.status = "refund_processing"
    db.commit()

    # 2. Execute Refund via PayHere Gateway
    try:
        refund_res = PayHereGateway.process_refund(
            payment_id=order.payhere_payment_id,
            description=req.reason,
            amount=req.amount
        )
    except Exception as e:
        order.status = "success"
        db.commit()
        logger.error("PayHere Refund Gateway Exception: %s", str(e))
        raise HTTPException(status_code=400, detail=f"Gateway communication failed: {str(e)}")

    if not refund_res.get("success"):
        order.status = "success"
        db.commit()
        logger.warning("PayHere Refund Rejected: %s", refund_res.get("msg"))
        raise HTTPException(status_code=400, detail=refund_res.get("msg", "Refund was rejected by PayHere."))

    # 3. Success State & Audit Trail Persistence
    refund_id = refund_res.get("refund_id") or "CONFIRMED"
    now = datetime.datetime.utcnow()

    order.status = "refunded"
    order.payhere_refund_id = refund_id
    order.refund_reason = req.reason.strip()
    order.refunded_at = now
    order.refunded_by_admin = current_user.email
    order.status_message = f"Refunded (Ref #{refund_id}): {req.reason.strip()}"
    order.updated_at = now

    # 4. Automated Subscription Revocation: Downgrade Candidate to Free
    candidate = db.get(User, order.user_id)
    if candidate and candidate.plan_tier == order.target_plan:
        candidate.plan_tier = "free"
        candidate.subscription_status = "expired"
        logger.info(
            "Candidate %s subscription automatically downgraded to FREE upon refund approval (Order: %s, Refund Ref: %s)",
            candidate.email, order.order_id, refund_id
        )

    db.commit()

    # 5. Dispatch Transactional Refund Emails to Customer & System Admins
    base_url = PayHereGateway.get_base_url()
    refund_amount = req.amount if req.amount and req.amount > 0 else order.amount
    customer_email = candidate.email if candidate else "customer@example.com"
    customer_name = candidate.full_name if candidate else "Customer"

    send_user_refund_processed(
        to_email=customer_email,
        full_name=customer_name,
        order_id=order.order_id,
        refund_id=refund_id,
        amount=refund_amount,
        currency=order.currency,
        reason=req.reason.strip(),
        base_url=base_url,
        background_tasks=background_tasks
    )
    send_admin_refund_alert(
        user_email=customer_email,
        full_name=customer_name,
        order_id=order.order_id,
        refund_id=refund_id,
        amount=refund_amount,
        currency=order.currency,
        reason=req.reason.strip(),
        admin_email=current_user.email,
        base_url=base_url,
        db=db,
        background_tasks=background_tasks
    )

    return AdminRefundResponse(
        success=True,
        order_id=order.order_id,
        refund_id=refund_id,
        message=f"Refund of {order.currency} {order.amount:.2f} successfully executed. Candidate has been downgraded to Free tier."
    )


@router.get("/api/admin/country-pricing")
async def admin_get_country_pricing(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Administrator endpoint: Fetch all country pricing configurations."""
    return _get_country_pricing_dict(db)


@router.post("/api/admin/country-pricing/update")
async def admin_update_country_pricing(
    req: AdminUpdateCountryPricingRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Administrator endpoint: Add or update pricing rules for a specific country."""
    country_dict = _get_country_pricing_dict(db)
    cc = req.country_code.strip().upper()

    country_dict[cc] = {
        "country_code": cc,
        "country_name": req.country_name.strip(),
        "currency_code": req.currency_code.strip().upper(),
        "currency_symbol": req.currency_symbol.strip(),
        "sprint_price": req.sprint_price.strip(),
        "plans": [p.model_dump() for p in req.plans]
    }

    json_str = json.dumps(country_dict, ensure_ascii=False)
    stmt = select(SaasSetting).where(SaasSetting.key == "saas_country_pricing_json")
    setting = db.scalars(stmt).first()
    if setting:
        setting.value = json_str
        setting.updated_at = datetime.datetime.utcnow()
    else:
        new_s = SaasSetting(
            key="saas_country_pricing_json",
            value=json_str,
            description="Dynamic Country-Specific Pricing Configurations (PPP)"
        )
        db.add(new_s)
    db.commit()

    return {"success": True, "message": f"Successfully updated pricing for country: {cc} ({req.country_name})!"}


@router.delete("/api/admin/country-pricing/{country_code}")
async def admin_delete_country_pricing(
    country_code: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Administrator endpoint: Delete custom pricing override for a specific country."""
    cc = country_code.strip().upper()
    if cc == "DEFAULT":
        raise HTTPException(status_code=400, detail="The DEFAULT pricing configuration cannot be deleted.")

    country_dict = _get_country_pricing_dict(db)
    if cc in country_dict:
        del country_dict[cc]
        json_str = json.dumps(country_dict, ensure_ascii=False)
        stmt = select(SaasSetting).where(SaasSetting.key == "saas_country_pricing_json")
        setting = db.scalars(stmt).first()
        if setting:
            setting.value = json_str
            setting.updated_at = datetime.datetime.utcnow()
            db.commit()

    return {"success": True, "message": f"Pricing override for country {cc} removed."}


@router.post("/api/admin/plans/update")
async def update_subscription_plans(
    req: UpdatePlansConfigRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Administrator endpoint to fully customize default Free, Pro, and Elite subscription plans."""
    json_str = json.dumps([p.model_dump() for p in req.plans], ensure_ascii=False)
    stmt = select(SaasSetting).where(SaasSetting.key == "plans_config_json")
    setting = db.scalars(stmt).first()
    if setting:
        setting.value = json_str
        setting.updated_at = datetime.datetime.utcnow()
    else:
        new_s = SaasSetting(
            key="plans_config_json",
            value=json_str,
            description="Dynamic Subscription Plans JSON configuration for Free, Pro, and Elite tiers"
        )
        db.add(new_s)
    
    country_dict = _get_country_pricing_dict(db)
    if "DEFAULT" in country_dict:
        country_dict["DEFAULT"]["plans"] = [p.model_dump() for p in req.plans]
        c_stmt = select(SaasSetting).where(SaasSetting.key == "saas_country_pricing_json")
        c_setting = db.scalars(c_stmt).first()
        if c_setting:
            c_setting.value = json.dumps(country_dict, ensure_ascii=False)
            c_setting.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"success": True, "message": "Subscription plans updated successfully in database!"}


# ═══════════════════════════════════════════════════════════════════
# MULTI-DURATION BILLING DISCOUNTS (1m, 3m, 6m, 12m, LIFETIME)
# ═══════════════════════════════════════════════════════════════════

@router.get("/api/admin/billing/discounts")
async def admin_get_billing_discounts(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retrieves current configurable discounts and lifetime pricing."""
    return PayHereGateway.get_billing_discounts(db=db)


@router.post("/api/admin/billing/discounts")
async def admin_update_billing_discounts(
    discounts_data: dict,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Administrator updates multi-duration discounts and lifetime pricing rules."""
    json_str = json.dumps(discounts_data, ensure_ascii=False)
    setting = db.scalars(select(SaasSetting).where(SaasSetting.key == "billing_discounts_json")).first()
    if setting:
        setting.value = json_str
        setting.updated_at = datetime.datetime.utcnow()
    else:
        setting = SaasSetting(
            key="billing_discounts_json",
            value=json_str,
            description="Configurable multi-duration subscription discounts (3m, 6m, 12m, lifetime)"
        )
        db.add(setting)
    db.commit()
    return {"success": True, "message": "Multi-duration billing discounts updated successfully!", "data": discounts_data}


# ═══════════════════════════════════════════════════════════════════
# PAYHERE SUBSCRIPTION MANAGER API (RECURRING SUBSCRIPTIONS CONSOLE)
# ═══════════════════════════════════════════════════════════════════

@router.get("/api/admin/payhere/subscriptions")
async def admin_list_payhere_subscriptions(
    current_user: User = Depends(require_admin)
):
    """
    Super Admin endpoint to list all recurring subscriptions via PayHere Subscription Manager REST API.
    Uses cached OAuth 2.0 Bearer Token.
    """
    return PayHereGateway.list_subscriptions()


@router.get("/api/admin/payhere/subscriptions/{subscription_id}")
async def admin_get_payhere_subscription(
    subscription_id: str,
    current_user: User = Depends(require_admin)
):
    """Retrieves details of a single recurring subscription from PayHere."""
    res = PayHereGateway.get_subscription(subscription_id)
    if res.get("status") == -1 and not res.get("data"):
        raise HTTPException(status_code=400, detail=res.get("msg", "Subscription not found."))
    return res


@router.get("/api/admin/payhere/subscriptions/{subscription_id}/payments")
async def admin_get_payhere_subscription_payments(
    subscription_id: str,
    current_user: User = Depends(require_admin)
):
    """Retrieves list of payments for a single PayHere recurring subscription."""
    return PayHereGateway.get_subscription_payments(subscription_id)


@router.post("/api/admin/payhere/subscriptions/{subscription_id}/retry")
async def admin_retry_payhere_subscription(
    subscription_id: str,
    current_user: User = Depends(require_admin)
):
    """Retries a failed recurring subscription charge via PayHere Subscription Manager API."""
    res = PayHereGateway.retry_subscription(subscription_id)
    if res.get("status") == -1:
        raise HTTPException(status_code=400, detail=res.get("msg", "Subscription is not eligible for retrying."))
    return res


@router.post("/api/admin/payhere/subscriptions/{subscription_id}/cancel")
async def admin_cancel_payhere_subscription(
    subscription_id: str,
    current_user: User = Depends(require_admin)
):
    """Cancels an active recurring subscription via PayHere Subscription Manager API."""
    res = PayHereGateway.cancel_subscription(subscription_id)
    if res.get("status") == -1:
        raise HTTPException(status_code=400, detail=res.get("msg", "Subscription could not be cancelled."))
    return res


# ═══════════════════════════════════════════════════════════════════════════
# PROMO CODE & CAMPAIGN MANAGEMENT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/api/admin/promos", response_model=List[AdminPromoCodeItem])
async def admin_list_promo_codes(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all created promo codes with usage metrics."""
    promos = db.scalars(select(PromoCode).order_by(PromoCode.id.desc())).all()
    results = []
    for p in promos:
        exp_str = p.expires_at.strftime("%Y-%m-%d") if p.expires_at else None
        results.append(AdminPromoCodeItem(
            id=p.id,
            code=p.code,
            code_type=p.code_type,
            discount_percent=p.discount_percent,
            free_days=p.free_days,
            target_plan=p.target_plan,
            max_uses=p.max_uses,
            times_used=p.times_used,
            is_active=p.is_active,
            expires_at=exp_str,
            created_at=p.created_at.strftime("%Y-%m-%d %H:%M"),
            created_by_admin=p.created_by_admin
        ))
    return results


@router.post("/api/admin/promos", response_model=AdminPromoCodeItem)
async def admin_create_promo_code(
    payload: AdminCreatePromoCodeRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Create a new discount percentage or free pass coupon code."""
    code_clean = payload.code.strip().upper()
    if not code_clean or len(code_clean) < 3:
        raise HTTPException(status_code=400, detail="Promo code must be at least 3 characters.")

    existing = db.scalars(select(PromoCode).where(PromoCode.code == code_clean)).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Promo code '{code_clean}' already exists.")

    expires_dt = None
    if payload.expires_at:
        try:
            expires_dt = datetime.datetime.strptime(payload.expires_at.strip(), "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid expiration date format. Use YYYY-MM-DD.")

    new_promo = PromoCode(
        code=code_clean,
        code_type=payload.code_type,
        discount_percent=max(0.0, min(100.0, float(payload.discount_percent))),
        free_days=max(0, int(payload.free_days)),
        target_plan=payload.target_plan.strip().lower() if payload.target_plan else "any",
        max_uses=max(0, int(payload.max_uses)),
        times_used=0,
        is_active=True,
        expires_at=expires_dt,
        created_by_admin=current_user.email
    )
    db.add(new_promo)
    db.commit()
    db.refresh(new_promo)

    exp_str = new_promo.expires_at.strftime("%Y-%m-%d") if new_promo.expires_at else None
    return AdminPromoCodeItem(
        id=new_promo.id,
        code=new_promo.code,
        code_type=new_promo.code_type,
        discount_percent=new_promo.discount_percent,
        free_days=new_promo.free_days,
        target_plan=new_promo.target_plan,
        max_uses=new_promo.max_uses,
        times_used=new_promo.times_used,
        is_active=new_promo.is_active,
        expires_at=exp_str,
        created_at=new_promo.created_at.strftime("%Y-%m-%d %H:%M"),
        created_by_admin=new_promo.created_by_admin
    )


@router.patch("/api/admin/promos/{promo_id}/toggle")
async def admin_toggle_promo_code(
    promo_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Toggle promo code active / inactive state."""
    promo = db.get(PromoCode, promo_id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found.")
    promo.is_active = not promo.is_active
    db.commit()
    return {"success": True, "id": promo.id, "code": promo.code, "is_active": promo.is_active}


@router.delete("/api/admin/promos/{promo_id}")
async def admin_delete_promo_code(
    promo_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Permanently delete a promo code."""
    promo = db.get(PromoCode, promo_id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found.")
    db.delete(promo)
    db.commit()
    return {"success": True, "message": f"Promo code '{promo.code}' deleted."}


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL QUEUE & OUTBOX AUDIT ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/admin/email-queue", response_model=EmailQueueListResponse)
async def admin_get_email_queue(
    status: Optional[str] = Query(None, description="Filter by status: 'pending', 'sent', 'failed'"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retrieve paginated delivery queue items and aggregate delivery stats."""
    # Compute aggregate stats
    all_items = db.scalars(select(QueuedEmail)).all()
    total = len(all_items)
    pending = sum(1 for e in all_items if e.status in ("pending", "processing"))
    sent = sum(1 for e in all_items if e.status == "sent")
    failed = sum(1 for e in all_items if e.status == "failed")

    query = select(QueuedEmail)
    if status and status.strip():
        clean_status = status.strip().lower()
        if clean_status == "pending":
            query = query.where(QueuedEmail.status.in_(["pending", "processing"]))
        else:
            query = query.where(QueuedEmail.status == clean_status)

    query = query.order_by(QueuedEmail.created_at.desc()).limit(limit)
    items = list(db.scalars(query).all())

    return EmailQueueListResponse(
        stats=EmailQueueStatsResponse(
            total=total,
            pending=pending,
            sent=sent,
            failed=failed
        ),
        items=items
    )


@router.get("/api/admin/email-queue/stats", response_model=EmailQueueStatsResponse)
async def admin_get_email_queue_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retrieve quick aggregate counts of email queue items."""
    all_items = db.scalars(select(QueuedEmail.status)).all()
    total = len(all_items)
    pending = sum(1 for s in all_items if s in ("pending", "processing"))
    sent = sum(1 for s in all_items if s == "sent")
    failed = sum(1 for s in all_items if s == "failed")
    return EmailQueueStatsResponse(
        total=total,
        pending=pending,
        sent=sent,
        failed=failed
    )


@router.post("/api/admin/email-queue/retry")
async def admin_retry_all_queued_emails(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Resets all pending & failed emails to be immediately due and triggers a batch send."""
    reset_count = retry_all_queued_emails(db=db)
    batch_stats = process_email_queue(batch_size=50, db=db)
    return {
        "success": True,
        "reset_count": reset_count,
        "batch_stats": batch_stats,
        "message": f"Processed {batch_stats.get('processed', 0)} emails: {batch_stats.get('sent', 0)} sent, {batch_stats.get('failed', 0)} failed."
    }


@router.post("/api/admin/email-queue/{email_id}/retry")
async def admin_retry_single_email(
    email_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Forces an immediate retry attempt for a specific queued email."""
    success = retry_single_queued_email(email_id, db=db)
    if success:
        return {"success": True, "message": f"Email #{email_id} was successfully delivered!"}
    else:
        item = db.get(QueuedEmail, email_id)
        last_err = item.last_error if item else "Unknown error"
        return {"success": False, "message": f"Email #{email_id} delivery failed: {last_err}"}


@router.delete("/api/admin/email-queue/{email_id}")
async def admin_delete_queued_email(
    email_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Removes an email record from the outbox queue."""
    item = db.get(QueuedEmail, email_id)
    if not item:
        raise HTTPException(status_code=404, detail="Queued email record not found.")
    db.delete(item)
    db.commit()
    return {"success": True, "message": f"Queued email #{email_id} removed."}


