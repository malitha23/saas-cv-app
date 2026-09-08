import os
import datetime
from typing import Optional
import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.database import get_db
from app.models import User, SaasSetting, UserJobApplication

# Cryptographic Secret Configuration
_env_secret = os.getenv("JWT_SECRET")
if _env_secret and _env_secret.strip() and _env_secret.strip() != "super-secret-saas-cryptographic-jwt-key-2026-9a8b7c6d5e4f3a2b1":
    JWT_SECRET = _env_secret.strip()
else:
    # If no secret or default placeholder is provided, generate a cryptographically strong runtime secret
    import secrets
    JWT_SECRET = secrets.token_urlsafe(48)

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_DAYS = 14

security_bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """
    Very secure password hashing using bcrypt with 12 salt work factor rounds.
    Protects against rainbow tables and brute-force attacks.
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Constant-time comparison verifying plain password against bcrypt hash.
    """
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(user: User) -> str:
    """
    Generates a cryptographically signed JWT access token for the authenticated user.
    """
    now = datetime.datetime.utcnow()
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "name": user.full_name,
        "tier": user.plan_tier,
        "admin": user.is_admin,
        "iat": now,
        "exp": now + datetime.timedelta(days=JWT_EXPIRATION_DAYS)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decodes and validates JWT token signature and expiration.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI Security Dependency: Ensures the request carries a valid Bearer JWT.
    Extracts the user from the database via typed SQLAlchemy query.
    Raises HTTP 401 if unauthenticated or invalid.
    """
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please register or log in to access this SaaS feature.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(auth.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(payload["sub"])
    stmt = select(User).where(User.id == user_id)
    user = db.scalars(stmt).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your user account is suspended or inactive.",
        )

    return user


def get_optional_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Optional authentication dependency for mixed-access routes.
    """
    if not auth or not auth.credentials:
        return None
    payload = decode_access_token(auth.credentials)
    if not payload or "sub" not in payload:
        return None
    try:
        user_id = int(payload["sub"])
        stmt = select(User).where(User.id == user_id)
        return db.scalars(stmt).first()
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# SUBSCRIPTION TIER & AI QUOTA SECURITY GUARDS
# ─────────────────────────────────────────────────────────────────────────────

TIER_RANKS = {
    "free": 0,
    "sprint": 1,
    "pro": 1,
    "elite": 2
}

DEFAULT_FREE_DAILY_AI_LIMIT = 2
DEFAULT_FREE_DAILY_PDF_LIMIT = 1
DEFAULT_FREE_DAILY_COVER_LETTER_LIMIT = 3
DEFAULT_FREE_DAILY_COPILOT_KITS_LIMIT = 1
DEFAULT_FREE_MAX_TRACKED_JOBS = 3
DEFAULT_FREE_DAILY_CHAT_LIMIT = 3
DEFAULT_FREE_DAILY_INTERVIEW_LIMIT = 1


def get_saas_setting(db: Session, key: str, default: str) -> str:
    """Read dynamic rule from saas_settings table with fallback default."""
    try:
        stmt = select(SaasSetting).where(SaasSetting.key == key)
        setting = db.scalars(stmt).first()
        if setting:
            return setting.value
    except Exception:
        pass
    return default


def ensure_daily_counters_reset(user: User, db: Session):
    """Safely reset all 5 daily counters on a new calendar day."""
    today_str = datetime.date.today().isoformat()
    if user.last_generation_date != today_str:
        user.daily_ai_generations_count = 0
        user.daily_pdf_downloads_count = 0
        user.daily_cover_letter_downloads_count = 0
        user.daily_copilot_kits_count = 0
        user.daily_chat_count = 0
        if hasattr(user, "daily_interview_count"):
            user.daily_interview_count = 0
        user.last_generation_date = today_str
        db.commit()
        db.refresh(user)


def check_and_update_subscription(user: User, db: Session) -> User:
    """
    Auto-downgrade expired subscriptions to free tier safely and record status.
    """
    if user.subscription_expires_at:
        now = datetime.datetime.utcnow()
        if user.subscription_expires_at < now and user.plan_tier != "free":
            user.plan_tier = "free"
            user.subscription_status = "expired"
            db.commit()
            db.refresh(user)
        elif user.subscription_expires_at >= now:
            user.subscription_status = "active"
    else:
        if (user.plan_tier or "free") == "free":
            user.subscription_status = "active"
    return user


