import os
import datetime
from collections import defaultdict
from typing import Dict, Any, List, Optional
from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.schemas import UserResponse, TailoredResume
from app.models import User
from app.auth import (
    get_saas_setting,
    DEFAULT_FREE_DAILY_AI_LIMIT,
    DEFAULT_FREE_DAILY_PDF_LIMIT,
    DEFAULT_FREE_DAILY_COVER_LETTER_LIMIT,
    DEFAULT_FREE_LIFETIME_ATS_LIMIT,
    DEFAULT_FREE_LIFETIME_VISUAL_LIMIT,
    DEFAULT_FREE_LIFETIME_COVER_LETTER_LIMIT,
)

# ─────────────────────────────────────────────────────────────────────────────
# JINJA2 TEMPLATES CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# ─────────────────────────────────────────────────────────────────────────────
# IN-MEMORY CACHES & PUBLISHED DATA STORES
# ─────────────────────────────────────────────────────────────────────────────
PUBLISHED_PORTFOLIOS: Dict[str, str] = {}
PUBLISHED_RESUMES: Dict[str, TailoredResume] = {}
CUSTOM_DOMAINS: Dict[str, str] = {}  # domain -> slug

# Sensitive endpoints rate limits: (max_requests, window_seconds)
RATE_LIMIT_RULES: Dict[str, tuple[int, int]] = {
    "/api/auth/login": (10, 60),               # Max 10 attempts per minute
    "/api/auth/register": (5, 60),             # Max 5 registrations per minute
    "/api/auth/forgot-password": (5, 60),      # Max 5 forgot password requests per minute
    "/api/auth/reset-password": (10, 60),      # Max 10 reset attempts per minute
    "/api/auth/google": (15, 60),              # Max 15 Google auth requests per minute
    "/api/tailor": (10, 60),                   # Max 10 AI generation requests per minute
    "/api/portfolio/verify-pin": (10, 60),     # Max 10 PIN attempts per minute (Anti-Bruteforce)
    "/api/upload": (10, 60),                   # Max 10 resume file uploads per minute
    "/api/conference/turn": (30, 60),          # Max 30 live conference turns per minute
    "/api/conference/tts": (60, 60),           # Max 60 voice syntheses per minute
    "/api/interview/evaluate-answer": (20, 60),# Max 20 interview evaluations per minute
    "/api/chat/copilot": (20, 60),             # Max 20 Career Copilot chat requests per minute
}
RATE_LIMIT_STORE: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
PIN_ATTEMPT_STORE: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"failed_count": 0, "lockout_until": 0.0})


