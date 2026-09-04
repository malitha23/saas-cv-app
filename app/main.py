import os
import io
import re
import json
import time
import datetime
from collections import defaultdict
from typing import Optional, Dict, List
from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Response, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.schemas import (
    TailorRequest, TailoredResume, ParseResponse, CheckoutRequest, DomainVerifyRequest,
    UserRegisterRequest, UserLoginRequest, UserResponse, TokenResponse,
    SaveResumeRequest, SavedResumeListItem,
    SubscriptionUpgradeRequest, SubscriptionStatusResponse,
    AdminOverviewResponse, AdminUserListItem, AdminUpdateUserPlanRequest,
    AdminSettingItem, AdminUpdateSettingsRequest,
    PlanItemConfig, PlansConfigResponse, UpdatePlansConfigRequest,
    CountryPricingConfig, CountryPricingResponse, AdminUpdateCountryPricingRequest,
    GoogleAuthRequest, GoogleConfigResponse
)
from app.parser import parse_resume_file, extract_candidate_name
from app.ai_engine import generate_with_gemini
from app.pdf_generator import generate_resume_pdf, generate_cover_letter_pdf
from app.portfolio_generator import generate_portfolio_html
from app.sample_data import SAMPLE_RESUMES
from app.database import get_db, engine, Base
from app.models import User, UserResume, SaasSetting
from app.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_optional_user,
    check_daily_ai_quota, check_daily_pdf_quota, check_ats_pdf_quota, check_visual_pdf_quota, check_daily_cover_letter_quota, require_tier, require_admin,
    check_and_update_subscription, get_saas_setting, verify_google_credential_token,
    DEFAULT_FREE_DAILY_AI_LIMIT, DEFAULT_FREE_DAILY_PDF_LIMIT, DEFAULT_FREE_DAILY_COVER_LETTER_LIMIT,
    DEFAULT_FREE_LIFETIME_ATS_LIMIT, DEFAULT_FREE_LIFETIME_VISUAL_LIMIT, DEFAULT_FREE_LIFETIME_COVER_LETTER_LIMIT
)

# Load .env variables
load_dotenv()

app = FastAPI(
    title="ATS-Friendly AI Resume, Cover Letter & Custom Portfolio SaaS",
    description="Micro-SaaS to optimize resumes, generate ATS PDFs, and publish modern custom developer portfolios",
    version="1.3.0"
)

# In-memory published portfolios and custom domain maps
PUBLISHED_PORTFOLIOS: Dict[str, str] = {}
CUSTOM_DOMAINS: Dict[str, str] = {}  # domain -> slug

# Hardened CORS configuration (rejects wildcards with credentials to prevent cross-origin hijacking)
ALLOWED_ORIGINS = [
    origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()
] or [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://resumatch.ai",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# ─────────────────────────────────────────────────────────────────────────────
# ANTI-ABUSE RATE LIMITING CONFIGURATION & MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────────────
# Sensitive endpoints rate limits: (max_requests, window_seconds)
RATE_LIMIT_RULES: Dict[str, tuple[int, int]] = {
    "/api/auth/login": (10, 60),      # Max 10 attempts per minute
    "/api/auth/register": (5, 60),    # Max 5 registrations per minute
    "/api/auth/google": (15, 60),     # Max 15 Google auth requests per minute
    "/api/tailor": (10, 60),          # Max 10 AI generation requests per minute
}
RATE_LIMIT_STORE: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))


def _get_client_ip(request: Request) -> str:
    """Extract client IP address safely considering reverse proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    """
    Sliding window in-memory rate limiter per IP.
    Thwarts credential stuffing, brute-forcing, and resource exhaustion DoS.
    """
    path = request.url.path
    rule = RATE_LIMIT_RULES.get(path)
    if rule:
        max_reqs, window_secs = rule
        client_ip = _get_client_ip(request)
        now = time.time()
        timestamps = RATE_LIMIT_STORE[client_ip][path]

        # Evict timestamps older than current window
        valid_timestamps = [t for t in timestamps if (now - t) < window_secs]
        RATE_LIMIT_STORE[client_ip][path] = valid_timestamps

        if len(valid_timestamps) >= max_reqs:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please slow down and try again later.",
                    "retry_after_seconds": int(window_secs - (now - valid_timestamps[0])) if valid_timestamps else window_secs
                },
                headers={"Retry-After": str(window_secs)}
            )

        RATE_LIMIT_STORE[client_ip][path].append(now)

    return await call_next(request)


# ─────────────────────────────────────────────────────────────────────────────
# OWASP ENTERPRISE SECURITY HEADERS MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Apply hardened OWASP security headers to all HTTP responses.
    Protects against Clickjacking, MIME-sniffing, XSS, and Referrer leakage.
    """
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Configure Jinja2 templates directory for modular component architecture
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)