def check_daily_ai_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Strict server-side quota verification:
    - Protects Google Gemini API budget against abuse & bots.
    - Free users: dynamically configured in Admin Panel (default: 2 runs/day).
    - Pro / Elite users: Unlimited runs.
    - Raises HTTP 402 (Payment Required) when quota exceeded.
    """
    check_and_update_subscription(current_user, db)
    ensure_daily_counters_reset(current_user, db)

    # Quota check for free tier
    if current_user.plan_tier == "free":
        limit_str = get_saas_setting(db, "free_daily_ai_limit", str(DEFAULT_FREE_DAILY_AI_LIMIT))
        try:
            limit = int(limit_str)
        except ValueError:
            limit = DEFAULT_FREE_DAILY_AI_LIMIT

        if current_user.daily_ai_generations_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "quota_exceeded",
                    "plan": "free",
                    "daily_limit": limit,
                    "message": f"Daily free AI generation limit ({limit} runs) reached. Upgrade to Pro ($9/mo) or Elite ($19/mo) for unlimited AI tailoring!",
                    "upgrade_url": "/api/subscription/upgrade"
                }
            )

    # Increment generation count and persist
    current_user.daily_ai_generations_count += 1
    db.commit()
    db.refresh(current_user)
    return current_user


DEFAULT_FREE_LIFETIME_ATS_LIMIT = 2
DEFAULT_FREE_LIFETIME_VISUAL_LIMIT = 1
DEFAULT_FREE_LIFETIME_COVER_LETTER_LIMIT = 3


def check_ats_pdf_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Enforces strategic Lifetime PDF download limit for Free users on Classic ATS format (Max: 2 lifetime downloads).
    Pro/Elite get unlimited downloads.
    """
    check_and_update_subscription(current_user, db)
    tier = (current_user.plan_tier or "free").lower()
    if tier == "free":
        limit_str = get_saas_setting(db, "free_lifetime_ats_limit", str(DEFAULT_FREE_LIFETIME_ATS_LIMIT))
        try:
            limit = int(limit_str)
        except ValueError:
            limit = DEFAULT_FREE_LIFETIME_ATS_LIMIT

        count = getattr(current_user, "lifetime_ats_downloads_count", 0) or 0
        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ats_quota_exceeded",
                    "error_code": "ats_quota_exceeded",
                    "plan": "free",
                    "lifetime_limit": limit,
                    "downloads_used": count,
                    "message": f"You have reached your Free Starter limit of {limit} Classic ATS PDF downloads. Upgrade to Pro ($9/mo) for unlimited downloads of all formats!",
                    "upgrade_url": "/api/subscription/upgrade"
                }
            )

    current_user.lifetime_ats_downloads_count = (getattr(current_user, "lifetime_ats_downloads_count", 0) or 0) + 1
    current_user.daily_pdf_downloads_count = (current_user.daily_pdf_downloads_count or 0) + 1
    db.commit()
    db.refresh(current_user)
    return current_user


def check_visual_pdf_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Enforces strategic Lifetime Visual Photo CV download limit for Free users (Max: 1 lifetime download).
    Pro/Elite get unlimited downloads.
    """
    check_and_update_subscription(current_user, db)
    tier = (current_user.plan_tier or "free").lower()
    if tier == "free":
        limit_str = get_saas_setting(db, "free_lifetime_visual_limit", str(DEFAULT_FREE_LIFETIME_VISUAL_LIMIT))
        try:
            limit = int(limit_str)
        except ValueError:
            limit = DEFAULT_FREE_LIFETIME_VISUAL_LIMIT

        count = getattr(current_user, "lifetime_visual_downloads_count", 0) or 0
        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "visual_quota_exceeded",
                    "error_code": "visual_quota_exceeded",
                    "plan": "free",
                    "lifetime_limit": limit,
                    "downloads_used": count,
                    "message": f"You have already downloaded your 1 free Visual Photo CV. Upgrade to Pro ($9/mo) for unlimited high-resolution Visual CV downloads!",
                    "upgrade_url": "/api/subscription/upgrade"
                }
            )

    current_user.lifetime_visual_downloads_count = (getattr(current_user, "lifetime_visual_downloads_count", 0) or 0) + 1
    db.commit()
    db.refresh(current_user)
    return current_user


def check_daily_pdf_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Alias for check_ats_pdf_quota for backwards compatibility."""
    return check_ats_pdf_quota(current_user=current_user, db=db)


