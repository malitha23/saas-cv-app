import os
import json
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models import User, PrebuiltCandidateProfile, BusinessCreditTransaction, OnlinePaymentOrder, UserResume
from app.auth import get_current_user
from app.schemas import (
    PrebuildProfileResponse,
    CandidatePrebuiltSummary,
    BusinessCreditPackOrderRequest,
    BusinessWalletResponse,
    BusinessTransactionItem
)
from app.services.business_service import (
    prebuild_candidate_profile,
    CREDIT_PACKS
)
from app.payhere import PayHereGateway
from app.email_service import (
    send_candidate_onboarding_invitation_email,
    send_candidate_suspension_email,
    send_candidate_reactivation_email
)

logger = logging.getLogger("dreemfolio.business_router")

router = APIRouter(prefix="/api/business", tags=["Business & Candidate Onboarding"])


@router.post("/prebuild", response_model=PrebuildProfileResponse)
async def api_prebuild_candidate(
    request: Request,
    candidate_email: str = Form(..., description="Candidate's email address"),
    target_role: Optional[str] = Form(None, description="Target job title or profession"),
    auto_send_email: bool = Form(False, description="Automatically dispatch onboarding invitation email"),
    file: UploadFile = File(..., description="Candidate resume PDF or Word file"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Magic Candidate Onboarding:
    Admin and Business users upload a candidate CV. AI extracts, formats, and structures
    the resume into an ATS profile and auto-publishes a live web portfolio.
    Issues a cryptographically secure, 1-click claim URL.
    Optionally dispatches instant VIP onboarding email with claim link.
    """
    file_bytes = await file.read()
    filename = file.filename or "resume.pdf"

    # Base URL resolution
    env_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    base_url = env_base if env_base else str(request.base_url).rstrip("/")

    return prebuild_candidate_profile(
        creator=current_user,
        candidate_email=candidate_email,
        target_role=target_role,
        file_bytes=file_bytes,
        filename=filename,
        db=db,
        base_url=base_url,
        auto_send_email=auto_send_email
    )


@router.get("/candidates", response_model=List[CandidatePrebuiltSummary])
async def list_onboarded_candidates(
    all_users: bool = Query(False, description="Admins can view all onboarded candidates"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List candidate profiles onboarded by the current business or admin.
    """
    is_admin = bool(getattr(current_user, "is_admin", False))
    acc_type = getattr(current_user, "account_type", "candidate")

    if not is_admin and acc_type != "business":
        raise HTTPException(
            status_code=403,
            detail="Access restricted: Candidate management is available only for Business accounts and Admins."
        )

    stmt = select(PrebuiltCandidateProfile)
    if not (is_admin and all_users):
        stmt = stmt.where(PrebuiltCandidateProfile.creator_id == current_user.id)

    stmt = stmt.order_by(desc(PrebuiltCandidateProfile.id))
    profiles = db.scalars(stmt).all()

    results: List[CandidatePrebuiltSummary] = []
    env_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    base_url = env_base if env_base else "https://www.dreemfolio.com"

    for p in profiles:
        linked_user = p.claimed_by
        if not linked_user and p.candidate_email:
            clean_email = p.candidate_email.strip().lower()
            linked_user = db.scalar(select(User).where(func.lower(User.email) == clean_email))

        has_account = bool(linked_user)
        is_user_active = bool(linked_user.is_active) if linked_user else (p.status != "blocked")
        claimed_user_name = (linked_user.full_name or linked_user.email) if linked_user else None

        creator_user_name = None
        if p.creator:
            creator_user_name = p.creator.company_name or p.creator.full_name or p.creator.email

        results.append(CandidatePrebuiltSummary(
            id=p.id,
            claim_token=p.claim_token,
            candidate_name=p.candidate_name,
            candidate_email=p.candidate_email,
            target_role=p.target_role,
            portfolio_slug=p.portfolio_slug,
            portfolio_url=f"{base_url}/p/{p.portfolio_slug}" if p.portfolio_slug else None,
            claim_url=f"{base_url}/claim/{p.claim_token}",
            status=p.status,
            has_account=has_account,
            is_user_active=is_user_active,
            created_at=p.created_at.strftime("%b %d, %Y %I:%M %p"),
            claimed_at=p.claimed_at.strftime("%b %d, %Y %I:%M %p") if p.claimed_at else None,
            claimed_by_name=claimed_user_name,
            creator_name=creator_user_name
        ))

    return results


@router.post("/candidates/{candidate_id}/send-email")
async def api_send_candidate_onboarding_email(
    candidate_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    1-Click Candidate Outreach:
    Dispatches a branded, high-converting invitation email with prebuilt portfolio and claim link.
    """
    is_admin = bool(getattr(current_user, "is_admin", False))
    acc_type = getattr(current_user, "account_type", "candidate")

    profile = db.get(PrebuiltCandidateProfile, candidate_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate prebuilt profile not found.")

    if not is_admin and profile.creator_id != current_user.id and acc_type != "business":
        raise HTTPException(status_code=403, detail="You do not have permission to email this candidate.")

    env_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    base_url = env_base if env_base else str(request.base_url).rstrip("/")
    claim_url = f"{base_url}/claim/{profile.claim_token}"
    portfolio_url = f"{base_url}/p/{profile.portfolio_slug}" if profile.portfolio_slug else None

    creator_name = (profile.creator.company_name or profile.creator.full_name) if profile.creator else "DreemFolio AI Talent Team"
    creator_email = profile.creator.email if profile.creator else None

    success = send_candidate_onboarding_invitation_email(
        to_email=profile.candidate_email,
        candidate_name=profile.candidate_name,
        target_role=profile.target_role,
        portfolio_url=portfolio_url,
        claim_url=claim_url,
        creator_name=creator_name,
        creator_email=creator_email,
        base_url=base_url,
        enqueue_on_fail=True
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to dispatch invitation email via SMTP. Please check email configuration.")

    return {
        "success": True,
        "message": f"Invitation email successfully dispatched to {profile.candidate_email}!"
    }


@router.post("/candidates/{candidate_id}/toggle-block")
async def api_toggle_block_candidate(
    candidate_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Block or Re-activate a candidate profile and their linked user login account.
    Automatically sends an informative notification email to the candidate detailing
    disabled or restored services.
    """
    is_admin = bool(getattr(current_user, "is_admin", False))
    acc_type = getattr(current_user, "account_type", "candidate")

    if not is_admin and acc_type != "business":
        raise HTTPException(
            status_code=403,
            detail="Access restricted: Candidate management is available only for Business accounts and Admins."
        )

    profile = db.get(PrebuiltCandidateProfile, candidate_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")

    if not is_admin and profile.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to modify this candidate.")

    # Find linked user account if exists
    linked_user = profile.claimed_by
    if not linked_user and profile.candidate_email:
        clean_email = profile.candidate_email.strip().lower()
        linked_user = db.scalar(select(User).where(func.lower(User.email) == clean_email))

    if linked_user and linked_user.is_admin:
        raise HTTPException(status_code=403, detail="Cannot block an administrator account.")

    env_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    base_url = env_base if env_base else str(request.base_url).rstrip("/")

    # If currently blocked -> Reactivate
    if profile.status == "blocked" or (linked_user and not linked_user.is_active):
        profile.status = "claimed" if linked_user else "pending"
        if linked_user:
            linked_user.is_active = True
        action = "reactivated"
        msg = f"Candidate {profile.candidate_name} ({profile.candidate_email}) has been re-activated successfully. Logins restored."

        # Dispatch automated reactivation notification email
        if profile.candidate_email:
            try:
                action_url = f"{base_url}/claim/{profile.claim_token}" if (profile.status == "pending" and profile.claim_token) else f"{base_url}/app"
                sent = send_candidate_reactivation_email(
                    to_email=profile.candidate_email,
                    candidate_name=profile.candidate_name,
                    portfolio_slug=profile.portfolio_slug,
                    action_url=action_url,
                    base_url=base_url
                )
                if sent:
                    msg += " Automated reactivation notification email sent."
            except Exception as e:
                logger.error(f"Failed to dispatch reactivation email to {profile.candidate_email}: {e}")
    else:
        # Currently active -> Block
        profile.status = "blocked"
        if linked_user:
            linked_user.is_active = False
        action = "blocked"
        msg = f"Candidate {profile.candidate_name} ({profile.candidate_email}) has been blocked. Account logins, live portfolio, and claim link are now suspended."
        # Evict live portfolio cache immediately
        from app.state import PUBLISHED_PORTFOLIOS
        if profile.portfolio_slug:
            PUBLISHED_PORTFOLIOS.pop(profile.portfolio_slug, None)

        # Dispatch automated suspension notification email
        if profile.candidate_email:
            try:
                sent = send_candidate_suspension_email(
                    to_email=profile.candidate_email,
                    candidate_name=profile.candidate_name,
                    portfolio_slug=profile.portfolio_slug,
                    base_url=base_url
                )
                if sent:
                    msg += " Automated suspension notification email sent."
            except Exception as e:
                logger.error(f"Failed to dispatch suspension email to {profile.candidate_email}: {e}")

    db.commit()
    db.refresh(profile)
    if linked_user:
        db.refresh(linked_user)

    return {
        "success": True,
        "action": action,
        "status": profile.status,
        "is_user_active": linked_user.is_active if linked_user else (profile.status != "blocked"),
        "message": msg
    }


@router.delete("/candidates/{candidate_id}")
async def api_delete_candidate_profile(
    candidate_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Permanently delete a candidate prebuilt profile record.
    """
    is_admin = bool(getattr(current_user, "is_admin", False))
    acc_type = getattr(current_user, "account_type", "candidate")

    if not is_admin and acc_type != "business":
        raise HTTPException(
            status_code=403,
            detail="Access restricted: Candidate management is available only for Business accounts and Admins."
        )

    profile = db.get(PrebuiltCandidateProfile, candidate_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")

    if not is_admin and profile.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to delete this candidate profile.")

    cand_name = profile.candidate_name
    from app.state import PUBLISHED_PORTFOLIOS, PORTFOLIO_STORAGE_DIR
    if profile.portfolio_slug:
        PUBLISHED_PORTFOLIOS.pop(profile.portfolio_slug, None)
        file_path = os.path.join(PORTFOLIO_STORAGE_DIR, f"{profile.portfolio_slug}.html")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

    db.delete(profile)
    db.commit()

    return {
        "success": True,
        "message": f"Candidate profile #{candidate_id} ({cand_name}) has been permanently deleted."
    }


@router.get("/candidates/{candidate_id}/resume")
async def get_candidate_profile_resume(
    candidate_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Fetch full candidate prebuilt profile resume data for editing by Creator or Admin.
    Supports lookup by integer ID or cryptographically secure 64-char claim_token.
    """
    is_admin = bool(getattr(current_user, "is_admin", False))

    profile = None
    if candidate_id.isdigit():
        profile = db.get(PrebuiltCandidateProfile, int(candidate_id))
    if not profile:
        profile = db.scalar(
            select(PrebuiltCandidateProfile).where(PrebuiltCandidateProfile.claim_token == candidate_id)
        )

    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")

    # Strict Zero-Trust Authorization: Only Admin or the exact Creator can view/edit
    if not is_admin and profile.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to view or edit this candidate's resume.")

    env_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    base_url = env_base if env_base else str(request.base_url).rstrip("/")
    portfolio_url = f"{base_url}/p/{profile.portfolio_slug}" if profile.portfolio_slug else None

    resume_data = {}
    if profile.resume_data_json:
        try:
            resume_data = json.loads(profile.resume_data_json)
        except Exception:
            resume_data = {}

    # If linked to a claimed user account, read their latest user_resumes entry to get candidate's own edits
    linked_user_id = profile.claimed_by_user_id
    if not linked_user_id and profile.candidate_email:
        clean_email = profile.candidate_email.strip().lower()
        matched_user = db.scalar(select(User).where(func.lower(User.email) == clean_email))
        if matched_user:
            linked_user_id = matched_user.id

    if linked_user_id:
        user_res = db.scalar(
            select(UserResume)
            .where(UserResume.user_id == linked_user_id)
            .order_by(UserResume.updated_at.desc())
        )
        if user_res and user_res.resume_data_json:
            try:
                user_res_data = json.loads(user_res.resume_data_json)
                if user_res.template_style and not user_res_data.get("template_style"):
                    user_res_data["template_style"] = user_res.template_style
                resume_data = user_res_data
            except Exception:
                pass

    if profile.portfolio_slug and isinstance(resume_data, dict):
        if not resume_data.get("portfolio_slug"):
            resume_data["portfolio_slug"] = profile.portfolio_slug
        if not resume_data.get("portfolio_url"):
            resume_data["portfolio_url"] = portfolio_url

    return {
        "success": True,
        "id": profile.id,
        "claim_token": profile.claim_token,
        "candidate_name": profile.candidate_name,
        "candidate_email": profile.candidate_email,
        "target_role": profile.target_role,
        "portfolio_slug": profile.portfolio_slug,
        "portfolio_url": portfolio_url,
        "claim_url": f"{base_url}/claim/{profile.claim_token}",
        "status": profile.status,
        "created_at": profile.created_at.strftime("%b %d, %Y %I:%M %p"),
        "resume_data": resume_data
    }


@router.put("/candidates/{candidate_id}/resume")
async def update_candidate_profile_resume(
    candidate_id: str,
    payload: Dict[str, Any],
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update candidate resume data and re-publish updated live portfolio.
    Accessible ONLY to Admin and the exact Business creator of the profile.
    Supports lookup by integer ID or cryptographically secure 64-char claim_token.
    """
    is_admin = bool(getattr(current_user, "is_admin", False))

    profile = None
    if candidate_id.isdigit():
        profile = db.get(PrebuiltCandidateProfile, int(candidate_id))
    if not profile:
        profile = db.scalar(
            select(PrebuiltCandidateProfile).where(PrebuiltCandidateProfile.claim_token == candidate_id)
        )

    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")

    # Strict Zero-Trust Authorization: Only Admin or the exact Creator can update
    if not is_admin and profile.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to edit this candidate's resume.")

    env_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    base_url = env_base if env_base else str(request.base_url).rstrip("/")
    portfolio_url = f"{base_url}/p/{profile.portfolio_slug}" if profile.portfolio_slug else None

    # Extract resume_data dictionary from payload
    resume_data = payload.get("resume_data") if "resume_data" in payload else payload
    if not isinstance(resume_data, dict):
        raise HTTPException(status_code=400, detail="Invalid resume data format.")

    # Ensure personal_info structure is present
    personal_info = resume_data.get("personal_info") or {}
    new_name = payload.get("candidate_name") or personal_info.get("full_name") or profile.candidate_name
    new_email = payload.get("candidate_email") or personal_info.get("email") or profile.candidate_email
    new_role = payload.get("target_role") or resume_data.get("target_job_title") or profile.target_role

    if "personal_info" not in resume_data or not isinstance(resume_data["personal_info"], dict):
        resume_data["personal_info"] = {}
    resume_data["personal_info"]["full_name"] = new_name
    resume_data["personal_info"]["email"] = new_email
    resume_data["target_job_title"] = new_role

    profile.candidate_name = new_name
    profile.candidate_email = new_email.strip().lower()
    profile.target_role = new_role
    if profile.portfolio_slug and isinstance(resume_data, dict):
        resume_data.setdefault("portfolio_slug", profile.portfolio_slug)
        if portfolio_url and not resume_data.get("portfolio_url"):
            resume_data["portfolio_url"] = portfolio_url
    profile.resume_data_json = json.dumps(resume_data, ensure_ascii=False)

    # Re-compile live web portfolio HTML and save to disk cache
    try:
        from app.portfolio_templates import generate_portfolio_html
        from app.state import save_published_portfolio
        from app.schemas import TailoredResume

        if "role_archetype" not in resume_data or not resume_data["role_archetype"]:
            resume_data["role_archetype"] = "auto"
        if "template_style" not in resume_data or not resume_data["template_style"]:
            resume_data["template_style"] = "classic"
        if "tailored_bullets" not in resume_data or not isinstance(resume_data["tailored_bullets"], list):
            resume_data["tailored_bullets"] = []

        tailored_obj = TailoredResume(**resume_data)
        updated_portfolio_html = generate_portfolio_html(
            resume=tailored_obj,
            theme=resume_data.get("portfolio_theme") or "neon_dark",
            slug=profile.portfolio_slug or ""
        )
        profile.portfolio_html = updated_portfolio_html
        if profile.portfolio_slug:
            save_published_portfolio(profile.portfolio_slug, updated_portfolio_html)
    except Exception as render_err:
        logger.warning("Could not re-generate portfolio HTML on candidate resume update: %s", render_err)

    # Sync linked candidate user_resumes entry so claimed user sees the exact edits in their dashboard
    target_user_id = profile.claimed_by_user_id
    if not target_user_id and profile.candidate_email:
        clean_cand_email = profile.candidate_email.strip().lower()
        matched_user = db.scalar(select(User).where(func.lower(User.email) == clean_cand_email))
        if matched_user:
            target_user_id = matched_user.id
            if profile.status == "pending":
                profile.claimed_by_user_id = matched_user.id

    if target_user_id:
        try:
            claimed_user_resume = db.scalar(
                select(UserResume).where(UserResume.user_id == target_user_id)
            )
            template_style_val = resume_data.get("template_style") or "classic"
            if claimed_user_resume:
                claimed_user_resume.title = f"{new_role or 'Professional'} ATS Resume"
                claimed_user_resume.target_role = new_role
                claimed_user_resume.template_style = template_style_val
                claimed_user_resume.resume_data_json = profile.resume_data_json
                claimed_user_resume.updated_at = datetime.utcnow()
            else:
                new_user_resume = UserResume(
                    user_id=target_user_id,
                    title=f"{new_role or 'Professional'} ATS Resume",
                    target_role=new_role,
                    template_style=template_style_val,
                    resume_data_json=profile.resume_data_json
                )
                db.add(new_user_resume)
        except Exception as sync_err:
            logger.warning("Could not sync candidate UserResume: %s", sync_err)

    db.commit()
    db.refresh(profile)

    env_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    base_url = env_base if env_base else str(request.base_url).rstrip("/")
    portfolio_url = f"{base_url}/p/{profile.portfolio_slug}" if profile.portfolio_slug else None

    return {
        "success": True,
        "message": f"Candidate CV and live portfolio successfully updated for {profile.candidate_name}!",
        "candidate_id": profile.id,
        "candidate_name": profile.candidate_name,
        "candidate_email": profile.candidate_email,
        "target_role": profile.target_role,
        "portfolio_url": portfolio_url
    }


def _reconstruct_text_from_resume_data(data: Dict[str, Any]) -> str:
    """Reconstruct structured text from stored resume JSON for AI re-generation."""
    parts = []
    pinfo = data.get("personal_info") or {}
    name = pinfo.get("full_name") or ""
    email = pinfo.get("email") or ""
    phone = pinfo.get("phone") or ""
    loc = pinfo.get("location") or ""
    title = pinfo.get("target_job_title") or data.get("target_job_title") or ""
    parts.append(f"{name}\n{email} | {phone} | {loc}\nTarget Title: {title}\n")

    summary = data.get("professional_summary") or ""
    if summary:
        parts.append(f"PROFESSIONAL SUMMARY\n{summary}\n")

    skills = data.get("skill_categories") or []
    if skills:
        parts.append("SKILLS")
        for cat in skills:
            if isinstance(cat, dict):
                cname = cat.get("name") or "Key Skills"
                cskills = cat.get("skills", [])
                if isinstance(cskills, list) and cskills:
                    parts.append(f"{cname}: {', '.join(str(s) for s in cskills)}")
        parts.append("")

    experiences = data.get("work_experience") or []
    if experiences:
        parts.append("WORK EXPERIENCE")
        for exp in experiences:
            if isinstance(exp, dict):
                parts.append(f"{exp.get('title', '')} at {exp.get('company', '')} ({exp.get('start_date', '')} - {exp.get('end_date', '')})")
                for b in exp.get("responsibilities", []):
                    parts.append(f"- {b}")
        parts.append("")

    educations = data.get("education") or []
    if educations:
        parts.append("EDUCATION")
        for edu in educations:
            if isinstance(edu, dict):
                parts.append(f"{edu.get('degree', '')} - {edu.get('institution', '')} ({edu.get('year', '')})")
        parts.append("")

    certifications = data.get("certifications") or []
    if certifications:
        parts.append("=== CERTIFICATIONS & VERIFIED CREDENTIALS ===")
        for c in certifications:
            if isinstance(c, dict):
                parts.append(f"- {c.get('name', '')} | Issuer: {c.get('issuer', '')} | Year: {c.get('year', '')} | URL: {c.get('url', '')}")
        parts.append("")

    projects = data.get("projects") or []
    if projects:
        parts.append("PROJECTS")
        for p in projects:
            if isinstance(p, dict):
                techs = p.get('technologies', [])
                tech_str = ', '.join(techs) if isinstance(techs, list) else str(techs)
                parts.append(f"{p.get('name', '')} ({tech_str})")
                for b in p.get("description_bullets", []):
                    parts.append(f"- {b}")
        parts.append("")

    return "\n".join(parts)


@router.post("/candidates/{candidate_id}/regenerate")
async def api_regenerate_candidate_profile(
    candidate_id: str,
    request: Request,
    target_role: Optional[str] = Form(None),
    auto_send_email: bool = Form(False),
    file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Secure Candidate Re-Generation:
    Re-processes and re-generates an existing candidate profile with AI without deleting or breaking
    their existing claim_token, live portfolio URL (portfolio_slug), or account links.
    Optionally accepts a new CV file (supporting multi-page PDFs with scanned certificates via Vision OCR)
    and an updated target role.
    """
    is_admin = bool(getattr(current_user, "is_admin", False))
    acc_type = getattr(current_user, "account_type", "candidate")

    if not is_admin and acc_type != "business":
        raise HTTPException(
            status_code=403,
            detail="Access restricted: Candidate management is available only for Business accounts and Admins."
        )

    profile = None
    if candidate_id.isdigit():
        profile = db.get(PrebuiltCandidateProfile, int(candidate_id))
    if not profile:
        profile = db.scalar(
            select(PrebuiltCandidateProfile).where(PrebuiltCandidateProfile.claim_token == candidate_id)
        )

    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")

    # Strict Zero-Trust Authorization: Only Admin or the exact Creator can re-generate
    if not is_admin and profile.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have permission to re-generate this candidate.")

    from app.services.business_service import validate_resume_file
    from app.parser import parse_resume_file
    from app.ai_engine import generate_with_gemini
    from app.portfolio_templates import generate_portfolio_html
    from app.state import save_published_portfolio, PUBLISHED_PORTFOLIOS
    from app.schemas import TailoredResume

    # 1. Resolve raw text: From new file or from existing stored resume data
    if file and file.filename:
        file_bytes = await file.read()
        if len(file_bytes) > 0:
            validate_resume_file(file_bytes, file.filename)
            raw_text, _ = parse_resume_file(file.filename, file_bytes)
        else:
            raw_text = ""
    else:
        raw_text = ""

    if not raw_text or len(raw_text.strip()) < 40:
        # Reconstruct text from existing profile JSON
        existing_data = {}
        if profile.resume_data_json:
            try:
                existing_data = json.loads(profile.resume_data_json)
            except Exception:
                pass
        if not existing_data:
            raise HTTPException(
                status_code=400,
                detail="No resume text or valid existing data available to re-generate. Please upload a CV file."
            )
        raw_text = _reconstruct_text_from_resume_data(existing_data)

    if not raw_text or len(raw_text.strip()) < 40:
        raise HTTPException(
            status_code=400,
            detail="Could not extract readable resume text to re-generate candidate profile."
        )

    # 2. AI Structuring and Tailoring
    role_str = (target_role or "").strip() or (profile.target_role or "").strip()
    # Avoid hardcoded fallback to "Software Engineer"
    if role_str.lower() in ["software engineer", "professional"] and not (target_role and target_role.strip()):
        role_str = ""

    comp_str = (profile.creator.company_name or profile.creator.full_name) if profile.creator else "Leading Organization"
    job_desc = f"Professional job placement profile tailored for {role_str} position." if role_str else "Professional job placement profile tailored for the candidate's verified career track, trade expertise, and credentials."

    try:
        tailored_resume = generate_with_gemini(
            resume_text=raw_text,
            job_description=job_desc,
            job_title=role_str if role_str else None,
            company_name=comp_str,
            role_archetype="auto",
            template_style="classic"
        )
    except Exception as e:
        logger.error("[Candidate Re-generate] AI generation error: %s", e)
        raise HTTPException(
            status_code=500,
            detail=f"AI Resume Processing encountered an issue: {str(e)}"
        )

    # 3. Preserve critical candidate identity and links
    extracted_name = tailored_resume.personal_info.full_name or ""
    if extracted_name and extracted_name not in ["Candidate", "Candidate Name"]:
        profile.candidate_name = extracted_name
    tailored_resume.personal_info.full_name = profile.candidate_name

    extracted_email = (tailored_resume.personal_info.email or "").strip().lower()
    clean_email = profile.candidate_email.strip().lower()
    # Strictly preserve the authentic extracted email from the candidate's CV
    if extracted_email and "@" in extracted_email and "candidate.com" not in extracted_email:
        tailored_resume.personal_info.email = extracted_email
        profile.candidate_email = extracted_email
    elif clean_email:
        tailored_resume.personal_info.email = clean_email

    final_role = role_str or getattr(tailored_resume, "target_job_title", "") or profile.target_role or "Professional"
    profile.target_role = final_role
    tailored_resume.target_job_title = final_role

    # 4. Save updated resume JSON
    profile.resume_data_json = tailored_resume.model_dump_json()

    # 5. Re-compile live web portfolio HTML while strictly PRESERVING the existing slug!
    active_slug = profile.portfolio_slug or f"portfolio_{profile.claim_token[:12]}"
    profile.portfolio_slug = active_slug

    try:
        portfolio_html = generate_portfolio_html(
            resume=tailored_resume,
            theme="neon_dark",
            slug=active_slug
        )
        profile.portfolio_html = portfolio_html
        save_published_portfolio(active_slug, portfolio_html)
    except Exception as render_err:
        logger.warning("[Candidate Re-generate] Could not re-compile portfolio HTML: %s", render_err)

    # 6. Synchronize claimed candidate UserResume if candidate already claimed account
    target_user_id = profile.claimed_by_user_id
    if not target_user_id and clean_email:
        matched_user = db.scalar(select(User).where(func.lower(User.email) == clean_email))
        if matched_user:
            target_user_id = matched_user.id
            if profile.status == "pending":
                profile.claimed_by_user_id = matched_user.id

    if target_user_id:
        try:
            claimed_user_resume = db.scalar(
                select(UserResume).where(UserResume.user_id == target_user_id)
            )
            if claimed_user_resume:
                claimed_user_resume.title = f"{final_role} ATS Resume"
                claimed_user_resume.target_role = final_role
                claimed_user_resume.resume_data_json = profile.resume_data_json
                claimed_user_resume.updated_at = datetime.utcnow()
            else:
                new_user_resume = UserResume(
                    user_id=target_user_id,
                    title=f"{final_role} ATS Resume",
                    target_role=final_role,
                    template_style="classic",
                    resume_data_json=profile.resume_data_json
                )
                db.add(new_user_resume)
        except Exception as sync_err:
            logger.warning("[Candidate Re-generate] Could not sync candidate UserResume: %s", sync_err)

    db.commit()
    db.refresh(profile)

    # 7. Base URLs
    env_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    base_url = env_base if env_base else str(request.base_url).rstrip("/")
    claim_url = f"{base_url}/claim/{profile.claim_token}"
    portfolio_url = f"{base_url}/p/{profile.portfolio_slug}" if profile.portfolio_slug else None

    # 8. Optional Invitation Email dispatch
    if auto_send_email and profile.candidate_email:
        try:
            creator_name = (profile.creator.company_name or profile.creator.full_name) if profile.creator else "DreemFolio AI Talent Team"
            send_candidate_onboarding_invitation_email(
                to_email=profile.candidate_email,
                candidate_name=profile.candidate_name,
                target_role=profile.target_role,
                portfolio_url=portfolio_url,
                claim_url=claim_url,
                creator_name=creator_name,
                creator_email=profile.creator.email if profile.creator else None,
                base_url=base_url,
                enqueue_on_fail=True
            )
        except Exception as mail_err:
            logger.error("[Candidate Re-generate] Could not send invitation email: %s", mail_err)

    return {
        "success": True,
        "message": f"Candidate profile #{profile.id} ({profile.candidate_name}) successfully re-generated with AI!",
        "candidate_id": profile.id,
        "candidate_name": profile.candidate_name,
        "candidate_email": profile.candidate_email,
        "target_role": profile.target_role,
        "portfolio_url": portfolio_url,
        "claim_url": claim_url,
        "certifications_count": len(getattr(tailored_resume, "certifications", []))
    }


@router.get("/wallet", response_model=BusinessWalletResponse)
async def get_business_wallet(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve business credit balance, available top-up packs, and credit ledger.
    """
    is_admin = bool(getattr(current_user, "is_admin", False))
    acc_type = getattr(current_user, "account_type", "candidate")

    if not is_admin and acc_type != "business":
        raise HTTPException(
            status_code=403,
            detail="Business wallet is available for Business and Recruiter accounts."
        )

    # Fetch recent transactions
    txns = db.scalars(
        select(BusinessCreditTransaction)
        .where(BusinessCreditTransaction.user_id == current_user.id)
        .order_by(desc(BusinessCreditTransaction.id))
        .limit(50)
    ).all()

    txn_items = [
        BusinessTransactionItem(
            id=t.id,
            amount=t.amount,
            balance_after=t.balance_after,
            description=t.description,
            reference_id=t.reference_id,
            created_at=t.created_at.strftime("%b %d, %Y %I:%M %p")
        )
        for t in txns
    ]

    effective_credits = 999999 if is_admin else (getattr(current_user, "business_credits", 0) or 0)

    return BusinessWalletResponse(
        business_credits=effective_credits,
        account_type=acc_type,
        company_name=getattr(current_user, "company_name", None),
        packs=CREDIT_PACKS,
        recent_transactions=txn_items
    )


@router.post("/credits/buy")
async def buy_business_credits(
    req: BusinessCreditPackOrderRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiates a verified PayHere checkout session for purchasing prepaid B2B candidate onboarding credits.
    """
    credits_count = 0
    amount_lkr = 0.0

    if req.custom_credits and req.custom_credits >= 5:
        credits_count = int(req.custom_credits)
        # Dynamic bulk discount tiers:
        # 5 - 24 credits: Rs. 150/candidate
        # 25 - 99 credits: Rs. 120/candidate (20% Agency discount)
        # 100+ credits: Rs. 99/candidate (34% Enterprise bulk discount)
        if credits_count >= 100:
            rate_per_credit = 99.0
        elif credits_count >= 25:
            rate_per_credit = 120.0
        else:
            rate_per_credit = 150.0
        amount_lkr = round(credits_count * rate_per_credit, 2)
    else:
        matched_pack = next((p for p in CREDIT_PACKS if p["pack_id"] == req.pack_id), None)
        if not matched_pack:
            raise HTTPException(status_code=400, detail="Invalid credit pack or custom credits selected (minimum 5 credits).")
        credits_count = matched_pack["credits"]
        amount_lkr = matched_pack["price_lkr"]

    plan_tier_key = f"credits_{credits_count}"

    order_id = f"ORD-BIZ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6].upper()}"

    env_base = os.getenv("APP_BASE_URL", "").strip().rstrip("/")
    base_url = env_base if env_base else str(request.base_url).rstrip("/")

    # Prepare signed PayHere payload
    payload = PayHereGateway.prepare_checkout_payload(
        order_id=order_id,
        plan_tier=plan_tier_key,
        user_email=current_user.email,
        user_name=current_user.full_name or "Business User",
        user_id=current_user.id,
        base_url=base_url,
        currency="LKR",
        billing_cycle="pack",
        amount_override=amount_lkr,
        db=db
    )

    # Save initiated order
    order = OnlinePaymentOrder(
        order_id=order_id,
        user_id=current_user.id,
        target_plan=plan_tier_key,
        billing_cycle="pack",
        amount=amount_lkr,
        currency="LKR",
        gateway="payhere",
        status="initiated"
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "success": True,
        "order_id": order_id,
        "amount": amount_lkr,
        "credits": credits_count,
        "currency": "LKR",
        "action_url": payload["action_url"],
        "params": payload["params"]
    }
