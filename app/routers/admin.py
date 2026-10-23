import json
import datetime
import logging
from typing import Optional, Dict, List, Any
import io
import csv
import threading
import time
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query, Response, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import select, func, distinct, or_

from app.database import get_db, SessionLocal
from app.models import (
    User, UserResume, SaasSetting, BankPaymentSlip, OnlinePaymentOrder,
    PromoCode, PromoCodeUsage, QueuedEmail, UserReview,
    SiteVisitor, MarketingLead, MarketingCampaignLog, CookieConsentLog
)
from app.schemas import (
    AdminOverviewResponse, AdminSettingItem, AdminUpdateSettingsRequest,
    AdminUserListItem, AdminUpdateUserPlanRequest,
    AdminRefundRequest, AdminRefundResponse,
    AdminUpdateCountryPricingRequest, UpdatePlansConfigRequest,
    AdminCreatePromoCodeRequest, AdminPromoCodeItem,
    QueuedEmailItem, EmailQueueListResponse, EmailQueueStatsResponse,
    AdminCreateReviewRequest
)
from app.auth import require_admin, get_saas_setting
from app.state import build_user_response
from app.pricing import _get_country_pricing_dict
from app.payhere import PayHereGateway
from app.email_service import (
    send_user_refund_processed, send_admin_refund_alert,
    process_email_queue, retry_single_queued_email, retry_all_queued_emails,
    send_promotional_campaign_email, render_marketing_campaign_html
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
    elif tier == "sprint":
        user.sprint_ats_downloads_count = 0
        user.sprint_visual_downloads_count = 0
        user.sprint_ai_generations_count = 0
        days = max(1, req.duration_days) if req.duration_days else 7
        user.subscription_started_at = now
        user.subscription_expires_at = now + datetime.timedelta(days=days)
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


@router.delete("/api/admin/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Permanently delete a spam, bot, or malicious user account."""
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Administrators cannot delete their own account.")

    stmt = select(User).where(User.id == user_id)
    user = db.scalars(stmt).first()
    if not user:
        raise HTTPException(status_code=404, detail="Target user not found.")

    if user.is_admin:
        raise HTTPException(status_code=403, detail="Cannot delete an administrator account.")

    target_email = user.email
    db.delete(user)
    db.commit()

    return {
        "success": True,
        "message": f"User #{user_id} ({target_email}) has been permanently deleted."
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
        actual_tier = "sprint"
        candidate.sprint_ats_downloads_count = 0
        candidate.sprint_visual_downloads_count = 0
        candidate.sprint_ai_generations_count = 0
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

    # Affiliate Revenue-Share Engine: Record commission if user was referred
    try:
        from app.services.affiliate_service import record_commission_on_payment
        record_commission_on_payment(
            buyer=candidate,
            order_amount=slip.amount_paid,
            order_id=f"BANK-SLIP-{slip.id}",
            db=db
        )
    except Exception as aff_err:
        logger.warning("Affiliate commission hook warning for bank slip %s: %s", slip.id, aff_err)

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


@router.post("/api/admin/payhere/orders/{order_id}/sync")
async def admin_sync_payhere_order(
    order_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Admin endpoint to actively query PayHere Retrieval API and sync payment status."""
    from app.routers.payments import sync_order_status_from_payhere
    order = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order reference not found.")

    new_status = sync_order_status_from_payhere(order, db, background_tasks)
    db.refresh(order)
    return {
        "success": True,
        "order_id": order.order_id,
        "status": order.status,
        "payhere_payment_id": order.payhere_payment_id,
        "status_message": order.status_message
    }


class AdminManualOrderActivationRequest(BaseModel):
    payment_id: Optional[str] = None
    admin_notes: Optional[str] = None


@router.post("/api/admin/payhere/orders/{order_id}/activate")
async def admin_manual_activate_payhere_order(
    order_id: str,
    background_tasks: BackgroundTasks,
    payload: Optional[AdminManualOrderActivationRequest] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Super Admin Override: Manually activates a candidate's subscription order
    when verified in PayHere Merchant Portal (e.g. status Authorized/Completed).
    """
    from app.routers.payments import activate_order_and_upgrade_candidate
    order = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == order_id)).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order reference not found.")

    pay_id = (payload.payment_id if payload else None) or order.payhere_payment_id or f"ADMIN-{int(time.time())}"
    notes = (payload.admin_notes if payload else None) or f"Manually verified & activated by Admin ({current_user.email})"

    activate_order_and_upgrade_candidate(
        order=order,
        db=db,
        payment_id=pay_id,
        payment_method="PayHere Verified",
        status_note=notes,
        background_tasks=background_tasks
    )
    db.refresh(order)
    return {
        "success": True,
        "message": f"Order #{order.order_id} has been activated successfully! Candidate upgraded.",
        "order_id": order.order_id,
        "status": order.status,
        "payhere_payment_id": order.payhere_payment_id
    }


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

    # 2. Execute Refund via PayHere Gateway OR Record Manual Refund
    if getattr(req, "manual_refund", False):
        refund_id = (
            req.refund_id.strip()
            if getattr(req, "refund_id", None) and req.refund_id.strip()
            else f"MANUAL-{int(datetime.datetime.utcnow().timestamp())}"
        )
    else:
        try:
            refund_res = PayHereGateway.process_refund(
                payment_id=order.payhere_payment_id,
                description=req.reason,
                amount=req.amount,
            )
            if not refund_res.get("success"):
                order.status = "success"
                db.commit()
                logger.warning("PayHere Refund Rejected: %s", refund_res.get("msg"))
                raise HTTPException(
                    status_code=400,
                    detail=refund_res.get("msg", "Refund was rejected by PayHere."),
                )
            refund_id = refund_res.get("refund_id") or "CONFIRMED"
        except HTTPException:
            raise
        except Exception as e:
            order.status = "success"
            db.commit()
            err_msg = str(e)
            if "403" in err_msg or "Cloudflare" in err_msg:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "PayHere Live Refund API is blocked by Cloudflare (HTTP 403) pending server IP whitelisting by support@payhere.lk. "
                        "Please issue the refund directly in your PayHere Merchant Portal (https://www.payhere.lk -> Payments), "
                        "then check 'Record Manual / Portal Refund' in this modal to revoke the Pro subscription in DreemFolio."
                    ),
                )
            logger.error("PayHere Refund Gateway Exception: %s", err_msg)
            raise HTTPException(
                status_code=400, detail=f"Gateway communication failed: {err_msg}"
            )
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