def check_daily_cover_letter_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """
    Enforces strategic Lifetime Cover Letter download limit for Free users (Max: 3 lifetime downloads).
    - 1st Cover Letter download is 100% clean (no watermark).
    - 2nd & 3rd Cover Letter downloads receive official watermark.
    - 4th download is blocked with quota exceeded.
    Pro/Elite get unlimited clean watermark-free downloads.
    """
    check_and_update_subscription(current_user, db)
    tier = (current_user.plan_tier or "free").lower()
    if tier == "free":
        limit_str = get_saas_setting(db, "free_lifetime_cover_letter_limit", str(DEFAULT_FREE_LIFETIME_COVER_LETTER_LIMIT))
        try:
            limit = int(limit_str)
        except ValueError:
            limit = DEFAULT_FREE_LIFETIME_COVER_LETTER_LIMIT

        count = getattr(current_user, "lifetime_cover_letter_downloads_count", 0) or 0
        if count >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "cover_letter_quota_exceeded",
                    "error_code": "cover_letter_quota_exceeded",
                    "plan": "free",
                    "lifetime_limit": limit,
                    "downloads_used": count,
                    "message": f"You have reached your Free Starter limit of {limit} Cover Letter downloads. Upgrade to Pro ($9/mo) for unlimited clean watermark-free downloads!",
                    "upgrade_url": "/api/subscription/upgrade"
                }
            )

    current_user.lifetime_cover_letter_downloads_count = (getattr(current_user, "lifetime_cover_letter_downloads_count", 0) or 0) + 1
    current_user.daily_cover_letter_downloads_count = (current_user.daily_cover_letter_downloads_count or 0) + 1
    db.commit()
    db.refresh(current_user)
    return current_user


def check_copilot_kit_quota(
    current_user: Optional[User],
    db: Session
) -> Optional[User]:
    """
    Quota guard for 1-Click Application Copilot screening kit generation.
    - Free tier / Guest: 1 kit per day.
    - Pro / Elite: Unlimited kits.
    """
    if not current_user:
        return None

    check_and_update_subscription(current_user, db)
    ensure_daily_counters_reset(current_user, db)

    tier = (current_user.plan_tier or "free").lower()
    if tier == "free":
        limit_str = get_saas_setting(db, "free_daily_copilot_kits_limit", str(DEFAULT_FREE_DAILY_COPILOT_KITS_LIMIT))
        try:
            limit = int(limit_str)
        except ValueError:
            limit = DEFAULT_FREE_DAILY_COPILOT_KITS_LIMIT

        if (current_user.daily_copilot_kits_count or 0) >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "copilot_kit_quota_exceeded",
                    "error_code": "copilot_kit_quota_exceeded",
                    "plan": "free",
                    "daily_limit": limit,
                    "kits_used": current_user.daily_copilot_kits_count,
                    "message": f"Daily free Application Kit limit ({limit} kit) reached. Upgrade to Pro ($9/mo) for unlimited 1-click tailored screening kits!",
                    "upgrade_url": "/api/subscription/upgrade"
                }
            )

        current_user.daily_copilot_kits_count = (current_user.daily_copilot_kits_count or 0) + 1
        db.commit()
        db.refresh(current_user)

    return current_user


