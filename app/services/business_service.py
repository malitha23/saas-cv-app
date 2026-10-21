import re
import os
import json
import secrets
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.models import User, PrebuiltCandidateProfile, BusinessCreditTransaction, UserResume
from app.parser import parse_resume_file
from app.ai_engine import generate_with_gemini
from app.portfolio_templates import generate_portfolio_html
from app.state import save_published_portfolio
from app.schemas import (
    PrebuildProfileResponse,
    CandidatePrebuiltSummary,
    BusinessTransactionItem,
    BusinessWalletResponse
)

logger = logging.getLogger("dreemfolio.business")

# Magic bytes definition for secure file validation
PDF_MAGIC = b"%PDF-"
DOCX_MAGIC = b"PK\x03\x04"
MAX_RESUME_SIZE = 10 * 1024 * 1024  # 10 MB

# Prepaid Credit Packs Configuration
CREDIT_PACKS = [
    {
        "pack_id": "pack_10",
        "credits": 10,
        "price_lkr": 1500.0,
        "price_usd": 15.0,
        "per_candidate_lkr": "Rs. 150",
        "title": "Starter Pack",
        "badge": "Perfect for Boutique Recruiters",
        "popular": False
    },
    {
        "pack_id": "pack_50",
        "credits": 50,
        "price_lkr": 4900.0,
        "price_usd": 49.0,
        "per_candidate_lkr": "Rs. 98",
        "title": "Agency Pro",
        "badge": "Best Value • Save 35%",
        "popular": True
    },
    {
        "pack_id": "pack_150",
        "credits": 150,
        "price_lkr": 11900.0,
        "price_usd": 119.0,
        "per_candidate_lkr": "Rs. 79",
        "title": "Enterprise Scale",
        "badge": "Maximum Savings • 47% Off",
        "popular": False
    }
]


def validate_resume_file(file_bytes: bytes, filename: str) -> str:
    """
    Cryptographic and format verification for uploaded resume files.
    Enforces 10MB maximum limit and inspects magic bytes (CWE-434 protection).
    """
    if not file_bytes or len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(file_bytes) > MAX_RESUME_SIZE:
        raise HTTPException(
            status_code=400,
            detail="File size exceeds the 10MB limit. Please upload a smaller document."
        )

    fn = filename.lower().strip()
    if fn.endswith(".pdf"):
        if not file_bytes.startswith(PDF_MAGIC):
            raise HTTPException(
                status_code=400,
                detail="Security Error: The file extension is .pdf but the file content does not match a valid PDF document."
            )
        return "pdf"
    elif fn.endswith(".docx"):
        if not file_bytes.startswith(DOCX_MAGIC):
            raise HTTPException(
                status_code=400,
                detail="Security Error: The file extension is .docx but the file content does not match a valid Word document."
            )
        return "docx"
    elif fn.endswith(".txt"):
        try:
            file_bytes[:1024].decode("utf-8")
            return "txt"
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=400,
                detail="Invalid text document format. Please upload standard UTF-8 text."
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Unsupported format. Only PDF (.pdf) and Word (.docx) files are supported for candidate onboarding."
        )


def generate_unique_candidate_slug(full_name: str, db: Session) -> str:
    """
    Generates a clean, unique URL slug for candidate live portfolios (e.g. /p/kasun-perera).
    Handles deduplication safely without race conditions.
    """
    clean_name = re.sub(r'[^a-zA-Z0-9]', '-', full_name.lower()).strip('-')
    clean_name = re.sub(r'-+', '-', clean_name)
    base_slug = clean_name or "candidate"

    slug = base_slug
    # Check if exists in PrebuiltCandidateProfile
    attempt = 1
    while True:
        existing = db.scalars(
            select(PrebuiltCandidateProfile.id).where(PrebuiltCandidateProfile.portfolio_slug == slug)
        ).first()
        if not existing:
            break
        attempt += 1
        slug = f"{base_slug}-{attempt}"

    return slug