# ═══════════════════════════════════════════════════════════════════════════════
# ADMIN USER REVIEWS & TESTIMONIALS CONTROL
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/api/admin/reviews")
async def get_admin_reviews(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retrieve all candidate feedback, star ratings, and showcase testimonials for moderation."""
    reviews = db.scalars(select(UserReview).order_by(UserReview.created_at.desc())).all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "reviewer_name": r.reviewer_name,
            "reviewer_role": r.reviewer_role,
            "reviewer_company": r.reviewer_company or "",
            "rating": r.rating,
            "review_text": r.review_text,
            "avatar_url": r.avatar_url or "",
            "is_approved": r.is_approved,
            "is_featured": r.is_featured,
            "source": r.source,
            "created_at": r.created_at.strftime("%b %d, %Y - %I:%M %p")
        }
        for r in reviews
    ]


@router.post("/api/admin/reviews/create")
async def admin_create_review(
    req: AdminCreateReviewRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Add a verified showcase review / testimonial directly from the Admin Panel."""
    review = UserReview(
        reviewer_name=req.reviewer_name.strip(),
        reviewer_role=req.reviewer_role.strip(),
        reviewer_company=req.reviewer_company.strip() if req.reviewer_company else None,
        rating=max(1, min(5, req.rating)),
        review_text=req.review_text.strip(),
        avatar_url=req.avatar_url.strip() if req.avatar_url else None,
        is_approved=req.is_approved,
        is_featured=req.is_featured,
        source="admin_showcase",
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow()
    )
    db.add(review)
    db.commit()
    db.refresh(review)
    return {"success": True, "id": review.id, "message": "Showcase testimonial added successfully."}


@router.post("/api/admin/reviews/{review_id}/toggle-approve")
async def admin_toggle_approve_review(
    review_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Toggle publication approval status for a candidate review."""
    review = db.scalar(select(UserReview).where(UserReview.id == review_id))
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found.")
    review.is_approved = not review.is_approved
    review.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"success": True, "is_approved": review.is_approved}


@router.post("/api/admin/reviews/{review_id}/toggle-feature")
async def admin_toggle_feature_review(
    review_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Toggle whether a review appears prominently in the Landing Page showcase."""
    review = db.scalar(select(UserReview).where(UserReview.id == review_id))
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found.")
    review.is_featured = not review.is_featured
    review.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"success": True, "is_featured": review.is_featured}


@router.delete("/api/admin/reviews/{review_id}")
async def admin_delete_review(
    review_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Permanently delete a spam or inappropriate review."""
    review = db.scalar(select(UserReview).where(UserReview.id == review_id))
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found.")
    db.delete(review)
    db.commit()
    return {"success": True, "message": f"Review #{review_id} has been permanently deleted."}


# ═══════════════════════════════════════════════════════════════════════════════
# VISITOR ANALYTICS, HUMAN PROOF & SALES MARKETING LEADS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/api/admin/analytics/stats")
async def get_admin_analytics_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Real Human Traffic Proof & Visitor Analytics.
    Differentiates verified human sessions from raw Cloudflare asset requests and bot crawlers.
    """
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)

    # 1. Human Unique Visitors & Pageviews
    total_human_visitors = db.scalar(
        select(func.count(distinct(SiteVisitor.visitor_hash))).where(SiteVisitor.is_bot == False)
    ) or 0

    unique_visitors_today = db.scalar(
        select(func.count(distinct(SiteVisitor.visitor_hash))).where(
            SiteVisitor.is_bot == False,
            SiteVisitor.created_at >= today_start
        )
    ) or 0

    unique_visitors_7d = db.scalar(
        select(func.count(distinct(SiteVisitor.visitor_hash))).where(
            SiteVisitor.is_bot == False,
            SiteVisitor.created_at >= seven_days_ago
        )
    ) or 0

    pageviews_today = db.scalar(
        select(func.count(SiteVisitor.id)).where(
            SiteVisitor.is_bot == False,
            SiteVisitor.created_at >= today_start
        )
    ) or 0

    pageviews_all_time = db.scalar(
        select(func.count(SiteVisitor.id)).where(SiteVisitor.is_bot == False)
    ) or 0

    # 2. Automated Bots & Crawlers Filtered
    bot_requests_filtered = db.scalar(
        select(func.count(SiteVisitor.id)).where(SiteVisitor.is_bot == True)
    ) or 0

    # 3. Cookie Consents & Conversion
    cookie_consents_count = db.scalar(select(func.count(CookieConsentLog.id))) or 0
    cookie_consent_rate = round((cookie_consents_count / max(total_human_visitors, 1)) * 100, 1)

    # 4. Total Marketing Leads Captured
    total_leads_count = db.scalar(select(func.count(MarketingLead.id))) or 0

    # 5. Cloudflare requests proof multiplier (Avg web page has ~25 sub-requests: JS, CSS, images, fonts)
    cloudflare_multiplier = 25
    estimated_cloudflare_requests = (pageviews_all_time * cloudflare_multiplier) + (bot_requests_filtered * 5)

    # 6. Top Visited Pages
    top_pages_rows = db.execute(
        select(SiteVisitor.path, func.count(SiteVisitor.id).label("hits"))
        .where(SiteVisitor.is_bot == False)
        .group_by(SiteVisitor.path)
        .order_by(func.count(SiteVisitor.id).desc())
        .limit(7)
    ).all()
    top_pages = [{"path": row[0], "hits": row[1]} for row in top_pages_rows]

    # 7. Top Countries
    top_countries_rows = db.execute(
        select(SiteVisitor.country_code, func.count(SiteVisitor.id).label("hits"))
        .where(SiteVisitor.is_bot == False)
        .group_by(SiteVisitor.country_code)
        .order_by(func.count(SiteVisitor.id).desc())
        .limit(7)
    ).all()
    top_countries = [{"country": row[0] or "UNKNOWN", "hits": row[1]} for row in top_countries_rows]

    # 8. Device Breakdown
    device_rows = db.execute(
        select(SiteVisitor.device_type, func.count(SiteVisitor.id).label("hits"))
        .where(SiteVisitor.is_bot == False)
        .group_by(SiteVisitor.device_type)
    ).all()
    device_stats = {row[0]: row[1] for row in device_rows}

    # 9. Top Referrers
    referrer_rows = db.execute(
        select(SiteVisitor.referrer, func.count(SiteVisitor.id).label("hits"))
        .where(SiteVisitor.is_bot == False, SiteVisitor.referrer.isnot(None), SiteVisitor.referrer != "")
        .group_by(SiteVisitor.referrer)
        .order_by(func.count(SiteVisitor.id).desc())
        .limit(7)
    ).all()
    top_referrers = [{"referrer": row[0], "hits": row[1]} for row in referrer_rows]

    # 10. Recent 35 Verified Human Visitors
    recent_rows = db.scalars(
        select(SiteVisitor)
        .where(SiteVisitor.is_bot == False)
        .order_by(SiteVisitor.id.desc())
        .limit(35)
    ).all()
    recent_visitors = [
        {
            "id": r.id,
            "hash": f"{r.visitor_hash[:8]}..." if r.visitor_hash else "anon",
            "country": r.country_code or "UNKNOWN",
            "ip_anonymized": r.ip_address or "---",
            "path": r.path,
            "referrer": r.referrer or "Direct / None",
            "device": r.device_type,
            "cookie_consented": r.cookie_consented,
            "time": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "---"
        }
        for r in recent_rows
    ]

    return {
        "unique_visitors_today": unique_visitors_today,
        "unique_visitors_7d": unique_visitors_7d,
        "total_human_visitors": total_human_visitors,
        "pageviews_today": pageviews_today,
        "pageviews_all_time": pageviews_all_time,
        "bot_requests_filtered": bot_requests_filtered,
        "cookie_consents_count": cookie_consents_count,
        "cookie_consent_rate": cookie_consent_rate,
        "total_leads_count": total_leads_count,
        "estimated_cloudflare_requests": estimated_cloudflare_requests,
        "top_pages": top_pages,
        "top_countries": top_countries,
        "device_stats": device_stats,
        "top_referrers": top_referrers,
        "recent_visitors": recent_visitors
    }


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL MARKETING, CSV IMPORTS & PROMOTIONAL CAMPAIGN ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class SendCampaignRequest(BaseModel):
    target_type: str = "selected"  # "selected", "all", "never_sent", "position", "test"
    selected_ids: Optional[List[int]] = None
    position_filter: Optional[str] = None
    test_email: Optional[str] = None
    subject: str = "Land More Interviews with DreemFolio AI - ATS Resume & Live Portfolio"
    template_type: str = "promotional_offer"
    headline: Optional[str] = "Accelerate Your Career with a Recruiter-Approved ATS Resume"
    message_body: Optional[str] = None
    cta_text: Optional[str] = "Check Your ATS Score Free →"
    cta_url: Optional[str] = "https://www.dreemfolio.com/ats-resume-checker"


class PreviewEmailRequest(BaseModel):
    subject: str = "Land More Interviews with DreemFolio AI"
    headline: Optional[str] = "Accelerate Your Career with a Recruiter-Approved ATS Resume"
    message_body: Optional[str] = None
    cta_text: Optional[str] = "Check Your ATS Score Free →"
    cta_url: Optional[str] = "https://www.dreemfolio.com/ats-resume-checker"
    sample_name: Optional[str] = "Dimmithra Perera"
    sample_position: Optional[str] = "Mobile Application Developer"


class BatchDeleteLeadsRequest(BaseModel):
    lead_ids: List[int]


class ClearAllLeadsRequest(BaseModel):
    position: Optional[str] = None
    status: Optional[str] = None
    confirm: bool = False


class ManualLeadImportItem(BaseModel):
    email: str
    name: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None


class ManualLeadsImportRequest(BaseModel):
    raw_csv: Optional[str] = None
    leads: Optional[List[ManualLeadImportItem]] = None
    campaign_tag: Optional[str] = "csv_import"


def parse_csv_contacts(csv_text: str) -> List[Dict[str, str]]:
    """
    Robust CSV parser that detects Position, Name, Email, Phone columns
    regardless of capitalization, order, or delimiter.
    """
    contacts = []
    if not csv_text or not csv_text.strip():
        return contacts

    clean_text = csv_text.strip().replace("\r\n", "\n").replace("\r", "\n")
    lines = [l for l in clean_text.split("\n") if l.strip()]
    if not lines:
        return contacts

    reader = csv.reader(lines)
    header = next(reader, None)
    if not header:
        return contacts

    col_map = {}
    for idx, raw_h in enumerate(header):
        h = raw_h.strip().lower()
        if any(k in h for k in ["email", "e-mail", "mail"]):
            col_map["email"] = idx
        elif any(k in h for k in ["name", "full name", "candidate", "applicant"]):
            col_map["name"] = idx
        elif any(k in h for k in ["position", "role", "title", "job", "designation"]):
            col_map["position"] = idx
        elif any(k in h for k in ["phone", "mobile", "tel", "contact"]):
            col_map["phone"] = idx

    # If header didn't specify 'email', check if header was actually data row
    if "email" not in col_map:
        for idx, cell in enumerate(header):
            if "@" in cell:
                col_map["email"] = idx
            elif idx == 0 and "position" not in col_map:
                col_map["position"] = 0
            elif idx == 1 and "name" not in col_map:
                col_map["name"] = 1
            elif idx == 3 and "phone" not in col_map:
                col_map["phone"] = 3
        # treat first row as data
        row_dict = {k: header[idx].strip() for k, idx in col_map.items() if idx < len(header)}
        if row_dict.get("email") and "@" in row_dict["email"]:
            contacts.append(row_dict)

    for row in reader:
        if not row:
            continue
        row_dict = {}
        for k, idx in col_map.items():
            if idx < len(row):
                row_dict[k] = row[idx].strip()

        email = row_dict.get("email", "").strip()
        if email and "@" in email:
            contacts.append(row_dict)

    return contacts


def _dispatch_campaign_worker(
    campaign_log_id: int,
    target_lead_ids: List[int],
    subject_template: str,
    headline_template: str,
    message_body_template: Optional[str],
    cta_text: str,
    cta_url: str
):
    """Background worker that dispatches personalized marketing emails with rate-limiting."""
    db = SessionLocal()
    sent_count = 0
    failed_count = 0
    try:
        leads = db.scalars(
            select(MarketingLead).where(MarketingLead.id.in_(target_lead_ids))
        ).all()

        for lead in leads:
            try:
                cand_name = (lead.name or "").strip() or "there"
                first_name = cand_name.split()[0] if cand_name != "there" else "there"
                cand_pos = (lead.position or "").strip() or "Professional"

                sub = subject_template.replace("{{name}}", first_name).replace("{name}", first_name)
                sub = sub.replace("{{position}}", cand_pos).replace("{position}", cand_pos)

                hd = headline_template.replace("{{name}}", first_name).replace("{name}", first_name)
                hd = hd.replace("{{position}}", cand_pos).replace("{position}", cand_pos)

                msg_body = None
                if message_body_template:
                    msg_body = message_body_template.replace("{{name}}", first_name).replace("{name}", first_name)
                    msg_body = msg_body.replace("{{position}}", cand_pos).replace("{position}", cand_pos)

                success = send_promotional_campaign_email(
                    to_email=lead.email,
                    subject=sub,
                    name=first_name,
                    position=cand_pos if lead.position else None,
                    headline=hd,
                    message_body=msg_body,
                    cta_text=cta_text,
                    cta_url=cta_url
                )

                if success:
                    lead.status = "sent"
                    lead.send_count = (lead.send_count or 0) + 1
                    lead.last_sent_at = datetime.datetime.utcnow()
                    lead.last_error = None
                    sent_count += 1
                else:
                    lead.status = "failed"
                    lead.last_error = "Email dispatcher failed or SMTP rejected recipient."
                    failed_count += 1

                db.commit()
                # Friendly delay between sends
                time.sleep(0.35)
            except Exception as item_err:
                logger.error("Error sending marketing campaign email to %s: %s", lead.email, item_err)
                lead.status = "failed"
                lead.last_error = str(item_err)[:350]
                failed_count += 1
                db.commit()

        # Update Campaign Log
        log = db.scalar(select(MarketingCampaignLog).where(MarketingCampaignLog.id == campaign_log_id))
        if log:
            log.total_sent = sent_count
            log.total_failed = failed_count
            db.commit()

    except Exception as err:
        logger.error("Fatal exception in marketing campaign background thread: %s", err)
    finally:
        db.close()


@router.get("/api/admin/marketing/stats")
async def get_admin_marketing_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Returns analytics and summary metrics for marketing leads and promotional campaigns."""
    total_leads = db.scalar(select(func.count(MarketingLead.id))) or 0
    total_sent = db.scalar(select(func.count(MarketingLead.id)).where(MarketingLead.send_count > 0)) or 0
    total_never_sent = db.scalar(select(func.count(MarketingLead.id)).where(or_(MarketingLead.send_count == 0, MarketingLead.send_count.is_(None)))) or 0
    total_failed = db.scalar(select(func.count(MarketingLead.id)).where(MarketingLead.status == "failed")) or 0

    # Distinct positions breakdown
    pos_rows = db.execute(
        select(MarketingLead.position, func.count(MarketingLead.id))
        .where(MarketingLead.position.isnot(None), MarketingLead.position != "")
        .group_by(MarketingLead.position)
        .order_by(func.count(MarketingLead.id).desc())
        .limit(20)
    ).all()
    positions = [{"position": r[0], "count": r[1]} for r in pos_rows]

    # Recent campaign logs
    campaigns = db.scalars(
        select(MarketingCampaignLog).order_by(MarketingCampaignLog.id.desc()).limit(10)
    ).all()

    return {
        "total_leads": total_leads,
        "total_sent": total_sent,
        "total_never_sent": total_never_sent,
        "total_failed": total_failed,
        "positions": positions,
        "recent_campaigns": [
            {
                "id": c.id,
                "subject": c.subject,
                "template_type": c.template_type,
                "headline": c.headline,
                "target_filter": c.target_filter,
                "total_targeted": c.total_targeted,
                "total_sent": c.total_sent,
                "total_failed": c.total_failed,
                "admin_user": c.admin_user,
                "created_at": c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else "---"
            }
            for c in campaigns
        ]
    }


@router.get("/api/admin/marketing/leads")
async def get_admin_marketing_leads(
    search: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    limit: int = Query(1000, le=2000),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Retrieve collected sales & marketing lead records with advanced filters."""
    query = select(MarketingLead)

    if search and search.strip():
        q = f"%{search.strip()}%"
        query = query.where(
            or_(
                MarketingLead.email.ilike(q),
                MarketingLead.name.ilike(q),
                MarketingLead.position.ilike(q),
                MarketingLead.phone.ilike(q)
            )
        )

    if position and position.strip() and position != "all":
        query = query.where(MarketingLead.position == position.strip())

    if status and status.strip() and status != "all":
        if status == "never_sent":
            query = query.where(or_(MarketingLead.send_count == 0, MarketingLead.send_count.is_(None)))
        elif status == "sent":
            query = query.where(MarketingLead.send_count > 0)
        else:
            query = query.where(MarketingLead.status == status.strip())

    if tag and tag.strip() and tag != "all":
        query = query.where(MarketingLead.campaign_tag == tag.strip())

    leads = db.scalars(query.order_by(MarketingLead.id.desc()).limit(limit)).all()

    return [
        {
            "id": lead.id,
            "email": lead.email,
            "name": lead.name or "",
            "position": lead.position or "",
            "phone": lead.phone or "",
            "source": lead.source,
            "campaign_tag": lead.campaign_tag or "",
            "status": lead.status or "pending",
            "send_count": lead.send_count or 0,
            "last_sent_at": lead.last_sent_at.strftime("%Y-%m-%d %H:%M") if lead.last_sent_at else None,
            "last_error": lead.last_error,
            "created_at": lead.created_at.strftime("%Y-%m-%d %H:%M") if lead.created_at else "---"
        }
        for lead in leads
    ]


@router.post("/api/admin/marketing/leads/import-csv")
async def import_marketing_leads_csv_file(
    file: UploadFile = File(...),
    campaign_tag: Optional[str] = Form("csv_import"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Import contacts from uploaded CSV file into the database."""
    content_bytes = await file.read()
    try:
        csv_text = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        csv_text = content_bytes.decode("latin-1", errors="ignore")

    parsed_contacts = parse_csv_contacts(csv_text)
    if not parsed_contacts:
        raise HTTPException(status_code=400, detail="No valid contacts with email addresses found in CSV.")

    imported_count = 0
    updated_count = 0

    for item in parsed_contacts:
        clean_email = item.get("email", "").strip().lower()
        if not clean_email or "@" not in clean_email:
            continue

        existing = db.scalar(select(MarketingLead).where(MarketingLead.email == clean_email))
        if existing:
            # Update fields if new data present
            if item.get("name"):
                existing.name = item["name"]
            if item.get("position"):
                existing.position = item["position"]
            if item.get("phone"):
                existing.phone = item["phone"]
            if campaign_tag:
                existing.campaign_tag = campaign_tag
            existing.updated_at = datetime.datetime.utcnow()
            updated_count += 1
        else:
            new_lead = MarketingLead(
                email=clean_email,
                name=item.get("name"),
                position=item.get("position"),
                phone=item.get("phone"),
                source="csv_upload",
                campaign_tag=campaign_tag or "csv_import",
                status="pending",
                send_count=0
            )
            db.add(new_lead)
            imported_count += 1

    db.commit()
    total_leads = db.scalar(select(func.count(MarketingLead.id))) or 0

    return {
        "success": True,
        "message": f"Successfully processed {len(parsed_contacts)} contacts: {imported_count} imported as new, {updated_count} updated.",
        "imported": imported_count,
        "updated": updated_count,
        "total_leads": total_leads
    }


@router.post("/api/admin/marketing/leads/import-text")
async def import_marketing_leads_raw_text(
    payload: ManualLeadsImportRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Import contacts via pasted CSV text or JSON contact list."""
    contacts_to_process = []

    if payload.raw_csv and payload.raw_csv.strip():
        contacts_to_process = parse_csv_contacts(payload.raw_csv)
    elif payload.leads:
        contacts_to_process = [
            {
                "email": l.email,
                "name": l.name or "",
                "position": l.position or "",
                "phone": l.phone or ""
            }
            for l in payload.leads
        ]

    if not contacts_to_process:
        raise HTTPException(status_code=400, detail="No valid contact data provided.")

    imported_count = 0
    updated_count = 0

    for item in contacts_to_process:
        clean_email = item.get("email", "").strip().lower()
        if not clean_email or "@" not in clean_email:
            continue

        existing = db.scalar(select(MarketingLead).where(MarketingLead.email == clean_email))
        if existing:
            if item.get("name"):
                existing.name = item["name"]
            if item.get("position"):
                existing.position = item["position"]
            if item.get("phone"):
                existing.phone = item["phone"]
            if payload.campaign_tag:
                existing.campaign_tag = payload.campaign_tag
            existing.updated_at = datetime.datetime.utcnow()
            updated_count += 1
        else:
            new_lead = MarketingLead(
                email=clean_email,
                name=item.get("name"),
                position=item.get("position"),
                phone=item.get("phone"),
                source="pasted_csv",
                campaign_tag=payload.campaign_tag or "pasted_csv",
                status="pending",
                send_count=0
            )
            db.add(new_lead)
            imported_count += 1

    db.commit()
    total_leads = db.scalar(select(func.count(MarketingLead.id))) or 0

    return {
        "success": True,
        "message": f"Processed {len(contacts_to_process)} contacts: {imported_count} new imported, {updated_count} updated.",
        "imported": imported_count,
        "updated": updated_count,
        "total_leads": total_leads
    }


@router.post("/api/admin/marketing/preview-email")
async def preview_marketing_email(
    payload: PreviewEmailRequest,
    current_user: User = Depends(require_admin)
):
    """Renders HTML preview of promotional campaign email with dummy or sample variables."""
    rendered_html = render_marketing_campaign_html(
        name=payload.sample_name or "Candidate",
        position=payload.sample_position or "Mobile Application Developer",
        headline=payload.headline,
        message_body=payload.message_body,
        cta_text=payload.cta_text,
        cta_url=payload.cta_url
    )
    return {"html": rendered_html}


@router.post("/api/admin/marketing/send-campaign")
async def send_marketing_campaign(
    payload: SendCampaignRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Launches a promotional email campaign.
    Supports targeting by: 'selected', 'never_sent', 'position', 'all', or 'test'.
    """
    if payload.target_type == "test":
        target_email = (payload.test_email or "").strip() or current_user.email
        if not target_email or "@" not in target_email:
            raise HTTPException(status_code=400, detail="Invalid test email address.")

        sample_name = current_user.full_name or "Administrator"
        sample_position = payload.position_filter or "Software Engineering Intern"
        test_sub = f"[TEST PREVIEW] {payload.subject}".replace("{{name}}", sample_name).replace("{name}", sample_name)
        test_sub = test_sub.replace("{{position}}", sample_position).replace("{position}", sample_position)
        test_hd = (payload.headline or "").replace("{{name}}", sample_name).replace("{name}", sample_name)
        test_hd = test_hd.replace("{{position}}", sample_position).replace("{position}", sample_position)
        test_msg_body = payload.message_body
        if test_msg_body:
            test_msg_body = test_msg_body.replace("{{name}}", sample_name).replace("{name}", sample_name)
            test_msg_body = test_msg_body.replace("{{position}}", sample_position).replace("{position}", sample_position)

        success = send_promotional_campaign_email(
            to_email=target_email,
            subject=test_sub,
            name=sample_name,
            position=sample_position,
            headline=test_hd,
            message_body=test_msg_body,
            cta_text=payload.cta_text,
            cta_url=payload.cta_url
        )
        return {
            "success": success,
            "message": f"Test promotional email dispatched to {target_email} successfully."
        }

    # Bulk Dispatch Logic
    if payload.target_type == "selected":
        if not payload.selected_ids:
            raise HTTPException(status_code=400, detail="No lead IDs selected.")
        target_ids = db.scalars(
            select(MarketingLead.id).where(MarketingLead.id.in_(payload.selected_ids))
        ).all()
    elif payload.target_type == "never_sent":
        target_ids = db.scalars(
            select(MarketingLead.id).where(
                or_(MarketingLead.send_count == 0, MarketingLead.send_count.is_(None))
            )
        ).all()
    elif payload.target_type == "position":
        if not payload.position_filter:
            raise HTTPException(status_code=400, detail="Position filter is required.")
        target_ids = db.scalars(
            select(MarketingLead.id).where(MarketingLead.position == payload.position_filter)
        ).all()
    elif payload.target_type == "all":
        target_ids = db.scalars(select(MarketingLead.id)).all()
    else:
        raise HTTPException(status_code=400, detail=f"Invalid target_type: {payload.target_type}")

    if not target_ids:
        raise HTTPException(status_code=400, detail="No matching leads found for this campaign criteria.")

    # Record campaign log
    campaign_log = MarketingCampaignLog(
        subject=payload.subject,
        template_type=payload.template_type,
        headline=payload.headline,
        target_filter=f"{payload.target_type}:{payload.position_filter or 'none'}",
        total_targeted=len(target_ids),
        total_sent=0,
        total_failed=0,
        admin_user=current_user.email
    )
    db.add(campaign_log)
    db.commit()
    db.refresh(campaign_log)

    # Spawn background daemon worker thread
    thread = threading.Thread(
        target=_dispatch_campaign_worker,
        args=(
            campaign_log.id,
            list(target_ids),
            payload.subject,
            payload.headline or "Accelerate Your Career with DreemFolio AI",
            payload.message_body,
            payload.cta_text or "Check ATS Score Free →",
            payload.cta_url or "https://www.dreemfolio.com/ats-resume-checker"
        ),
        daemon=True
    )
    thread.start()

    return {
        "success": True,
        "message": f"Promotional campaign successfully launched! Sending to {len(target_ids)} leads in background.",
        "campaign_id": campaign_log.id,
        "targeted_count": len(target_ids)
    }


@router.post("/api/admin/marketing/leads/batch-delete")
async def batch_delete_marketing_leads(
    payload: BatchDeleteLeadsRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Batch delete selected marketing leads."""
    if not payload.lead_ids:
        raise HTTPException(status_code=400, detail="No lead IDs provided.")

    leads = db.scalars(select(MarketingLead).where(MarketingLead.id.in_(payload.lead_ids))).all()
    deleted_count = len(leads)
    for l in leads:
        db.delete(l)
    db.commit()

    return {
        "success": True,
        "message": f"Successfully deleted {deleted_count} lead(s).",
        "deleted_count": deleted_count
    }


@router.get("/api/admin/marketing/leads/export-csv")
async def export_marketing_leads_csv(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Download all saved marketing leads as an enriched CSV file."""
    leads = db.scalars(
        select(MarketingLead).order_by(MarketingLead.id.desc())
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Full Name", "Position / Role", "Email Address", "Phone",
        "Status", "Send Count", "Last Sent At (UTC)", "Campaign Tag", "Source", "Captured At (UTC)"
    ])

    for lead in leads:
        writer.writerow([
            lead.id,
            lead.name or "",
            lead.position or "",
            lead.email,
            lead.phone or "",
            lead.status or "pending",
            lead.send_count or 0,
            lead.last_sent_at.strftime("%Y-%m-%d %H:%M:%S") if lead.last_sent_at else "",
            lead.campaign_tag or "",
            lead.source,
            lead.created_at.strftime("%Y-%m-%d %H:%M:%S") if lead.created_at else ""
        ])

    csv_data = output.getvalue()
    today_date = datetime.date.today().isoformat()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="dreemfolio_leads_{today_date}.csv"'
        }
    )


@router.delete("/api/admin/marketing/leads/{lead_id}")
async def delete_marketing_lead(
    lead_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a single lead from marketing list."""
    lead = db.scalar(select(MarketingLead).where(MarketingLead.id == lead_id))
    if not lead:
        raise HTTPException(status_code=404, detail="Lead record not found.")
    db.delete(lead)
    db.commit()
    return {"success": True, "message": f"Lead #{lead_id} removed successfully."}


@router.delete("/api/admin/marketing/campaigns/{campaign_id}")
async def delete_marketing_campaign_log(
    campaign_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete a campaign audit log record."""
    log = db.scalar(select(MarketingCampaignLog).where(MarketingCampaignLog.id == campaign_id))
    if not log:
        raise HTTPException(status_code=404, detail="Campaign log not found.")
    db.delete(log)
    db.commit()
    return {"success": True, "message": f"Campaign log #{campaign_id} deleted."}


@router.post("/api/admin/marketing/leads/clear-all")
async def clear_all_marketing_leads(
    payload: ClearAllLeadsRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Delete all leads or filtered leads matching position/status with confirmation."""
    if not payload.confirm:
        raise HTTPException(status_code=400, detail="Confirmation required to delete leads.")

    query = select(MarketingLead)
    if payload.position and payload.position != "all":
        query = query.where(MarketingLead.position == payload.position)
    if payload.status and payload.status != "all":
        if payload.status == "never_sent":
            query = query.where(or_(MarketingLead.send_count == 0, MarketingLead.send_count.is_(None)))
        elif payload.status == "sent":
            query = query.where(MarketingLead.send_count > 0)
        else:
            query = query.where(MarketingLead.status == payload.status)

    leads_to_delete = db.scalars(query).all()
    count = len(leads_to_delete)
    for lead in leads_to_delete:
        db.delete(lead)
    db.commit()

    return {"success": True, "message": f"Successfully deleted {count} lead(s).", "deleted_count": count}


@router.post("/api/admin/marketing/sync-users")
async def sync_registered_users_to_marketing_leads(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Syncs all active registered users into the marketing leads database,
    automatically deduplicating so existing emails are never added twice.
    """
    users = db.scalars(select(User).where(User.is_active == True)).all()
    added_count = 0
    skipped_count = 0

    for u in users:
        clean_email = (u.email or "").strip().lower()
        if not clean_email or "@" not in clean_email:
            continue

        existing = db.scalar(select(MarketingLead).where(MarketingLead.email == clean_email))
        if existing:
            skipped_count += 1
            continue

        lead = MarketingLead(
            name=u.full_name or "Registered User",
            email=clean_email,
            position="Registered Candidate",
            campaign_tag="registered_users",
            source="user_registration",
            created_at=datetime.datetime.utcnow()
        )
        db.add(lead)
        added_count += 1

    db.commit()
    return {
        "success": True,
        "message": f"Successfully synced {added_count} registered user(s) into campaign leads ({skipped_count} existing/duplicates skipped).",
        "added_count": added_count,
        "skipped_count": skipped_count
    }


@router.get("/api/admin/ai/usage-stats")
async def get_admin_ai_usage_stats(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Returns granular Gemini AI token telemetry, daily/weekly/monthly metrics,
    estimated cost breakdown ($ and LKR), and top 10 AI consuming users.
    """
    from app.services.ai_tracking_service import get_ai_metrics_overview
    return get_ai_metrics_overview(db)


class GrowthBotConfigUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    daily_limit: Optional[int] = None
    preferred_language: Optional[str] = None
    enable_affiliate_booster: Optional[bool] = None
    enable_resume_booster: Optional[bool] = None
    enable_portfolio_booster: Optional[bool] = None
    morning_window_start: Optional[str] = None
    morning_window_end: Optional[str] = None
    evening_window_start: Optional[str] = None
    evening_window_end: Optional[str] = None

class GrowthBotTriggerRequest(BaseModel):
    max_to_send: Optional[int] = 5


@router.get("/api/admin/growth-bot/status")
async def get_growth_bot_status(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Returns real-time configuration, window status, and recent activity logs for Autonomous Growth Bot."""
    from app.services.growth_bot import (
        get_or_create_growth_bot_config, reset_daily_limits_if_needed,
        get_prime_window_info
    )
    from app.models import GrowthBotLog
    cfg = get_or_create_growth_bot_config(db)
    reset_daily_limits_if_needed(cfg, db)
    window_info = get_prime_window_info(cfg)

    recent_logs = db.scalars(
        select(GrowthBotLog).order_by(GrowthBotLog.created_at.desc()).limit(25)
    ).all()

    logs_data = [
        {
            "id": l.id,
            "action": l.action,
            "recipient_email": l.recipient_email,
            "recipient_name": l.recipient_name,
            "segment": l.segment,
            "language": l.language,
            "subject": l.subject,
            "details": l.details,
            "created_at": l.created_at.strftime("%Y-%m-%d %I:%M %p") if l.created_at else None
        }
        for l in recent_logs
    ]

    return {
        "success": True,
        "config": {
            "is_enabled": cfg.is_enabled,
            "daily_limit": cfg.daily_limit,
            "sent_today": cfg.sent_today,
            "remaining_today": max(0, cfg.daily_limit - cfg.sent_today),
            "preferred_language": cfg.preferred_language,
            "enable_affiliate_booster": cfg.enable_affiliate_booster,
            "enable_resume_booster": cfg.enable_resume_booster,
            "enable_portfolio_booster": cfg.enable_portfolio_booster,
            "morning_window_start": getattr(cfg, "morning_window_start", "09:30") or "09:30",
            "morning_window_end": getattr(cfg, "morning_window_end", "11:30") or "11:30",
            "evening_window_start": getattr(cfg, "evening_window_start", "19:30") or "19:30",
            "evening_window_end": getattr(cfg, "evening_window_end", "21:30") or "21:30",
            "last_run_at": cfg.last_run_at.strftime("%Y-%m-%d %I:%M %p") if cfg.last_run_at else None,
            "last_run_status": cfg.last_run_status
        },
        "window_info": window_info,
        "recent_logs": logs_data
    }


@router.post("/api/admin/growth-bot/config")
async def update_growth_bot_config(
    payload: GrowthBotConfigUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Updates master switch, daily limits, and targeted segment settings for Growth Bot."""
    from app.services.growth_bot import get_or_create_growth_bot_config
    cfg = get_or_create_growth_bot_config(db)

    if payload.is_enabled is not None:
        cfg.is_enabled = payload.is_enabled
    if payload.daily_limit is not None and 1 <= payload.daily_limit <= 500:
        cfg.daily_limit = payload.daily_limit
    if payload.preferred_language is not None and payload.preferred_language in ("auto", "si", "en", "ta"):
        cfg.preferred_language = payload.preferred_language
    if payload.enable_affiliate_booster is not None:
        cfg.enable_affiliate_booster = payload.enable_affiliate_booster
    if payload.enable_resume_booster is not None:
        cfg.enable_resume_booster = payload.enable_resume_booster
    if payload.enable_portfolio_booster is not None:
        cfg.enable_portfolio_booster = payload.enable_portfolio_booster
    if payload.morning_window_start is not None and payload.morning_window_start.strip():
        cfg.morning_window_start = payload.morning_window_start.strip()
    if payload.morning_window_end is not None and payload.morning_window_end.strip():
        cfg.morning_window_end = payload.morning_window_end.strip()
    if payload.evening_window_start is not None and payload.evening_window_start.strip():
        cfg.evening_window_start = payload.evening_window_start.strip()
    if payload.evening_window_end is not None and payload.evening_window_end.strip():
        cfg.evening_window_end = payload.evening_window_end.strip()

    db.commit()
    db.refresh(cfg)
    return {"success": True, "message": "Growth bot configuration updated successfully."}


@router.post("/api/admin/growth-bot/audit")
async def trigger_growth_bot_audit(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Executes a non-destructive research audit on database candidates and returns breakdown."""
    from app.services.growth_bot import run_growth_bot_audit
    result = run_growth_bot_audit(db)
    return {"success": True, "audit": result}


@router.post("/api/admin/growth-bot/trigger")
async def trigger_growth_bot_now(
    payload: Optional[GrowthBotTriggerRequest] = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Force executes an immediate outreach dispatch batch bypassing prime time window check."""
    from app.services.growth_bot import execute_growth_bot_cycle
    max_send = (payload.max_to_send if payload else 5) or 5
    result = execute_growth_bot_cycle(db, force_now=True, max_to_send=max_send)
    return {"success": True, "result": result}