def _get_client_ip(request: Request) -> str:
    """Extract client IP address safely considering reverse proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


def build_user_response(user: User, db: Optional[Session] = None) -> UserResponse:
    """Standardized user response builder with dynamic quotas, plan validity, and lifetime stats."""
    today_str = datetime.date.today().isoformat()
    now = datetime.datetime.utcnow()

    if user.last_generation_date != today_str:
        daily_count = 0
        pdf_count = 0
        cl_count = 0
    else:
        daily_count = user.daily_ai_generations_count or 0
        pdf_count = user.daily_pdf_downloads_count or 0
        cl_count = getattr(user, "daily_cover_letter_downloads_count", 0) or 0

    tier = user.plan_tier or "free"
    ai_limit = DEFAULT_FREE_DAILY_AI_LIMIT
    pdf_limit = DEFAULT_FREE_DAILY_PDF_LIMIT
    cl_limit = DEFAULT_FREE_DAILY_COVER_LETTER_LIMIT
    if db is not None:
        try:
            ai_limit = int(get_saas_setting(db, "free_daily_ai_limit", str(DEFAULT_FREE_DAILY_AI_LIMIT)))
        except (ValueError, TypeError):
            ai_limit = DEFAULT_FREE_DAILY_AI_LIMIT
        try:
            pdf_limit = int(get_saas_setting(db, "free_daily_pdf_limit", str(DEFAULT_FREE_DAILY_PDF_LIMIT)))
        except (ValueError, TypeError):
            pdf_limit = DEFAULT_FREE_DAILY_PDF_LIMIT
        try:
            cl_limit = int(get_saas_setting(db, "free_daily_cover_letter_limit", str(DEFAULT_FREE_DAILY_COVER_LETTER_LIMIT)))
        except (ValueError, TypeError):
            cl_limit = DEFAULT_FREE_DAILY_COVER_LETTER_LIMIT

    remaining = None
    pdf_remaining = None
    cl_remaining = None
    if tier == "free":
        remaining = max(0, ai_limit - daily_count)
        pdf_remaining = max(0, pdf_limit - pdf_count)
        cl_remaining = max(0, cl_limit - cl_count)

    # Compute days remaining and human-readable validity label
    days_left = None
    status_label = user.subscription_status or "active"

    if user.subscription_expires_at:
        exp_delta = user.subscription_expires_at - now
        total_seconds = exp_delta.total_seconds()
        if total_seconds > 0:
            days_left = max(1, int(total_seconds // 86400) + (1 if (total_seconds % 86400) > 0 else 0))
            validity_label = f"{days_left} days remaining"
            status_label = "active"
        else:
            days_left = 0
            validity_label = "Expired"
            status_label = "expired"
    else:
        if tier == "free":
            validity_label = "Lifetime Free"
            status_label = "active"
        else:
            validity_label = "Active"

    # Strategic Lifetime Quotas
    life_ats_limit = DEFAULT_FREE_LIFETIME_ATS_LIMIT
    life_visual_limit = DEFAULT_FREE_LIFETIME_VISUAL_LIMIT
    life_cl_limit = DEFAULT_FREE_LIFETIME_COVER_LETTER_LIMIT
    if db is not None:
        try:
            life_ats_limit = int(get_saas_setting(db, "free_lifetime_ats_limit", str(DEFAULT_FREE_LIFETIME_ATS_LIMIT)))
        except (ValueError, TypeError):
            life_ats_limit = DEFAULT_FREE_LIFETIME_ATS_LIMIT
        try:
            life_visual_limit = int(get_saas_setting(db, "free_lifetime_visual_limit", str(DEFAULT_FREE_LIFETIME_VISUAL_LIMIT)))
        except (ValueError, TypeError):
            life_visual_limit = DEFAULT_FREE_LIFETIME_VISUAL_LIMIT
        try:
            life_cl_limit = int(get_saas_setting(db, "free_lifetime_cover_letter_limit", str(DEFAULT_FREE_LIFETIME_COVER_LETTER_LIMIT)))
        except (ValueError, TypeError):
            life_cl_limit = DEFAULT_FREE_LIFETIME_COVER_LETTER_LIMIT

    life_ats_used = getattr(user, "lifetime_ats_downloads_count", 0) or 0
    life_visual_used = getattr(user, "lifetime_visual_downloads_count", 0) or 0
    life_cl_used = getattr(user, "lifetime_cover_letter_downloads_count", 0) or 0

    bonus_ats = getattr(user, "referral_bonus_downloads", 0) or 0
    effective_ats_limit = life_ats_limit + bonus_ats

    life_ats_remaining = None if tier in ["pro", "elite"] else max(0, effective_ats_limit - life_ats_used)
    life_visual_remaining = None if tier in ["pro", "elite"] else max(0, life_visual_limit - life_visual_used)
    life_cl_remaining = None if tier in ["pro", "elite"] else max(0, life_cl_limit - life_cl_used)

    started_str = user.subscription_started_at.strftime("%B %d, %Y") if user.subscription_started_at else None
    exp_str = user.subscription_expires_at.strftime("%B %d, %Y") if user.subscription_expires_at else None

    # Calculate referrals count
    referrals_count = 0
    if db is not None:
        try:
            from sqlalchemy import select, func
            from app.models import User as UserModel
            referrals_count = db.scalar(
                select(func.count(UserModel.id)).where(UserModel.referred_by_id == user.id)
            ) or 0
        except Exception:
            referrals_count = 0

    # Pending Payment Protection Detection
    has_pending = False
    pending_info = None
    has_slip = False

    if db is not None:
        try:
            from app.models import OnlinePaymentOrder, BankPaymentSlip
            from app.schemas import PendingOrderInfo
            from sqlalchemy import select
            cutoff = now - datetime.timedelta(minutes=30)
            pending_order = db.scalars(
                select(OnlinePaymentOrder)
                .where(
                    OnlinePaymentOrder.user_id == user.id,
                    OnlinePaymentOrder.status.in_(["initiated", "pending"]),
                    OnlinePaymentOrder.created_at >= cutoff
                )
                .order_by(OnlinePaymentOrder.id.desc())
            ).first()

            if pending_order:
                has_pending = True
                created_str = pending_order.created_at.strftime("%b %d, %Y %I:%M %p") if pending_order.created_at else ""
                pending_info = PendingOrderInfo(
                    order_id=pending_order.order_id,
                    target_plan=pending_order.target_plan,
                    amount=pending_order.amount,
                    currency=pending_order.currency,
                    gateway=pending_order.gateway or "payhere",
                    status=pending_order.status,
                    created_at=created_str,
                    status_url=f"/payment/status?order_id={pending_order.order_id}&status={pending_order.status}"
                )

            pending_slip = db.scalars(
                select(BankPaymentSlip.id)
                .where(
                    BankPaymentSlip.user_id == user.id,
                    BankPaymentSlip.status == "pending"
                )
            ).first()
            has_slip = bool(pending_slip)
        except Exception:
            pass

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        plan_tier=tier,
        is_admin=bool(user.is_admin),
        created_at=user.created_at.strftime("%B %d, %Y"),
        subscription_status=status_label,
        subscription_started_at=started_str,
        subscription_expires_at=exp_str,
        subscription_days_remaining=days_left,
        subscription_validity_label=validity_label,
        daily_ai_generations_count=daily_count,
        daily_generations_remaining=remaining,
        daily_pdf_downloads_count=pdf_count,
        daily_pdf_downloads_remaining=pdf_remaining,
        daily_cover_letter_downloads_count=cl_count,
        daily_cover_letter_downloads_remaining=cl_remaining,
        daily_copilot_kits_count=getattr(user, "daily_copilot_kits_count", 0) or 0,
        daily_copilot_kits_remaining=None if tier in ["pro", "elite"] else max(0, 1 - (getattr(user, "daily_copilot_kits_count", 0) or 0)),
        daily_chat_count=getattr(user, "daily_chat_count", 0) or 0,
        daily_chat_remaining=None if tier in ["pro", "elite"] else max(0, 3 - (getattr(user, "daily_chat_count", 0) or 0)),
        daily_interview_count=getattr(user, "daily_interview_count", 0) or 0,
        daily_interview_remaining=None if tier in ["pro", "elite"] else max(0, 1 - (getattr(user, "daily_interview_count", 0) or 0)),
        lifetime_ats_downloads_count=life_ats_used,
        lifetime_ats_downloads_remaining=life_ats_remaining,
        lifetime_visual_downloads_count=life_visual_used,
        lifetime_visual_downloads_remaining=life_visual_remaining,
        lifetime_cover_letter_downloads_count=life_cl_used,
        lifetime_cover_letter_downloads_remaining=life_cl_remaining,
        has_pending_order=has_pending,
        pending_order=pending_info,
        has_pending_slip=has_slip,
        avatar_url=getattr(user, "avatar_url", None),
        auth_provider=getattr(user, "auth_provider", "email") or "email",
        google_id=getattr(user, "google_id", None),
        referral_code=getattr(user, "referral_code", None),
        referral_bonus_downloads=getattr(user, "referral_bonus_downloads", 0) or 0,
        referrals_count=referrals_count
    )
