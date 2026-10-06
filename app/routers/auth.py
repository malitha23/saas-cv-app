import os
import re
import json
import secrets
import datetime
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Response
from sqlalchemy.orm import Session
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import User, EmailVerificationOtp
from app.schemas import (
    GoogleConfigResponse, GoogleAuthRequest, TokenResponse,
    UserRegisterRequest, UserLoginRequest, ForgotPasswordRequest,
    ResetPasswordRequest, UserResponse, DeleteAccountRequest,
    SendRegistrationOtpRequest, VerifyRegistrationOtpRequest
)
from app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, check_and_update_subscription,
    get_saas_setting, verify_google_credential_token
)
from app.state import build_user_response
from app.email_service import (
    send_user_welcome_email, send_admin_new_user_alert,
    send_user_forgot_password, send_user_password_reset_success,
    send_user_registration_otp
)

logger = logging.getLogger("dreemfolio.auth")

router = APIRouter(tags=["Authentication"])


@router.get("/api/auth/google-config", response_model=GoogleConfigResponse)
async def get_google_auth_config(db: Session = Depends(get_db)):
    """Fetch active Google OAuth 2.0 configuration for client-side Google Identity Services."""
    client_id = get_saas_setting(db, "google_client_id", os.environ.get("GOOGLE_CLIENT_ID", "")).strip()
    return GoogleConfigResponse(
        client_id=client_id if client_id else None,
        is_enabled=bool(client_id)
    )


