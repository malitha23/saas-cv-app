import re
import json
import datetime
import asyncio
from typing import Optional, List
from fastapi import APIRouter, File, UploadFile, HTTPException, Response, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import User, UserResume
from app.sample_data import SAMPLE_RESUMES
from app.parser import parse_resume_file, extract_candidate_name
from app.ai_engine import generate_with_gemini
from app.pdf_generator import generate_resume_pdf, generate_cover_letter_pdf
from app.schemas import ParseResponse, TailorRequest, TailoredResume, SaveResumeRequest, SavedResumeListItem
from app.auth import (
    get_current_user, get_optional_user, check_daily_ai_quota,
    check_ats_pdf_quota, check_visual_pdf_quota, check_daily_cover_letter_quota,
    check_and_update_subscription, get_saas_setting
)

router = APIRouter(tags=["Resume & Cover Letter"])

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB ceiling


@router.get("/api/sample-data")
async def get_sample_data():
    """Return pre-built realistic sample resumes and job descriptions."""
    return SAMPLE_RESUMES


@router.post("/api/upload", response_model=ParseResponse)
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

        text, detected_sections = await asyncio.to_thread(parse_resume_file, filename, content)
        
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


@router.post("/api/tailor", response_model=TailoredResume)
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
        result = await asyncio.to_thread(
            generate_with_gemini,
            resume_text=payload.resume_text,
            job_description=payload.job_description,
            api_key=payload.api_key,
            job_title=payload.job_title,
            company_name=payload.company_name,
            role_archetype=payload.role_archetype or "auto",
            template_style=payload.template_style or "classic",
            cover_letter_tone=payload.cover_letter_tone or "professional"
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Optimization error: {str(e)}")


@router.post("/api/generate-pdf/resume")
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
        elif (not is_visual) and tier == "free":
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="Please sign in or create a free account to download your ATS resume PDF."
                )
            # Free users get 2 Lifetime ATS PDF downloads
            check_ats_pdf_quota(current_user, db)

    try:
        pdf_bytes = await asyncio.to_thread(generate_resume_pdf, resume)
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


@router.post("/api/generate-pdf/cover-letter")
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
        
        used_count = getattr(current_user, "lifetime_cover_letter_downloads_count", 1)
        apply_watermark = is_free and (used_count > 1)
        
        pdf_bytes = await asyncio.to_thread(generate_cover_letter_pdf, resume, is_free_watermarked=apply_watermark)
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
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Cover Letter Generation error: {str(e)}")


@router.get("/api/user/resumes", response_model=List[SavedResumeListItem])
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


@router.post("/api/user/resumes")
async def save_user_resume(
    req: SaveResumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save or update tailored resume data into MySQL for the logged-in user."""
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


@router.get("/api/user/resumes/{resume_id}")
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

    return {
        "resume_id": resume.id,
        "title": resume.title,
        "resume_data": json.loads(resume.resume_data_json)
    }


@router.delete("/api/user/resumes/{resume_id}")
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