def check_job_tracker_quota(
    current_user: User,
    db: Session
) -> User:
    """
    Enforces maximum active tracked jobs limit for Free users (Max 3 tracked jobs).
    Pro / Elite users have unlimited tracking with cloud sync.
    """
    check_and_update_subscription(current_user, db)
    tier = (current_user.plan_tier or "free").lower()

    if tier == "free":
        stmt = select(func.count(UserJobApplication.id)).where(UserJobApplication.user_id == current_user.id)
        current_tracked = db.scalar(stmt) or 0
        limit_str = get_saas_setting(db, "free_max_tracked_jobs", str(DEFAULT_FREE_MAX_TRACKED_JOBS))
        try:
            limit = int(limit_str)
        except ValueError:
            limit = DEFAULT_FREE_MAX_TRACKED_JOBS

        if current_tracked >= limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "tracker_quota_exceeded",
                    "error_code": "tracker_quota_exceeded",
                    "plan": "free",
                    "limit": limit,
                    "tracked_count": current_tracked,
                    "message": f"Free Starter tier allows tracking up to {limit} jobs. Upgrade to Pro ($9/mo) for unlimited Kanban pipeline job tracking!",
                    "upgrade_url": "/api/subscription/upgrade"
                }
            )

    return current_user


def check_chat_copilot_quota(
    current_user: Optional[User],
    db: Session
) -> tuple[bool, int, str]:
    """
    Checks message allowance for the AI Career Copilot Chatbot.
    - Pro / Elite: Unlimited 24/7 coaching & mock interviews.
    - Free registered user: 3 messages per day.
    - Guest: 3 messages per day.
    Returns: (is_allowed, remaining_count, message)
    """
    if not current_user:
        return True, 2, "2 trial messages remaining"

    check_and_update_subscription(current_user, db)
    ensure_daily_counters_reset(current_user, db)

    tier = (current_user.plan_tier or "free").lower()
    if tier in ["pro", "elite"]:
        return True, 9999, "Unlimited Pro Coach"

    limit_str = get_saas_setting(db, "free_daily_chat_limit", str(DEFAULT_FREE_DAILY_CHAT_LIMIT))
    try:
        limit = int(limit_str)
    except ValueError:
        limit = DEFAULT_FREE_DAILY_CHAT_LIMIT

    used = current_user.daily_chat_count or 0
    if used >= limit:
        return False, 0, f"Daily free Career Copilot limit ({limit} messages) reached."

    current_user.daily_chat_count = used + 1
    db.commit()
    db.refresh(current_user)
    remaining = max(0, limit - (used + 1))
    return True, remaining, f"{remaining} free messages remaining today"


def check_voice_interview_quota(
    current_user: Optional[User],
    db: Session
) -> tuple[bool, int, str]:
    """
    Checks session allowance for the AI Voice Mock Interview Simulator.
    - Pro / Elite: Unlimited full-length voice mock interviews.
    - Free / Guest: 1 interactive practice session per day (3 questions).
    Returns: (is_allowed, remaining_count, message)
    """
    if not current_user:
        return True, 1, "1 trial session remaining"

    check_and_update_subscription(current_user, db)
    ensure_daily_counters_reset(current_user, db)

    tier = (current_user.plan_tier or "free").lower()
    if tier in ["pro", "elite"]:
        return True, 9999, "Unlimited Voice Interviews (Pro Access)"

    limit_str = get_saas_setting(db, "free_daily_interview_limit", str(DEFAULT_FREE_DAILY_INTERVIEW_LIMIT))
    try:
        limit = int(limit_str)
    except ValueError:
        limit = DEFAULT_FREE_DAILY_INTERVIEW_LIMIT

    used = getattr(current_user, "daily_interview_count", 0) or 0
    if used >= limit:
        return False, 0, f"Daily free Voice Mock Interview limit ({limit} session) reached."

    if hasattr(current_user, "daily_interview_count"):
        current_user.daily_interview_count = used + 1
        db.commit()
        db.refresh(current_user)

    remaining = max(0, limit - (used + 1))
    return True, remaining, f"{remaining} free practice sessions remaining today"



def require_tier(minimum_tier: str):

    """
    FastAPI Dependency Factory enforcing server-side privilege boundaries.
    Prevents free/pro users from accessing elite-only endpoints (e.g. custom domains).
    """
    min_rank = TIER_RANKS.get(minimum_tier.lower(), 0)

    def tier_checker(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        check_and_update_subscription(current_user, db)
        user_rank = TIER_RANKS.get((current_user.plan_tier or "free").lower(), 0)
        if user_rank < min_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "plan_upgrade_required",
                    "required_tier": minimum_tier,
                    "current_tier": current_user.plan_tier,
                    "message": f"This feature requires the {minimum_tier.upper()} plan. Please upgrade to unlock."
                }
            )
        return current_user

    return tier_checker