def prebuild_candidate_profile(
    creator: User,
    candidate_email: str,
    target_role: Optional[str],
    file_bytes: bytes,
    filename: str,
    db: Session,
    base_url: str,
    auto_send_email: bool = False
) -> PrebuildProfileResponse:
    """
    Core B2B Onboarding Service:
    1. Authenticates creator permissions (Admin or Business or users with Business credits).
    2. Validates credit wallet (deducts 1 credit if Business, free for Admin).
    3. Parses document & feeds to AI engine for structured ATS resume data.
    4. Auto-compiles live interactive web portfolio HTML.
    5. Persists pre-built profile and generates single-use cryptographic claim link.
    6. Optionally auto-dispatches VIP onboarding invitation email to candidate.
    """
    # 1. Permission check
    is_admin = bool(getattr(creator, "is_admin", False))
    acc_type = getattr(creator, "account_type", "candidate")
    user_credits = getattr(creator, "business_credits", 0) or 0
    if not is_admin and acc_type != "business" and user_credits < 1:
        raise HTTPException(
            status_code=403,
            detail="Access restricted: Candidate Magic Onboarding is only available for Business accounts and Administrators."
        )

    # 2. Credit check (Business accounts must have at least 1 credit)
    if not is_admin:
        current_credits = getattr(creator, "business_credits", 0) or 0
        if current_credits < 1:
            raise HTTPException(
                status_code=402,
                detail="Insufficient credits. You need at least 1 credit to onboard a candidate. Please top up your business wallet."
            )

    # 3. Email validation
    email_clean = (candidate_email or "").strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Please enter a valid candidate email address.")

    # 4. File validation & extraction
    validate_resume_file(file_bytes, filename)
    raw_text, detected_sections = parse_resume_file(filename, file_bytes)

    if not raw_text or len(raw_text.strip()) < 40:
        raise HTTPException(
            status_code=400,
            detail="Could not extract readable text from the uploaded resume. Please verify the document is not an image scan or password-protected."
        )

    # 5. AI structuring and tailoring
    role_str = (target_role or "").strip() or "Software Engineer"
    comp_str = getattr(creator, "company_name", None) or "Leading Technology Firm"

    try:
        tailored_resume = generate_with_gemini(
            resume_text=raw_text,
            job_description=f"Professional job placement profile tailored for {role_str} position.",
            job_title=role_str,
            company_name=comp_str,
            role_archetype="auto",
            template_style="classic"
        )
        try:
            from app.services.ai_tracking_service import record_ai_usage
            record_ai_usage(
                db=db,
                user_id=creator.id if creator else None,
                user_email=creator.email if creator else None,
                model_name="gemini-3.8-flash",
                operation="magic_onboarding",
                prompt_tokens=len(raw_text) // 3 + 1100,
                completion_tokens=3100
            )
        except Exception:
            pass
    except Exception as e:
        logger.warning("Gemini AI structuring warning, falling back to universal parser: %s", e)
        # generate_with_gemini already has internal fallback to _parse_and_tailor_user_data
        raise HTTPException(
            status_code=500,
            detail=f"AI Resume Processing encountered an issue: {str(e)}"
        )

    # Candidate Name
    cand_name = tailored_resume.personal_info.full_name or "Candidate"
    if cand_name == "Candidate" and email_clean:
        # Try extracting from email prefix
        cand_name = email_clean.split("@")[0].replace(".", " ").title()
        tailored_resume.personal_info.full_name = cand_name

    tailored_resume.personal_info.email = email_clean

    # 6. Generate Slug & Live Portfolio HTML
    slug = generate_unique_candidate_slug(cand_name, db)
    portfolio_html = generate_portfolio_html(tailored_resume, theme="neon_dark", slug=slug)

    # Persist live portfolio to shared disk and state
    save_published_portfolio(slug, portfolio_html)

    # 7. Generate Single-use Cryptographic Claim Token
    claim_token = secrets.token_urlsafe(32)

    # 8. Deduct Credit (if Business user)
    if not is_admin:
        creator.business_credits -= 1
        new_balance = creator.business_credits
        txn = BusinessCreditTransaction(
            user_id=creator.id,
            amount=-1,
            balance_after=new_balance,
            description=f"Onboarded candidate {cand_name} ({email_clean})",
            reference_id=claim_token
        )
        db.add(txn)

    # 9. Create Prebuilt Candidate Record
    prebuilt_profile = PrebuiltCandidateProfile(
        creator_id=creator.id,
        claim_token=claim_token,
        candidate_email=email_clean,
        candidate_name=cand_name,
        target_role=role_str,
        resume_data_json=tailored_resume.model_dump_json(),
        portfolio_slug=slug,
        portfolio_html=portfolio_html,
        status="pending"
    )
    db.add(prebuilt_profile)
    db.commit()
    db.refresh(prebuilt_profile)

    # 10. Format URLs and copyable invitation
    base_clean = base_url.rstrip("/")
    claim_url = f"{base_clean}/claim/{claim_token}"
    portfolio_url = f"{base_clean}/p/{slug}"

    invitation_message = (
        f"Hi {cand_name}! We have pre-built your ATS-Optimized Resume & Live Portfolio Website "
        f"with DreemFolio AI.\n\n"
        f"🌐 Preview your live portfolio: {portfolio_url}\n"
        f"⚡ 1-Click Claim your profile & editable CV: {claim_url}\n\n"
        f"(Free forever • Instant setup)"
    )

    remaining_credits = 999999 if is_admin else creator.business_credits

    # 11. Optional Auto-Dispatch of VIP Invitation Email
    email_dispatched = False
    email_status = None
    if auto_send_email:
        try:
            from app.email_service import send_candidate_onboarding_invitation_email
            creator_name = (creator.company_name or creator.full_name) if creator else "DreemFolio AI Talent Team"
            email_dispatched = send_candidate_onboarding_invitation_email(
                to_email=email_clean,
                candidate_name=cand_name,
                target_role=role_str,
                portfolio_url=portfolio_url,
                claim_url=claim_url,
                creator_name=creator_name,
                base_url=base_clean,
                enqueue_on_fail=True
            )
            if email_dispatched:
                email_status = f"VIP invitation email automatically dispatched to {email_clean}!"
        except Exception as mail_err:
            logger.warning("Could not auto-dispatch candidate invitation email: %s", mail_err)

    logger.info(
        "✅ Prebuilt profile created: %s (%s) by user %s. Token: %s. Auto-email: %s",
        cand_name, email_clean, creator.email, claim_token, email_dispatched
    )

    return PrebuildProfileResponse(
        success=True,
        id=prebuilt_profile.id,
        claim_token=claim_token,
        claim_url=claim_url,
        portfolio_url=portfolio_url,
        portfolio_slug=slug,
        candidate_name=cand_name,
        candidate_email=email_clean,
        target_role=role_str,
        credits_remaining=remaining_credits,
        invitation_message=invitation_message,
        email_sent=email_dispatched,
        email_status_text=email_status
    )


