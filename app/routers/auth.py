import os
import secrets
import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import User
from app.schemas import (
    GoogleConfigResponse, GoogleAuthRequest, TokenResponse,
    UserRegisterRequest, UserLoginRequest, ForgotPasswordRequest,
    ResetPasswordRequest, UserResponse
)
from app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, check_and_update_subscription,
    get_saas_setting, verify_google_credential_token
)
from app.state import build_user_response
from app.email_service import (
    send_user_welcome_email, send_admin_new_user_alert,
    send_user_forgot_password, send_user_password_reset_success
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

    google_sub = google_info["sub"]
    google_email = google_info["email"]
    google_name = google_info.get("name") or "Candidate"
    google_picture = google_info.get("picture")

    # 1. Lookup by google_id
    stmt = select(User).where(User.google_id == google_sub)
    user = db.scalars(stmt).first()

    if not user:
        # 2. Lookup by email for safe account linking (Google verified the email!)
        stmt_email = select(User).where(User.email == google_email)
        user = db.scalars(stmt_email).first()

        if user:
            # Safe account linking: Link Google ID to existing account
            user.google_id = google_sub
            if google_picture and not user.avatar_url:
                user.avatar_url = google_picture
            if not user.auth_provider or user.auth_provider == "email":
                user.auth_provider = "google"
            db.commit()
            db.refresh(user)
        else:
            # 3. Create brand new user
            now = datetime.datetime.utcnow()
            random_pw = secrets.token_urlsafe(32)
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
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            base_url = str(request.base_url).rstrip("/")
            send_user_welcome_email(user.email, user.full_name, base_url, background_tasks)
            send_admin_new_user_alert(user.email, user.full_name, "Google", base_url, db, background_tasks)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your account has been deactivated.")

    check_and_update_subscription(user, db)
    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=build_user_response(user, db)
    )


@router.post("/api/auth/register", response_model=TokenResponse)
async def register_user(
    req: UserRegisterRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Register a new SaaS user with secure bcrypt hashing (Defaults to Free Starter Tier)."""
    email_clean = req.email.strip().lower()
    stmt = select(User).where(User.email == email_clean)
    existing = db.scalars(stmt).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email address already exists. Please log in."
        )

    user = User(
        email=email_clean,
        hashed_password=hash_password(req.password),
        full_name=req.full_name.strip() or "Candidate",
        plan_tier="free",  # Default Free Starter Tier
        subscription_status="active"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    base_url = str(request.base_url).rstrip("/")
    send_user_welcome_email(user.email, user.full_name, base_url, background_tasks)
    send_admin_new_user_alert(user.email, user.full_name, "Email", base_url, db, background_tasks)

    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=build_user_response(user, db)
    )


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