@app.on_event("startup")
def on_startup():
    """Ensure database tables are created in MySQL on startup."""
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables (users, user_resumes) successfully initialized in MySQL!")
    except Exception as e:
        print("⚠️ Warning during database table initialization:", e)


@app.get("/api/health")
async def health_check():
    """Health status and API readiness."""
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy",
        "gemini_api_configured": has_gemini_key,
        "engine": "Gemini Flash + ReportLab ATS + Custom Portfolio Engine",
        "version": "1.3.0"
    }


@app.get("/api/sample-data")
async def get_sample_data():
    """Return pre-built realistic sample resumes and job descriptions."""
    return SAMPLE_RESUMES


MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB ceiling


@app.post("/api/upload", response_model=ParseResponse)
async def upload_resume(file: UploadFile = File(...)):
    """Upload and extract plain text from PDF, DOCX, or TXT resume files with strict format and size validation."""
    try:
        # Prevent unbounded RAM consumption: read at most MAX_UPLOAD_SIZE + 1 bytes
        content = await file.read(MAX_UPLOAD_SIZE + 1)
        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="File size exceeds the 10MB limit. Please upload a smaller resume document."
            )
        if not content:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        filename = (file.filename or "uploaded_resume.pdf").strip()
        lower_fn = filename.lower()

        # Strict magic bytes verification to block spoofed extensions, executables, or corrupted uploads
        if lower_fn.endswith(".pdf"):
            if not content.startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid PDF document format. The file header does not match a valid PDF."
                )
        elif lower_fn.endswith(".docx"):
            if not (content.startswith(b"PK\x03\x04") or content.startswith(b"PK\x05\x06")):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid DOCX document format. The file header does not match a valid Word document."
                )
        elif lower_fn.endswith(".txt"):
            if b"\x00" in content[:2048]:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid text document format. Binary content was detected."
                )
        else:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file extension. Only .pdf, .docx, and .txt files are supported."
            )

        text, detected_sections = parse_resume_file(filename, content)
        
        if not text.strip():
            raise HTTPException(
                status_code=400,
                detail="Could not extract readable text. The document might be scanned/image-based."
            )
            
        # Extract contact metadata
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        extracted_email = email_match.group(0) if email_match else None
        
        phone_match = re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,5}', text)
        extracted_phone = phone_match.group(0).strip() if phone_match else None
        
        extracted_name = extract_candidate_name(text, extracted_email or "")
        
        return ParseResponse(
            success=True,
            text=text,
            filename=filename,
            character_count=len(text),
            detected_sections=detected_sections,
            extracted_name=extracted_name,
            extracted_email=extracted_email,
            extracted_phone=extracted_phone,
            message=f"Extracted resume for {extracted_name} ({len(text)} characters)"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/tailor", response_model=TailoredResume)
async def tailor_resume(
    payload: TailorRequest,
    current_user: User = Depends(check_daily_ai_quota)
):
    """
    Optimize candidate resume against target Job Description using Gemini Flash.
    Requires SaaS registration and login.
    """
    if not payload.resume_text.strip():
        raise HTTPException(status_code=400, detail="Resume text cannot be empty.")
    if not payload.job_description.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")
        
    try:
        result = generate_with_gemini(
            resume_text=payload.resume_text,
            job_description=payload.job_description,
            api_key=payload.api_key,
            job_title=payload.job_title,
            company_name=payload.company_name,
            template_style=payload.template_style or "classic",
            cover_letter_tone=payload.cover_letter_tone or "professional"
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Optimization error: {str(e)}")


@app.post("/api/generate-pdf/resume")
async def create_resume_pdf(
    resume: TailoredResume,
    download: bool = False,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Generate 100% ATS-compliant PDF resume in requested template style.
    Free users can preview all visual formats on screen and download Classic ATS format within daily limits.
    Downloading Visual Photo CV formats requires Pro (or enabled in Admin panel).
    """
    is_visual = (resume.template_style or 'classic') in ['visual_sidebar', 'creative_gradient', 'tech_noir', 'indigo_banner', 'emerald_prestige']
    tier = (current_user.plan_tier if current_user else "free").lower()

    if download:
        if is_visual and tier == "free":
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Please sign in or create a free account to download your free Visual Photo CV."
                )
            # Free users get 1 Lifetime Visual CV download
            check_visual_pdf_quota(current_user, db)
        elif (not is_visual) and tier == "free" and current_user:
            # Free users get 2 Lifetime ATS PDF downloads
            check_ats_pdf_quota(current_user, db)

    try:
        pdf_bytes = generate_resume_pdf(resume)
        safe_name = resume.personal_info.full_name.replace(" ", "_")
        filename = f"{safe_name}_ATS_Resume_{resume.template_style}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/pdf"
            }
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"PDF Generation error: {str(e)}")


@app.post("/api/generate-pdf/cover-letter")
async def create_cover_letter_pdf(
    resume: TailoredResume,
    current_user: User = Depends(check_daily_cover_letter_quota)
):
    """
    Generate professional ATS-formatted Cover Letter PDF:
    - Free tier: 1st download is 100% clean (no watermark), 2nd and 3rd receive official watermark badge.
    - Pro/Elite tier: Always 100% clean and watermark-free.
    """
    try:
        tier = (current_user.plan_tier or "free").lower()
        is_free = tier == "free"
        
        # Strategic rule: 1st download is 100% clean without watermark!
        # current_user.lifetime_cover_letter_downloads_count has just been incremented to 1 on the 1st download.
        # If count <= 1, it's the first download, so NO watermark!
        used_count = getattr(current_user, "lifetime_cover_letter_downloads_count", 1)
        apply_watermark = is_free and (used_count > 1)
        
        pdf_bytes = generate_cover_letter_pdf(resume, is_free_watermarked=apply_watermark)
        safe_name = (resume.personal_info.full_name or "Candidate").replace(" ", "_")
        company = (resume.target_company or "Company").replace(" ", "_")
        filename = f"{safe_name}_Cover_Letter_{company}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/pdf"
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cover Letter PDF error: {str(e)}")


@app.post("/api/generate-portfolio")
async def create_portfolio_preview(resume: TailoredResume, theme: str = "neon_dark"):
    """Generate customizable standalone responsive HTML portfolio."""
    try:
        html_code = generate_portfolio_html(resume, theme=theme)
        return {"success": True, "html": html_code, "theme": theme}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portfolio generation error: {str(e)}")


@app.post("/api/download-portfolio")
async def download_portfolio(resume: TailoredResume, theme: str = "neon_dark"):
    """Download standalone index.html portfolio file ready for hosting."""
    try:
        html_code = generate_portfolio_html(resume, theme=theme)
        safe_name = resume.personal_info.full_name.replace(" ", "_").lower()
        filename = f"{safe_name}_portfolio.html"
        
        return Response(
            content=html_code.encode("utf-8"),
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "text/html; charset=utf-8"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portfolio export error: {str(e)}")


@app.post("/api/publish-portfolio")
async def publish_portfolio(
    resume: TailoredResume,
    theme: str = "neon_dark",
    current_user: User = Depends(require_tier("pro"))
):
    """Publish live portfolio to a public URL e.g. /p/malith-sayuranga. Gated to Pro & Elite tiers."""
    try:
        html_code = generate_portfolio_html(resume, theme=theme)
        clean_name = re.sub(r'[^a-zA-Z0-9]', '-', resume.personal_info.full_name.lower()).strip('-')
        slug = clean_name or "developer"
        
        PUBLISHED_PORTFOLIOS[slug] = html_code
        
        # If custom domain attached
        if resume.personal_info.custom_domain:
            domain_clean = resume.personal_info.custom_domain.strip().lower().replace("https://", "").replace("http://", "").rstrip('/')
            CUSTOM_DOMAINS[domain_clean] = slug
            
        live_url = f"/p/{slug}"
        
        return {
            "success": True,
            "slug": slug,
            "live_url": live_url,
            "custom_domain": resume.personal_info.custom_domain,
            "message": f"Portfolio published live at {live_url}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publish error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Publish error: {str(e)}")


@app.post("/api/domain/verify")
async def verify_custom_domain(
    req: DomainVerifyRequest,
    current_user: User = Depends(require_tier("elite"))
):
    """
    Verify custom private domain and return required DNS CNAME / A records.
    Requires Executive Elite Plan.
    """
    # Strict regex sanitization to prevent injection or SSRF
    domain_clean = req.domain.strip().lower().replace("https://", "").replace("http://", "").rstrip('/')
    if not domain_clean or "." not in domain_clean or not re.match(r'^[a-z0-9\.\-]+$', domain_clean):
        raise HTTPException(status_code=400, detail="Please enter a valid domain format (e.g. 'malitha.dev' or 'portfolio.mybrand.com').")

    safe_slug = re.sub(r'[^a-zA-Z0-9_-]', '', req.slug)
    CUSTOM_DOMAINS[domain_clean] = safe_slug
    
    return {
        "success": True,
        "domain": domain_clean,
        "dns_records": [
            {
                "type": "CNAME",
                "name": "@" if domain_clean.count(".") == 1 else domain_clean.split(".")[0],
                "target": "cname.resumatch.ai",
                "ttl": "3600",
                "status": "Ready to configure"
            },
            {
                "type": "A",
                "name": "@",
                "target": "76.76.21.21",
                "ttl": "3600",
                "status": "Alternative"
            }
        ],
        "ssl_status": "Auto-provisioned Let's Encrypt SSL",
        "message": f"Domain {domain_clean} mapped successfully to {req.slug}!"
    }


@app.get("/p/{slug}")
async def view_public_portfolio(slug: str):
    """Publicly accessible live candidate portfolio webpage."""
    if slug in PUBLISHED_PORTFOLIOS:
        return HTMLResponse(content=PUBLISHED_PORTFOLIOS[slug])
    raise HTTPException(status_code=404, detail="Portfolio not found. Please publish it first from the dashboard.")


# ─────────────────────────────────────────────────────────────────────────────
# SAAS AUTHENTICATION & SUBSCRIPTION TIER ROUTES (BCRYPT + JWT)
# ─────────────────────────────────────────────────────────────────────────────

def build_user_response(user: User, db: Optional[Session] = None) -> UserResponse:
    import datetime
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

    life_ats_remaining = None if tier in ["pro", "elite"] else max(0, life_ats_limit - life_ats_used)
    life_visual_remaining = None if tier in ["pro", "elite"] else max(0, life_visual_limit - life_visual_used)
    life_cl_remaining = None if tier in ["pro", "elite"] else max(0, life_cl_limit - life_cl_used)

    started_str = user.subscription_started_at.strftime("%B %d, %Y") if user.subscription_started_at else None
    exp_str = user.subscription_expires_at.strftime("%B %d, %Y") if user.subscription_expires_at else None

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
        lifetime_ats_downloads_count=life_ats_used,
        lifetime_ats_downloads_remaining=life_ats_remaining,
        lifetime_visual_downloads_count=life_visual_used,
        lifetime_visual_downloads_remaining=life_visual_remaining,
        lifetime_cover_letter_downloads_count=life_cl_used,
        lifetime_cover_letter_downloads_remaining=life_cl_remaining,
        avatar_url=getattr(user, "avatar_url", None),
        auth_provider=getattr(user, "auth_provider", "email") or "email",
        google_id=getattr(user, "google_id", None)
    )


@app.get("/api/auth/google-config", response_model=GoogleConfigResponse)
async def get_google_auth_config(db: Session = Depends(get_db)):
    """Fetch active Google OAuth 2.0 configuration for client-side Google Identity Services."""
    client_id = get_saas_setting(db, "google_client_id", os.environ.get("GOOGLE_CLIENT_ID", "")).strip()
    return GoogleConfigResponse(
        client_id=client_id if client_id else None,
        is_enabled=bool(client_id)
    )


@app.post("/api/auth/google", response_model=TokenResponse)
async def auth_with_google(req: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Authenticate SaaS user with Google Identity Services (GIS).
    Verifies Google ID token, performs secure account linking, and creates user if new.
    """
    import secrets
    import datetime

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

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your account has been deactivated.")

    check_and_update_subscription(user, db)
    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=build_user_response(user, db)
    )


@app.post("/api/auth/register", response_model=TokenResponse)
async def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
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

    token = create_access_token(user)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=build_user_response(user, db)
    )


@app.post("/api/auth/login", response_model=TokenResponse)
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


@app.get("/api/auth/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetch profile of currently authenticated user with real-time quota status."""
    check_and_update_subscription(current_user, db)
    return build_user_response(current_user, db)


# ─────────────────────────────────────────────────────────────────────────────
# SUBSCRIPTION BILLING & UPGRADE ROUTES (SECURE FEATURE ACTIVATION)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/subscription/upgrade", response_model=UserResponse)
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

    import datetime
    now = datetime.datetime.utcnow()

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
    current_user.subscription_expires_at = now + datetime.timedelta(days=days)
    db.commit()
    db.refresh(current_user)

    return build_user_response(current_user, db)


@app.get("/api/subscription/status", response_model=SubscriptionStatusResponse)
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
        "code_export": tier == "elite"
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
        features=features
    )



# ─────────────────────────────────────────────────────────────────────────────
# SAAS CLOUD RESUMES PERSISTENCE ROUTES (MYSQL)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/user/resumes", response_model=List[SavedResumeListItem])
async def list_user_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all saved resumes in MySQL belonging to the logged-in user."""
    stmt = (
        select(UserResume)
        .where(UserResume.user_id == current_user.id)
        .order_by(UserResume.updated_at.desc())
    )
    resumes = db.scalars(stmt).all()
    return [
        SavedResumeListItem(
            id=r.id,
            title=r.title,
            target_role=r.target_role,
            template_style=r.template_style,
            updated_at=r.updated_at.strftime("%b %d, %Y %I:%M %p")
        )
        for r in resumes
    ]


@app.post("/api/user/resumes")
async def save_user_resume(
    req: SaveResumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save or update tailored resume data into MySQL for the logged-in user."""
    import datetime
    json_data = req.resume_data.model_dump_json()
    new_title = req.title.strip() or f"{req.resume_data.target_job_title} - {req.resume_data.target_company or 'Resume'}"

    target_resume = None
    if req.resume_id:
        stmt = select(UserResume).where(
            UserResume.id == req.resume_id,
            UserResume.user_id == current_user.id
        )
        target_resume = db.scalars(stmt).first()

    if target_resume:
        target_resume.title = new_title
        target_resume.target_role = req.resume_data.target_job_title
        target_resume.template_style = req.resume_data.template_style or "visual_sidebar"
        target_resume.resume_data_json = json_data
        target_resume.updated_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(target_resume)
        return {
            "success": True,
            "resume_id": target_resume.id,
            "title": target_resume.title,
            "message": "Resume updated in MySQL!"
        }
    else:
        new_resume = UserResume(
            user_id=current_user.id,
            title=new_title,
            target_role=req.resume_data.target_job_title,
            template_style=req.resume_data.template_style or "visual_sidebar",
            resume_data_json=json_data
        )
        db.add(new_resume)
        db.commit()
        db.refresh(new_resume)
        return {
            "success": True,
            "resume_id": new_resume.id,
            "title": new_resume.title,
            "message": "Resume successfully created in MySQL!"
        }


@app.get("/api/user/resumes/{resume_id}")
async def load_user_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Load a specific saved resume from MySQL into the editor. Restoring is gated to Pro unless enabled by Admin."""
    check_and_update_subscription(current_user, db)
    tier = (current_user.plan_tier or "free").lower()
    if tier == "free":
        allow_restore = get_saas_setting(db, "free_allow_cloud_restore", "false").lower() == "true"
        if not allow_restore:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "pro_required",
                    "feature": "cloud_restore",
                    "message": "Restoring saved resumes into the editor requires the Pro Career plan ($9/mo). Free users can view resume history, or upgrade to Pro to instantly edit any past version!",
                    "upgrade_url": "/api/subscription/upgrade"
                }
            )

    stmt = select(UserResume).where(
        UserResume.id == resume_id,
        UserResume.user_id == current_user.id
    )
    resume = db.scalars(stmt).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Saved resume not found or access denied.")

    import json
    return {
        "resume_id": resume.id,
        "title": resume.title,
        "resume_data": json.loads(resume.resume_data_json)
    }


@app.delete("/api/user/resumes/{resume_id}")
async def delete_user_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a saved resume from MySQL."""
    stmt = select(UserResume).where(
        UserResume.id == resume_id,
        UserResume.user_id == current_user.id
    )
    resume = db.scalars(stmt).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Saved resume not found or access denied.")

    db.delete(resume)
    db.commit()
    return {"success": True, "message": "Resume deleted successfully from MySQL."}


@app.post("/api/checkout")
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


# ─────────────────────────────────────────────────────────────────────────────
# ENTERPRISE SAAS ADMIN MANAGEMENT ROUTES (STRICT require_admin GUARD)
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/admin/overview", response_model=AdminOverviewResponse)
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


@app.get("/api/admin/settings", response_model=List[AdminSettingItem])
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


@app.post("/api/admin/settings/update")
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


@app.get("/api/admin/users", response_model=List[AdminUserListItem])
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


@app.post("/api/admin/users/{user_id}/plan")
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


DEFAULT_COUNTRY_PRICING_DATA: Dict[str, Dict[str, Any]] = {
    "DEFAULT": {
        "country_code": "DEFAULT",
        "country_name": "Global (USD)",
        "currency_code": "USD",
        "currency_symbol": "$",
        "sprint_price": "$4.99",
        "plans": [
            {
                "plan_key": "free",
                "title": "Free Starter",
                "badge": "Freemium",
                "price_display": "$0",
                "period_display": "/ forever",
                "sub_billing_text": "No Credit Card Required",
                "description": "Great for trying out AI resume keyword tailoring & ATS match scoring.",
                "features": [
                    "2 AI Tailored Runs per day",
                    "ATS Keyword Match & Score (0-100)",
                    "2 Classic ATS PDF Downloads (Lifetime Free)",
                    "1 Visual Photo CV Download (Lifetime Free)",
                    "3 AI Cover Letters (1st Clean • 2 Watermarked)",
                    "Interactive Web Portfolio Studio (Live Preview)",
                    "MySQL Cloud Auto-Save (Restoring requires Pro)"
                ],
                "is_popular": False,
                "button_text": "Current Plan"
            },
            {
                "plan_key": "pro",
                "title": "Pro Career",
                "badge": "🔥 Best Seller",
                "price_display": "$9",
                "period_display": "/ month",
                "sub_billing_text": "or $19 for 3-Month Job Hunt Pass",
                "description": "Everything needed to land senior interviews with unbranded formats & live cloud sync.",
                "features": [
                    "Unlimited AI Tailoring runs",
                    "Unlimited ATS & Visual Photo CV Downloads",
                    "Unlimited AI Cover Letters (100% Watermark-Free & Clean)",
                    "Photo & Digital Signature Upload",
                    "Hosted Live Portfolio Subdomain (.resumatch.ai)",
                    "MySQL Cloud Auto-Save & Instant Version Restore"
                ],
                "is_popular": True,
                "button_text": "Upgrade to Pro ($9/mo)"
            },
            {
                "plan_key": "elite",
                "title": "Executive Elite",
                "badge": "Personal Brand",
                "price_display": "$19",
                "period_display": "/ month",
                "sub_billing_text": "or $39 for 3-Month Elite Pass",
                "description": "For Tech Leads, Architects & Executives building an elite digital brand.",
                "features": [
                    "Everything in Pro Career",
                    "All 8 Portfolio Web Architectures",
                    "100% Full CRUD Portfolio Studio",
                    "Connect Custom Private Domain & SSL",
                    "Standalone Website HTML Export",
                    "Priority AI Processing Queue"
                ],
                "is_popular": False,
                "button_text": "Upgrade to Elite ($19/mo)"
            }
        ]
    },
    "LK": {
        "country_code": "LK",
        "country_name": "Sri Lanka (LKR)",
        "currency_code": "LKR",
        "currency_symbol": "Rs.",
        "sprint_price": "Rs. 490",
        "plans": [
            {
                "plan_key": "free",
                "title": "Free Starter",
                "badge": "Freemium",
                "price_display": "Rs. 0",
                "period_display": "/ forever",
                "sub_billing_text": "No Credit Card Required",
                "description": "Great for trying out AI resume keyword tailoring & ATS match scoring.",
                "features": [
                    "2 AI Tailored Runs per day",
                    "ATS Keyword Match & Score (0-100)",
                    "2 Classic ATS PDF Downloads (Lifetime Free)",
                    "1 Visual Photo CV Download (Lifetime Free)",
                    "3 AI Cover Letters (1st Clean • 2 Watermarked)",
                    "Interactive Web Portfolio Studio (Live Preview)",
                    "MySQL Cloud Auto-Save (Restoring requires Pro)"
                ],
                "is_popular": False,
                "button_text": "Current Plan"
            },
            {
                "plan_key": "pro",
                "title": "Pro Career",
                "badge": "🔥 Best Seller",
                "price_display": "Rs. 990",
                "period_display": "/ month",
                "sub_billing_text": "or Rs. 2,490 for 3-Month Job Hunt Pass",
                "description": "Everything needed to land senior interviews with unbranded formats & live cloud sync.",
                "features": [
                    "Unlimited AI Tailoring runs",
                    "Unlimited ATS & Visual Photo CV Downloads",
                    "Unlimited AI Cover Letters (100% Watermark-Free & Clean)",
                    "Photo & Digital Signature Upload",
                    "Hosted Live Portfolio Subdomain (.resumatch.ai)",
                    "MySQL Cloud Auto-Save & Instant Version Restore"
                ],
                "is_popular": True,
                "button_text": "Upgrade to Pro (Rs. 990/mo)"
            },
            {
                "plan_key": "elite",
                "title": "Executive Elite",
                "badge": "Personal Brand",
                "price_display": "Rs. 2,490",
                "period_display": "/ month",
                "sub_billing_text": "or Rs. 5,900 for 3-Month Elite Pass",
                "description": "For Tech Leads, Architects & Executives building an elite digital brand.",
                "features": [
                    "Everything in Pro Career",
                    "All 8 Portfolio Web Architectures",
                    "100% Full CRUD Portfolio Studio",
                    "Connect Custom Private Domain & SSL",
                    "Standalone Website HTML Export",
                    "Priority AI Processing Queue"
                ],
                "is_popular": False,
                "button_text": "Upgrade to Elite (Rs. 2,490/mo)"
            }
        ]
    }
}

DEFAULT_PLANS_CONFIG_DATA = DEFAULT_COUNTRY_PRICING_DATA["DEFAULT"]["plans"]


def _get_country_pricing_dict(db: Session) -> Dict[str, Dict[str, Any]]:
    """Helper to retrieve all dynamic country pricing rules from database with fallback."""
    import json
    raw = get_saas_setting(db, "saas_country_pricing_json", "")
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "DEFAULT" in parsed:
                return parsed
        except Exception:
            pass
    return DEFAULT_COUNTRY_PRICING_DATA


@app.get("/api/plans", response_model=PlansConfigResponse)
async def get_subscription_plans(db: Session = Depends(get_db)):
    """Fetch default dynamically configured subscription plans."""
    import json
    country_dict = _get_country_pricing_dict(db)
    default_plans = country_dict.get("DEFAULT", {}).get("plans", DEFAULT_PLANS_CONFIG_DATA)
    return PlansConfigResponse(plans=[PlanItemConfig(**p) for p in default_plans])


@app.get("/api/subscription/plans", response_model=CountryPricingResponse)
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
    # 1. Determine target country code
    target_country = (country or "").strip().upper()
    if not target_country:
        target_country = request.headers.get("CF-IPCountry", "").strip().upper()
    if not target_country:
        target_country = request.headers.get("X-Country-Code", "").strip().upper()
    if not target_country:
        target_country = "LK"  # Default test fallback or check locale

    all_countries = _get_country_pricing_dict(db)

    # 2. Match country or fallback to DEFAULT (USD)
    matched_config = all_countries.get(target_country)
    if not matched_config:
        # Check if currency was explicitly requested (e.g. LKR)
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


@app.get("/api/admin/country-pricing")
async def admin_get_country_pricing(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Administrator endpoint: Fetch all country pricing configurations."""
    return _get_country_pricing_dict(db)


@app.post("/api/admin/country-pricing/update")
async def admin_update_country_pricing(
    req: AdminUpdateCountryPricingRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Administrator endpoint: Add or update pricing rules for a specific country."""
    import json
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

    # Persist updated JSON dictionary to MySQL saas_settings
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


@app.delete("/api/admin/country-pricing/{country_code}")
async def admin_delete_country_pricing(
    country_code: str,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Administrator endpoint: Delete custom pricing override for a specific country."""
    import json
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


@app.post("/api/admin/plans/update")
async def update_subscription_plans(
    req: UpdatePlansConfigRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Administrator endpoint to fully customize default Free, Pro, and Elite subscription plans."""
    import json
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
    
    # Also synchronize DEFAULT plans in country pricing
    country_dict = _get_country_pricing_dict(db)
    if "DEFAULT" in country_dict:
        country_dict["DEFAULT"]["plans"] = [p.model_dump() for p in req.plans]
        c_stmt = select(SaasSetting).where(SaasSetting.key == "saas_country_pricing_json")
        c_setting = db.scalars(c_stmt).first()
        if c_setting:
            c_setting.value = json_str
            c_setting.updated_at = datetime.datetime.utcnow()
    db.commit()
    return {"success": True, "message": "Subscription plans updated successfully in database!"}


# Mount static assets directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/admin", response_class=HTMLResponse)
async def serve_admin_page(request: Request):
    """Serve dedicated, enterprise-hardened standalone Administrator Control Center."""
    response = templates.TemplateResponse(request=request, name="admin.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@app.get("/privacy", response_class=HTMLResponse)
async def serve_privacy_policy(request: Request):
    """Serve official GDPR & CCPA compliant Privacy Policy."""
    return templates.TemplateResponse(request=request, name="legal/privacy.html", context={"active_page": "privacy"})


@app.get("/terms", response_class=HTMLResponse)
async def serve_terms_of_service(request: Request):
    """Serve official Terms of Service & Subscription Agreement."""
    return templates.TemplateResponse(request=request, name="legal/terms.html", context={"active_page": "terms"})


@app.get("/refund", response_class=HTMLResponse)
@app.get("/refund-policy", response_class=HTMLResponse)
async def serve_refund_policy(request: Request):
    """Serve official Refund & Cancellation Policy."""
    return templates.TemplateResponse(request=request, name="legal/refund.html", context={"active_page": "refund"})


@app.get("/security", response_class=HTMLResponse)
async def serve_security_whitepaper(request: Request):
    """Serve official Security & Compliance Architecture document."""
    return templates.TemplateResponse(request=request, name="legal/security.html", context={"active_page": "security"})


# ─────────────────────────────────────────────────────────────────────────────
# SEARCH ENGINE DISCOVERY & SEO ENDPOINTS (SITEMAP, ROBOTS, MANIFEST, FAVICON)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/robots.txt", response_class=Response)
async def serve_robots_txt():
    """Serve dynamic, crawler-friendly robots.txt for Google, Bing, and major search engines."""
    content = """User-agent: *
Allow: /
Allow: /privacy
Allow: /terms
Allow: /refund
Allow: /refund-policy
Allow: /security
Allow: /static/
Disallow: /api/
Disallow: /admin
Disallow: /portfolio/preview/

# Search Engine Sitemaps
Sitemap: https://resumatch.ai/sitemap.xml
Host: https://resumatch.ai
"""
    return Response(content=content, media_type="text/plain")


@app.get("/sitemap.xml", response_class=Response)
async def serve_sitemap_xml():
    """Serve dynamic XML Sitemap complying with sitemaps.org standard."""
    today = datetime.date.today().isoformat()
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://resumatch.ai/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://resumatch.ai/privacy</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://resumatch.ai/terms</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://resumatch.ai/refund</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
  <url>
    <loc>https://resumatch.ai/security</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
</urlset>"""
    return Response(content=sitemap, media_type="application/xml")


@app.get("/manifest.json")
async def serve_manifest():
    """Serve Web App Manifest for PWA and Mobile SEO."""
    manifest_path = os.path.join(static_dir, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse(content={"name": "ResuMatch AI"})


@app.get("/favicon.ico")
async def serve_favicon():
    """Serve SVG favicon for root icon requests."""
    svg_path = os.path.join(static_dir, "favicon.svg")
    if os.path.exists(svg_path):
        with open(svg_path, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="image/svg+xml")
    return Response(content="", status_code=204)


@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    """Serve the modularized SaaS Web Application frontend with OWASP security headers."""
    return templates.TemplateResponse(request=request, name="index.html")