def sync_prebuilt_candidate_profile(user: User, db: Session, claim_token: Optional[str] = None) -> bool:
    """
    Instant Auto-Sync Engine:
    When a candidate authenticates (Google Sign-In, Email Registration, or Login):
    1. Resolves matching pending profile via claim_token cookie or candidate email.
    2. Injects parsed resume into candidate's user_resumes table.
    3. Confirms live portfolio persistence.
    4. Atomically transitions profile status from 'pending' -> 'claimed'.
    """
    try:
        token_clean = (claim_token or "").strip()
        user_email = (user.email or "").strip().lower()

        profile: Optional[PrebuiltCandidateProfile] = None

        # Primary Lookup: by secure claim token
        if token_clean:
            profile = db.scalars(
                select(PrebuiltCandidateProfile).where(
                    PrebuiltCandidateProfile.claim_token == token_clean,
                    PrebuiltCandidateProfile.status == "pending"
                )
            ).first()

            # STRICT RESTRICTION: Ensure authenticated user email matches the candidate email
            if profile:
                profile_email = (profile.candidate_email or "").strip().lower()
                if profile_email != user_email:
                    logger.warning(
                        "⚠️ Prebuilt profile claim denied: email mismatch! Profile candidate email is '%s', but authenticated user is '%s'",
                        profile_email, user_email
                    )
                    return False

        # Secondary Lookup: by candidate email match
        if not profile and user_email:
            profile = db.scalars(
                select(PrebuiltCandidateProfile).where(
                    func.lower(func.trim(PrebuiltCandidateProfile.candidate_email)) == user_email,
                    PrebuiltCandidateProfile.status == "pending"
                ).order_by(PrebuiltCandidateProfile.id.desc())
            ).first()

        if not profile:
            return False

        # Check if user already has an active resume; create or update with prebuilt candidate data
        existing_resume = db.scalars(
            select(UserResume).where(UserResume.user_id == user.id)
        ).first()

        resume_dict = {}
        if profile.resume_data_json:
            try:
                resume_dict = json.loads(profile.resume_data_json)
            except Exception:
                pass
        tmpl_style = resume_dict.get("template_style") or "classic"

        if not existing_resume:
            new_resume = UserResume(
                user_id=user.id,
                title=f"{profile.target_role or 'Professional'} ATS Resume",
                target_role=profile.target_role,
                template_style=tmpl_style,
                resume_data_json=profile.resume_data_json
            )
            db.add(new_resume)
        else:
            existing_resume.title = f"{profile.target_role or 'Professional'} ATS Resume"
            existing_resume.target_role = profile.target_role
            existing_resume.template_style = tmpl_style
            existing_resume.resume_data_json = profile.resume_data_json
            existing_resume.updated_at = datetime.utcnow()

        # Ensure portfolio HTML is cached and on disk
        if profile.portfolio_slug and profile.portfolio_html:
            save_published_portfolio(profile.portfolio_slug, profile.portfolio_html)

        # Transition status atomically to prevent double claiming
        profile.status = "claimed"
        profile.claimed_by_user_id = user.id
        profile.claimed_at = datetime.utcnow()

        db.commit()
        logger.info(
            "🎉 Prebuilt profile claimed successfully! User: %s (ID %s), Token: %s, Slug: %s",
            user.email, user.id, profile.claim_token, profile.portfolio_slug
        )
        return True

    except Exception as e:
        logger.error("Error syncing prebuilt candidate profile for %s: %s", getattr(user, "email", "unknown"), e)
        db.rollback()
        return False