@router.post("/api/auth/google", response_model=TokenResponse)
async def auth_with_google(
    req: GoogleAuthRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Authenticate SaaS user with Google Identity Services (GIS).
    Verifies Google ID token, performs secure account linking, and creates user if new.
    """
    client_id = get_saas_setting(db, "google_client_id", os.environ.get("GOOGLE_CLIENT_ID", "")).strip()
    
    # Cryptographically verify the Google ID token with zero-trust validation
    google_info = verify_google_credential_token(
        req.credential,
        expected_client_id=client_id if client_id else None
    )

    google_sub = str(google_info["sub"]).strip()
    google_email = str(google_info.get("email") or "").strip().lower()
    if not google_email:
        raise HTTPException(
            status_code=400,
            detail="Google authentication failed: Email address was not provided by Google."
        )
    raw_google_name = str(google_info.get("name") or "Candidate").strip()
    clean_google_name = re.sub(r"<[^>]*>", "", raw_google_name).strip()
    clean_google_name = re.sub(r"[<>\"'`{};]", "", clean_google_name)
    google_name = re.sub(r"\s+", " ", clean_google_name)[:70] or "Candidate"
    google_picture = google_info.get("picture")

    # 1. Lookup by google_id OR by email (case-insensitive & trimmed for safe account linking)
    stmt = select(User).where(
        or_(
            User.google_id == google_sub,
            func.lower(func.trim(User.email)) == google_email
        )
    )
    user = db.scalars(stmt).first()

    if user:
        # Safe account linking: Link Google ID to existing account
        needs_commit = False
        if not user.google_id:
            user.google_id = google_sub
            needs_commit = True
        if google_picture and not user.avatar_url:
            user.avatar_url = google_picture
            needs_commit = True
        if not user.auth_provider or user.auth_provider == "email":
            user.auth_provider = "google"
            needs_commit = True
        if needs_commit:
            try:
                db.commit()
                db.refresh(user)
            except IntegrityError:
                db.rollback()
                user = db.scalars(stmt).first()
    else:
        # 2. Create brand new user
        now = datetime.datetime.utcnow()
        random_pw = secrets.token_urlsafe(32)
        my_ref_code = generate_unique_referral_code(db)
        user = User(
            email=google_email,
            hashed_password=hash_password(random_pw),
            full_name=google_name,
            plan_tier="free",
            subscription_status="active",
            subscription_started_at=now,
            daily_ai_generations_count=0,
            daily_pdf_downloads_count=0,
            daily_cover_letter_downloads_count=0,
            lifetime_ats_downloads_count=0,
            lifetime_visual_downloads_count=0,
            lifetime_cover_letter_downloads_count=0,
            google_id=google_sub,
            avatar_url=google_picture,
            auth_provider="google",
            is_admin=False,
            is_active=True,
            referral_code=my_ref_code
        )
        try:
            db.add(user)
            db.commit()
            db.refresh(user)
        except Exception as db_err:
            # Concurrency / duplicate race-condition safeguard:
            # Another concurrent request or previous session already inserted this user!
            db.rollback()
            user = db.scalars(
                select(User).where(
                    or_(
                        User.google_id == google_sub,
                        func.lower(func.trim(User.email)) == google_email
                    )
                )
            ).first()
            if not user:
                logger.error("Failed to insert or locate user during Google signup: %s", db_err)
                raise HTTPException(
                    status_code=409,
                    detail="An account with this email address already exists. Please log in."
                )

        incoming_ref = (req.referral_code or request.cookies.get("dreemfolio_ref") or "").strip()
        if incoming_ref:
            try:
                process_referral_signup(user, incoming_ref, db)
            except Exception as ref_err:
                logger.warning("Referral processing error: %s", ref_err)

        try:
            base_url = str(request.base_url).rstrip("/")
            send_user_welcome_email(user.email, user.full_name, base_url, background_tasks)
            send_admin_new_user_alert(user.email, user.full_name, "Google", base_url, db, background_tasks)
        except Exception as notify_err:
            logger.warning("Notification error during Google signup: %s", notify_err)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your account has been deactivated.")

    check_and_update_subscription(user, db)
    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=build_user_response(user, db)
    )


def generate_unique_referral_code(db: Session) -> str:
    """Generate cryptographically distinct referral code e.g. DF-A1B2C3."""
    for _ in range(10):
        candidate = f"DF-{secrets.token_hex(3).upper()}"
        if not db.scalars(select(User.id).where(User.referral_code == candidate)).first():
            return candidate
    return f"DF-{secrets.token_hex(4).upper()}"


def process_referral_signup(new_user: User, raw_ref_code: Optional[str], db: Session) -> bool:
    """Link referred user and reward inviter with +1 clean ATS download with anti-fraud protection."""
    try:
        if not raw_ref_code or not raw_ref_code.strip():
            return False
        ref_clean = raw_ref_code.strip()
        
        referrer = None
        if ref_clean.upper().startswith("DF-"):
            referrer = db.scalars(select(User).where(User.referral_code == ref_clean.upper())).first()
        elif ref_clean.startswith("portfolio_"):
            slug = ref_clean.replace("portfolio_", "").strip().lower()
            users = db.scalars(select(User)).all()
            for u in users:
                clean_u = re.sub(r'[^a-zA-Z0-9]', '-', u.full_name.lower()).strip('-')
                if clean_u == slug:
                    referrer = u
                    break
        else:
            referrer = db.scalars(select(User).where(User.referral_code == ref_clean.upper())).first()

        # Anti-fraud: cannot refer oneself
        if referrer and referrer.id != new_user.id:
            new_user.referred_by_id = referrer.id
            referrer.referral_bonus_downloads = (getattr(referrer, "referral_bonus_downloads", 0) or 0) + 1
            db.commit()
            return True
        return False
    except Exception as e:
        logger.warning("Error processing referral signup: %s", e)
DISPOSABLE_EMAIL_DOMAINS = {
    "mailinator.com", "tempmail.com", "10minutemail.com", "guerrillamail.com",
    "trashmail.com", "yopmail.com", "dispostable.com", "getairmail.com",
    "fakeinbox.com", "sharklasers.com", "guerrillamailblock.com", "grr.la",
    "temp-mail.org", "throwawaymail.com", "nada.ltd", "mohmal.com", "inboxkitten.com",
    "burnermail.io", "maildrop.cc", "crazymailing.com", "mytemp.email", "disposablemail.com"
}


@router.post("/api/auth/send-registration-otp")
async def send_registration_otp(
    req: SendRegistrationOtpRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Validates email format, screens for disposable/fake domains, generates a secure 6-digit OTP,
    and dispatches verification code via email. Blocks fake and unverified account generation.
    """
    email_clean = req.email.strip().lower()
    domain = email_clean.split("@")[-1] if "@" in email_clean else ""
    if domain in DISPOSABLE_EMAIL_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail="Temporary or disposable email domains are not permitted. Please use a legitimate personal or work email address."
        )

    # Check if already registered
    existing_user = db.scalars(select(User).where(User.email == email_clean)).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="An account with this email address already exists. Please log in."
        )

    # Rate limiting: max 1 OTP request every 45 seconds per email
    now = datetime.datetime.utcnow()
    recent_otp = db.scalars(
        select(EmailVerificationOtp)
        .where(
            EmailVerificationOtp.email == email_clean,
            EmailVerificationOtp.is_used == False,
            EmailVerificationOtp.created_at >= now - datetime.timedelta(seconds=45)
        )
    ).first()
    if recent_otp:
        raise HTTPException(
            status_code=429,
            detail="A verification code was recently sent. Please wait 45 seconds before requesting another code."
        )

    # Generate 6-digit cryptographic OTP
    otp_code = f"{secrets.randbelow(900000) + 100000}"
    expires_at = now + datetime.timedelta(minutes=10)
    pw_hash = hash_password(req.password)
    clean_name = re.sub(r"<[^>]*>", "", req.full_name or "").strip()
    clean_name = re.sub(r"[<>\"'`{};]", "", clean_name)
    clean_name = re.sub(r"\s+", " ", clean_name)[:70] or "Candidate"

    incoming_ref = (req.referral_code or request.cookies.get("dreemfolio_ref") or "").strip() or None

    # Invalidate previous unused OTPs for this email
    prev_otps = db.scalars(
        select(EmailVerificationOtp).where(
            EmailVerificationOtp.email == email_clean,
            EmailVerificationOtp.is_used == False
        )
    ).all()
    for p in prev_otps:
        p.is_used = True

    # Record new OTP
    otp_record = EmailVerificationOtp(
        email=email_clean,
        otp_code=otp_code,
        full_name=clean_name,
        password_hash=pw_hash,
        referral_code=incoming_ref,
        expires_at=expires_at,
        is_used=False
    )
    db.add(otp_record)
    db.commit()

    # Dispatch email in background
    base_url = str(request.base_url).rstrip("/")
    send_user_registration_otp(
        to_email=email_clean,
        full_name=clean_name,
        otp_code=otp_code,
        base_url=base_url,
        background_tasks=background_tasks
    )

    return {
        "success": True,
        "message": f"A 6-digit verification code has been sent to {email_clean}. Please check your inbox.",
        "email": email_clean
    }