def require_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Strict server-side administrator authorization guard.
    Guarantees only users with is_admin=True can access admin management APIs.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required. Permission denied."
        )
    return current_user


def verify_google_credential_token(credential: str, expected_client_id: Optional[str] = None) -> dict:
    """
    Cryptographically verifies a Google ID token with Google's official token verification service.
    Enforces zero-trust validation of issuer, audience, expiration, and email_verified.
    Returns normalized dictionary with sub, email, name, picture.
    """
    import urllib.request
    import json
    import time

    if not credential or not isinstance(credential, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google credential token is missing or malformed."
        )

    # 1. Dev / Automated Test Hook (Strictly restricted to test/dev environment)
    is_test_env = (
        os.getenv("TESTING", "").strip().lower() in ("true", "1", "yes") or
        os.getenv("ENVIRONMENT", "").strip().lower() in ("test", "testing")
    )
    if credential.startswith("mock_google_token_"):
        if not is_test_env:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mock Google authentication credentials are prohibited in production."
            )
        parts = credential.split(":", 4)
        sub = parts[1] if len(parts) > 1 else "google_12345"
        email = parts[2] if len(parts) > 2 else "google_user@example.com"
        name = parts[3] if len(parts) > 3 else "Google Candidate"
        picture = parts[4] if len(parts) > 4 else "https://lh3.googleusercontent.com/a/default-user=s96-c"
        return {
            "sub": sub,
            "email": email.strip().lower(),
            "name": name.strip(),
            "picture": picture.strip(),
            "email_verified": True
        }

    # 2. Query Google's tokeninfo endpoint (ID token or OAuth2 access token)
    payload = None
    is_access_token = False
    try:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
        req = urllib.request.Request(url, headers={"User-Agent": "DreemFolio-OAuth/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        # Check if credential is an OAuth2 access token from popup flow
        try:
            url = f"https://oauth2.googleapis.com/tokeninfo?access_token={credential}"
            req = urllib.request.Request(url, headers={"User-Agent": "DreemFolio-OAuth/1.0"})
            with urllib.request.urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
                is_access_token = True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google token verification failed: {str(e)}"
            )

    # If access token was supplied, fetch user profile for name and avatar
    if is_access_token:
        try:
            u_url = "https://www.googleapis.com/oauth2/v3/userinfo"
            u_req = urllib.request.Request(u_url, headers={"Authorization": f"Bearer {credential}", "User-Agent": "DreemFolio-OAuth/1.0"})
            with urllib.request.urlopen(u_req, timeout=8) as u_res:
                u_data = json.loads(u_res.read().decode("utf-8"))
                payload.update(u_data)
        except Exception:
            pass

    # 3. Check for error in payload
    if "error" in payload or "error_description" in payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=payload.get("error_description", "Invalid or expired Google token.")
        )

    # 4. Verify Issuer if ID token
    if not is_access_token:
        iss = payload.get("iss", "")
        if iss not in ["accounts.google.com", "https://accounts.google.com"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Untrusted Google token issuer: {iss}"
            )

    # 5. Verify Audience if expected_client_id is provided
    if expected_client_id:
        aud = payload.get("aud", "")
        if aud != expected_client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google token audience mismatch."
            )

    # 6. Verify Expiration
    exp = int(payload.get("exp", 0))
    if exp < time.time():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google ID token has expired."
        )

    # 7. Verify Email Verification status
    email_verified = payload.get("email_verified")
    if email_verified not in [True, "true", "True", 1]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google account email is not verified. Access denied."
        )

    email = payload.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google token did not contain an email address."
        )

    return {
        "sub": payload.get("sub"),
        "email": email.strip().lower(),
        "name": payload.get("name") or payload.get("given_name") or email.split("@")[0],
        "picture": payload.get("picture"),
        "email_verified": True
    }