@router.post("/api/auth/verify-registration-otp", response_model=TokenResponse)
async def verify_registration_otp(
    req: VerifyRegistrationOtpRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Verifies 6-digit OTP code. Upon successful verification, securely creates user account,
    applies referral rewards, and issues cryptographic JWT token.
    """
    email_clean = req.email.strip().lower()
    otp_clean = req.otp_code.strip()
    now = datetime.datetime.utcnow()

    # Query active, unexpired OTP for this email
    otp_record = db.scalars(
        select(EmailVerificationOtp)
        .where(
            EmailVerificationOtp.email == email_clean,
            EmailVerificationOtp.is_used == False,
            EmailVerificationOtp.expires_at >= now
        )
        .order_by(EmailVerificationOtp.id.desc())
    ).first()

    if not otp_record:
        raise HTTPException(
            status_code=400,
            detail="Verification code is invalid or has expired. Please request a new code."
        )

    # Brute-force check: max 5 failed attempts per OTP record
    if otp_record.attempts >= 5:
        otp_record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=400,
            detail="Too many incorrect attempts. This verification code has been revoked. Please request a new one."
        )

    if otp_record.otp_code != otp_clean:
        otp_record.attempts += 1
        db.commit()
        remaining = 5 - otp_record.attempts
        raise HTTPException(
            status_code=400,
            detail=f"Incorrect verification code. Please check your email and try again ({remaining} attempts remaining)."
        )

    # Mark OTP as successfully used
    otp_record.is_used = True
    db.commit()

    # Re-check user existence in case of race condition
    existing = db.scalars(select(User).where(User.email == email_clean)).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email address already exists. Please log in."
        )

    my_ref_code = generate_unique_referral_code(db)
    user = User(
        email=email_clean,
        hashed_password=otp_record.password_hash,
        full_name=otp_record.full_name,
        plan_tier="free",
        subscription_status="active",
        referral_code=my_ref_code
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="An account with this email address already exists. Please log in."
        )

    # Process referral attribution if code stored
    incoming_ref = (otp_record.referral_code or request.cookies.get("dreemfolio_ref") or "").strip()
    if incoming_ref:
        process_referral_signup(user, incoming_ref, db)

    base_url = str(request.base_url).rstrip("/")
    send_user_welcome_email(user.email, user.full_name, base_url, background_tasks)
    send_admin_new_user_alert(user.email, user.full_name, "Email (Verified OTP)", base_url, db, background_tasks)

    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=build_user_response(user, db)
    )


@router.post("/api/auth/register")
async def register_user_redirect_to_otp(
    req: UserRegisterRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Mandatory email verification gateway: intercepts direct registration calls
    and routes through 6-digit OTP verification to prevent fake email creation.
    """
    otp_req = SendRegistrationOtpRequest(
        email=req.email,
        password=req.password,
        full_name=req.full_name,
        referral_code=req.referral_code
    )
    return await send_registration_otp(otp_req, request, background_tasks, db)


@router.post("/api/auth/login", response_model=TokenResponse)
async def login_user(req: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate SaaS user credentials and issue cryptographic JWT."""
    email_clean = req.email.strip().lower()
    stmt = select(User).where(User.email == email_clean)
    user = db.scalars(stmt).first()

    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password. Please check your credentials."
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your account has been deactivated.")

    check_and_update_subscription(user, db)
    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=build_user_response(user, db)
    )


@router.post("/api/auth/forgot-password")
async def forgot_password(
    req: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Initiate secure password reset request.
    Generates a cryptographically strong 1-hour expiration token and dispatches reset email.
    Always returns success to prevent user enumeration attacks.
    """
    email_clean = req.email.strip().lower()
    stmt = select(User).where(User.email == email_clean)
    user = db.scalars(stmt).first()

    if user and user.is_active:
        token = secrets.token_urlsafe(32)
        user.reset_password_token = token
        user.reset_password_expires_at = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        db.commit()

        base_url = str(request.base_url).rstrip("/")
        send_user_forgot_password(
            to_email=user.email,
            full_name=user.full_name or "Candidate",
            reset_token=token,
            base_url=base_url,
            background_tasks=background_tasks
        )
        logger.info("Password reset token generated and dispatched for %s", email_clean)

    return {
        "success": True,
        "message": "If an account exists with this email address, a password reset link has been dispatched to your inbox."
    }


@router.post("/api/auth/reset-password")
async def reset_password(
    req: ResetPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Validate password reset token and update user credentials with salted bcrypt hash.
    """
    token_clean = req.token.strip()
    if not token_clean:
        raise HTTPException(status_code=400, detail="Password reset token is required.")

    if len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="New password must be at least 6 characters long.")

    stmt = select(User).where(User.reset_password_token == token_clean)
    user = db.scalars(stmt).first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid or unrecognized password reset token.")

    now = datetime.datetime.utcnow()
    if not user.reset_password_expires_at or user.reset_password_expires_at < now:
        user.reset_password_token = None
        user.reset_password_expires_at = None
        db.commit()
        raise HTTPException(status_code=400, detail="This password reset link has expired. Please request a new one.")

    # Update password and clear reset token
    user.hashed_password = hash_password(req.new_password)
    user.reset_password_token = None
    user.reset_password_expires_at = None
    db.commit()

    base_url = str(request.base_url).rstrip("/")
    send_user_password_reset_success(
        to_email=user.email,
        full_name=user.full_name or "Candidate",
        base_url=base_url,
        background_tasks=background_tasks
    )
    logger.info("Password successfully reset for user %s", user.email)

    return {
        "success": True,
        "message": "Your password has been successfully reset. You may now log in with your new credentials."
    }


@router.get("/api/auth/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch profile of currently authenticated user with real-time quota status."""
    check_and_update_subscription(current_user, db)
    return build_user_response(current_user, db)


# ═══════════════════════════════════════════════════════════════════════════
# DATA PROTECTION & STATUTORY USER RIGHTS (SRI LANKA PDPA NO. 9 OF 2022 & GDPR)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/api/auth/export-data")
async def export_my_personal_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Statutory Right of Access & Data Portability (PDPA No. 9 of 2022 Sec 13 / GDPR Art 20).
    Packages all user profile data, tailored resumes, and career logs into machine-readable JSON.
    """
    # 1. User Profile Record
    user_info = {
        "user_id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "plan_tier": current_user.plan_tier,
        "subscription_status": current_user.subscription_status,
        "subscription_started_at": current_user.subscription_started_at.isoformat() if current_user.subscription_started_at else None,
        "subscription_expires_at": current_user.subscription_expires_at.isoformat() if current_user.subscription_expires_at else None,
        "auth_provider": current_user.auth_provider,
        "referral_code": current_user.referral_code,
        "referral_bonus_downloads": current_user.referral_bonus_downloads,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }

    # 2. Resumes & Tailored Documents
    resumes_list = []
    for r in current_user.resumes:
        parsed_content = {}
        if r.resume_data_json:
            try:
                parsed_content = json.loads(r.resume_data_json)
            except Exception:
                parsed_content = {"raw": r.resume_data_json}
        resumes_list.append({
            "id": r.id,
            "title": r.title,
            "target_role": r.target_role,
            "template_style": r.template_style,
            "resume_data": parsed_content,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })

    # 3. Tracked Job Applications
    jobs_list = []
    for j in current_user.job_applications:
        app_kit = {}
        if j.application_kit_json:
            try:
                app_kit = json.loads(j.application_kit_json)
            except Exception:
                app_kit = {"raw": j.application_kit_json}
        jobs_list.append({
            "id": j.id,
            "job_title": j.job_title,
            "company_name": j.company_name,
            "location": j.location,
            "work_mode": j.work_mode,
            "salary_range": j.salary_range,
            "match_score": j.match_score,
            "status": j.status,
            "job_url": j.job_url,
            "applied_date": j.applied_date,
            "notes": j.notes,
            "application_kit": app_kit,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        })

    # 4. Billing Audit History
    orders_list = [
        {
            "order_id": o.order_id,
            "target_plan": o.target_plan,
            "billing_cycle": o.billing_cycle,
            "amount": o.amount,
            "currency": o.currency,
            "gateway": o.gateway,
            "status": o.status,
            "payment_method": o.payment_method,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in current_user.online_orders
    ]

    slips_list = [
        {
            "id": s.id,
            "target_plan": s.target_plan,
            "amount_paid": s.amount_paid,
            "currency": s.currency,
            "status": s.status,
            "bank_reference": s.bank_reference,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in current_user.bank_payment_slips
    ]

    # 5. Compile Compliant Export Bundle
    export_bundle = {
        "_compliance_metadata": {
            "legal_framework": "Sri Lanka Personal Data Protection Act No. 9 of 2022 (PDPA) & EU GDPR",
            "statutory_right": "Section 13 (Right of Access) & Article 20 (Data Portability)",
            "data_controller": "DreemFolio AI (privacy@dreemfolio.com, Hambanthota, Sri Lanka)",
            "privacy_policy_url": "https://dreemfolio.com/privacy",
            "export_timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "ai_training_guarantee": "Zero AI retention: Resumes and personal texts are never used to train base foundation AI models.",
            "payment_security": "PCI-DSS Level 1 compliant: Zero credit/debit card numbers stored on our servers."
        },
        "user_profile": user_info,
        "saved_resumes": resumes_list,
        "job_applications": jobs_list,
        "billing_records": {
            "online_orders": orders_list,
            "bank_deposit_slips": slips_list,
        }
    }

    file_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', current_user.email.split('@')[0])
    date_str = datetime.date.today().strftime("%Y%m%d")
    filename = f"dreemfolio_data_{file_slug}_{date_str}.json"
    json_bytes = json.dumps(export_bundle, indent=2, ensure_ascii=False).encode("utf-8")

    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.delete("/api/auth/delete-account")
async def delete_my_account(
    req: DeleteAccountRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Statutory Right to Erasure / 'Right to Be Forgotten' (PDPA No. 9 of 2022 Sec 15 / GDPR Art 17).
    Permanently erases all user profile records, resumes, cover letters, and associated personal assets.
    """
    # 1. Validate confirmation keyword
    if req.confirmation.strip().upper() != "DELETE":
        raise HTTPException(
            status_code=400,
            detail="Confirmation mismatch. Please enter 'DELETE' in uppercase to permanently erase your account."
        )

    # 2. Check password verification for email-registered accounts
    if current_user.auth_provider == "email" and current_user.hashed_password:
        if not req.password:
            raise HTTPException(
                status_code=400,
                detail="Your current password is required to verify identity and authorize account deletion."
            )
        if not verify_password(req.password, current_user.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="Incorrect password. Account deletion aborted."
            )

    # 3. Protect against accidental deletion of the last admin
    if current_user.is_admin:
        admin_count = db.scalar(
            select(func.count(User.id)).where(
                User.is_admin == True,
                User.id != current_user.id,
                User.is_active == True
            )
        ) or 0
        if admin_count == 0:
            raise HTTPException(
                status_code=400,
                detail="This account is the sole active administrator of DreemFolio AI and cannot be deleted. Please appoint another administrator first."
            )

    user_id = current_user.id
    user_email = current_user.email

    # 4. Clean up any stored bank slip uploads on disk
    try:
        slips_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "slips")
        for slip in current_user.bank_payment_slips:
            if slip.slip_image_url and "/static/uploads/slips/" in slip.slip_image_url:
                file_name = os.path.basename(slip.slip_image_url)
                full_path = os.path.join(slips_dir, file_name)
                if os.path.exists(full_path):
                    os.remove(full_path)
    except Exception as e:
        logger.warning("Error purging user slip uploads during account erasure: %s", e)

    # 5. Purge user from in-memory caches and published portfolio registry
    try:
        from app.state import PUBLISHED_PORTFOLIOS, PUBLISHED_RESUMES
        slugs_to_remove = []
        for slug, res_obj in list(PUBLISHED_RESUMES.items()):
            if getattr(res_obj, "user_id", None) == user_id or getattr(res_obj, "email", None) == user_email:
                slugs_to_remove.append(slug)
        for s in slugs_to_remove:
            PUBLISHED_RESUMES.pop(s, None)
            PUBLISHED_PORTFOLIOS.pop(s, None)
    except Exception as e:
        logger.warning("Error cleaning in-memory state for user %s: %s", user_id, e)

    # 6. Permanently delete user from database (triggers ON DELETE CASCADE for resumes, job applications, orders)
    db.delete(current_user)
    db.commit()

    logger.info("PDPA Section 15 Erasure completed: User ID %s (%s) erased permanently.", user_id, user_email)

    return {
        "success": True,
        "message": "Your account and all associated personal data have been permanently erased in compliance with the Sri Lanka Personal Data Protection Act No. 9 of 2022."
    }

