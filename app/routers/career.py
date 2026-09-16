import os
import json
import datetime
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, WebSocket
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import User, UserJobApplication
from app.schemas import (
    JobSearchRequest, JobSearchResponse,
    ApplicationKitRequest, ApplicationKitResponse,
    ChatCopilotRequest, ChatCopilotResponse,
    MockInterviewStartRequest, MockInterviewStartResponse,
    EvaluateAnswerRequest, AnswerEvaluationResponse,
    FinalInterviewReportRequest, FinalInterviewReportResponse,
    ConferenceTurnRequest, ConferenceTurnResponse,
    ConferenceDebriefRequest, ConferenceDebriefResponse,
    ConferenceTTSRequest,
    TrackedJobCreate, TrackedJobUpdate, TrackedJobResponse
)
from app.auth import (
    get_current_user, get_optional_user,
    check_copilot_kit_quota, check_chat_copilot_quota,
    check_voice_interview_quota, check_conference_quota,
    check_job_tracker_quota
)
from app.ai_engine import (
    search_live_jobs, generate_application_kit, chat_with_career_copilot,
    generate_mock_interview_questions, evaluate_mock_interview_answer,
    generate_interview_final_report, process_conference_conversation_turn,
    generate_conference_debrief
)
from app.tts_engine import synthesize_speech_audio
from app.conference_live_ws import handle_conference_live_websocket

router = APIRouter(tags=["Career, Jobs & AI Copilot"])

MAX_FREE_CONFERENCE_TURNS = 5
CONFERENCE_SESSION_TURNS: Dict[str, int] = defaultdict(int)


@router.post("/api/jobs/search", response_model=JobSearchResponse)
async def search_jobs_endpoint(
    payload: JobSearchRequest,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Real-time Job Hunter & Aggregator.
    Searches active remote & global tech job vacancies with direct LinkedIn Easy Apply URLs.
    Free tier / Guest: capped at 4 vacancies. Pro / Elite: unlimited full search results.
    """
    try:
        user_tier = (current_user.plan_tier or "free").lower() if current_user else "free"
        effective_limit = payload.limit or 8
        if user_tier == "free" and effective_limit > 4:
            effective_limit = 4

        return search_live_jobs(
            keywords=payload.keywords,
            location=payload.location or "Remote",
            work_mode=payload.work_mode or "all",
            experience_level=payload.experience_level or "all",
            limit=effective_limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job search failed: {str(e)}")


@router.post("/api/jobs/application-kit", response_model=ApplicationKitResponse)
async def create_application_kit_endpoint(
    payload: ApplicationKitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate instant tailored screening question answers, elevator pitch, and salary script
    for 1-click job application auto-filling.
    Guarded by check_copilot_kit_quota: Free users get 1 kit/day trial; Pro/Elite get unlimited.
    Requires authenticated user account.
    """
    check_copilot_kit_quota(current_user, db)
    try:
        return generate_application_kit(
            job_title=payload.job_title,
            company_name=payload.company_name,
            job_description=payload.job_description,
            work_mode=payload.work_mode,
            salary_range=payload.salary_range,
            resume_data=payload.resume_data
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate application kit: {str(e)}")


@router.post("/api/chat/copilot", response_model=ChatCopilotResponse)
async def chat_copilot_endpoint(
    payload: ChatCopilotRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    AI Career Copilot & Technical Interview Simulator.
    Provides real-time, context-aware resume critique, interview roleplay, cold outreach, and salary advice.
    Free users: 3 messages per day. Pro / Elite: Unlimited 24/7 coaching.
    Requires authenticated user account.
    """
    is_allowed, remaining, msg = check_chat_copilot_quota(current_user, db)
    if not is_allowed:
        return ChatCopilotResponse(
            reply="🔒 **Daily Free Limit Reached**\n\nYou have reached your **3 free Career Copilot messages** for today. Upgrade to **Pro Career ($9/mo)** or **Executive Elite** for unlimited 24/7 technical mock interviews, resume bullet rewrites, and cold recruiter outreach scripts!",
            suggested_prompts=["Upgrade to Pro ($9/mo)", "View Subscription Plans"],
            action_trigger={"type": "upgrade_modal", "plan": "pro"}
        )

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        return chat_with_career_copilot(
            messages=payload.messages,
            resume_context=payload.resume_context,
            target_job_title=payload.target_job_title,
            company_name=payload.company_name,
            api_key=api_key
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Career Copilot error: {str(e)}")


@router.post("/api/interview/start", response_model=MockInterviewStartResponse)
async def start_mock_interview_endpoint(
    payload: MockInterviewStartRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Initiates an interactive AI Voice Mock Interview session.
    Enforces daily practice session quotas for Free users (1 session/day, max 3 questions).
    Pro/Elite users receive unlimited full-length sessions with custom questions.
    Requires authenticated user account.
    """
    is_allowed, remaining, msg = check_voice_interview_quota(current_user, db)
    if not is_allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "quota_exceeded",
                "message": msg,
                "upgrade_required": True,
                "required_tier": "pro"
            }
        )

    tier = (current_user.plan_tier if current_user else "free").lower()
    q_count = payload.question_count if tier in ["pro", "elite"] else min(3, payload.question_count)

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        res = generate_mock_interview_questions(
            target_role=payload.target_role,
            target_company=payload.target_company,
            interview_type=payload.interview_type,
            difficulty=payload.difficulty,
            question_count=q_count,
            resume_context=payload.resume_context,
            api_key=api_key
        )
        if isinstance(res, MockInterviewStartResponse):
            return res
        return MockInterviewStartResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start mock interview: {str(e)}")


@router.post("/api/interview/evaluate-answer", response_model=AnswerEvaluationResponse)
async def evaluate_interview_answer_endpoint(
    payload: EvaluateAnswerRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Real-time spoken response evaluator.
    Analyzes candidate's transcribed answer for STAR adherence, filler words,
    speaking pace (WPM), technical strengths, and an exemplary model response.
    Requires authenticated user account.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        res = evaluate_mock_interview_answer(
            question_text=payload.question_text,
            candidate_answer=payload.candidate_answer_transcript,
            duration_seconds=payload.duration_seconds,
            target_role=payload.target_role,
            interview_type=payload.interview_type,
            api_key=api_key
        )
        res["question_id"] = payload.question_id
        return AnswerEvaluationResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate answer: {str(e)}")


@router.post("/api/interview/final-report", response_model=FinalInterviewReportResponse)
async def final_interview_report_endpoint(
    payload: FinalInterviewReportRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generates an executive-grade Candidate Interview Readiness Dossier and hiring verdict
    synthesizing performance across all completed questions.
    Requires authenticated user account.
    """
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        eval_dicts = [e.dict() for e in payload.evaluations]
        res = generate_interview_final_report(
            target_role=payload.target_role,
            interview_type=payload.interview_type,
            evaluations=eval_dicts,
            api_key=api_key
        )
        res["session_id"] = payload.session_id
        return FinalInterviewReportResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compile interview report: {str(e)}")


@router.post("/api/conference/turn", response_model=ConferenceTurnResponse)
async def conference_turn_endpoint(
    payload: ConferenceTurnRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Two-way real-time conversational conference turn with live mistake detection ("Waradi Kiyala Denna").
    Analyzes candidate's spoken speech, flags technical vagueness, pacing, filler words,
    and returns realistic spoken responses from the AI Interviewer avatar.
    Guarded by check_conference_quota: requires authenticated user.
    Security: Enforces turn limit (max 5 turns) on Free tier to protect Gemini API quota.
    """
    tier = (current_user.plan_tier or "free").lower()
    session_turns = CONFERENCE_SESSION_TURNS[payload.session_id]

    if tier == "free":
        if session_turns >= MAX_FREE_CONFERENCE_TURNS:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "free_turn_limit_reached",
                    "message": f"Free Starter practice session is limited to {MAX_FREE_CONFERENCE_TURNS} conversational turns. Please complete your session with 'End & Debrief' or upgrade to Pro ($9/mo) for unlimited live practice!",
                    "upgrade_required": True,
                    "required_tier": "pro"
                }
            )

    is_allowed, remaining, msg = check_conference_quota(current_user, db)
    if not is_allowed and session_turns == 0:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "quota_exceeded",
                "message": msg,
                "upgrade_required": True,
                "required_tier": "pro"
            }
        )

    # Consume daily session quota upon starting first turn
    if tier == "free" and session_turns == 0 and hasattr(current_user, "daily_interview_count"):
        if (current_user.daily_interview_count or 0) < 1:
            current_user.daily_interview_count = 1
            db.commit()
            db.refresh(current_user)

    CONFERENCE_SESSION_TURNS[payload.session_id] = session_turns + 1

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        res = process_conference_conversation_turn(
            session_id=payload.session_id,
            candidate_transcript=payload.candidate_transcript,
            conversation_history=payload.conversation_history,
            target_role=payload.target_role,
            target_company=payload.target_company,
            speaking_duration_seconds=payload.speaking_duration_seconds,
            api_key=api_key
        )
        return ConferenceTurnResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conference turn failed: {str(e)}")


@router.post("/api/conference/debrief", response_model=ConferenceDebriefResponse)
async def conference_debrief_endpoint(
    payload: ConferenceDebriefRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Compiles executive post-conference meeting debrief with full scorecard of mistakes corrected.
    Requires authenticated user account.
    """
    try:
        tier = (current_user.plan_tier or "free").lower()
        if tier == "free" and hasattr(current_user, "daily_interview_count"):
            if (current_user.daily_interview_count or 0) < 1:
                current_user.daily_interview_count = 1
                db.commit()
                db.refresh(current_user)

        api_key = os.getenv("GEMINI_API_KEY")
        res = generate_conference_debrief(
            session_id=payload.session_id,
            target_role=payload.target_role,
            target_company=payload.target_company,
            turns_history=payload.turns_history,
            all_mistakes=payload.all_mistakes,
            api_key=api_key
        )
        return ConferenceDebriefResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conference debrief failed: {str(e)}")


@router.post("/api/conference/tts")
async def conference_tts_post(payload: ConferenceTTSRequest):
    """
    Direct Server-Side Neural Voice Engine.
    Synthesizes studio-quality natural human MP3 audio for AI Interviewer Alex.
    Uses Edge-TTS with instant Google TTS fallback. 100% Free, zero token cost.
    """
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    try:
        audio_bytes, source = await synthesize_speech_audio(text, payload.voice)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=86400",
                "X-TTS-Engine": source,
                "Content-Disposition": "inline; filename=alex_speech.mp3"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")


@router.get("/api/conference/tts")
async def conference_tts_get(
    text: str = Query(..., min_length=1, max_length=3000),
    voice: Optional[str] = Query("en-US-ChristopherNeural")
):
    """
    Direct Server-Side Neural Voice Engine (GET endpoint for direct HTML5 audio playback).
    """
    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    try:
        audio_bytes, source = await synthesize_speech_audio(clean_text, voice)
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Cache-Control": "public, max-age=86400",
                "X-TTS-Engine": source,
                "Content-Disposition": "inline; filename=alex_speech.mp3"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS synthesis failed: {str(e)}")


@router.websocket("/ws/conference/live")
async def conference_live_ws_endpoint(websocket: WebSocket):
    """
    Real-Time Bidirectional Voice-to-Voice WebSocket Gateway.
    Powered by Google Gemini Live Multimodal API (gemini-2.5-flash-native-audio-latest).
    Streams raw 24kHz audio chunks directly to candidate's browser with sub-800ms latency.
    """
    role = websocket.query_params.get("role", "Senior Software Engineer")
    company = websocket.query_params.get("company", "Global Employer")
    voice = websocket.query_params.get("voice", "Puck")
    user_name = websocket.query_params.get("user_name")
    await handle_conference_live_websocket(
        websocket=websocket,
        role=role,
        company=company,
        voice=voice,
        user_name=user_name
    )


@router.get("/api/user/job-tracker", response_model=List[TrackedJobResponse])
async def get_user_tracked_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all tracked job applications for the logged-in candidate."""
    stmt = select(UserJobApplication).where(
        UserJobApplication.user_id == current_user.id
    ).order_by(UserJobApplication.updated_at.desc())
    jobs = db.scalars(stmt).all()
    
    out = []
    for j in jobs:
        kit_dict = None
        if j.application_kit_json:
            try:
                kit_dict = json.loads(j.application_kit_json)
            except Exception:
                pass
        out.append(
            TrackedJobResponse(
                id=j.id,
                job_title=j.job_title,
                company_name=j.company_name,
                location=j.location,
                work_mode=j.work_mode,
                salary_range=j.salary_range,
                match_score=j.match_score,
                job_url=j.job_url,
                status=j.status,
                applied_date=j.applied_date,
                notes=j.notes,
                has_application_kit=bool(kit_dict),
                application_kit=kit_dict,
                created_at=j.created_at.strftime("%b %d, %Y"),
                updated_at=j.updated_at.strftime("%b %d, %Y")
            )
        )
    return out


@router.post("/api/user/job-tracker", response_model=TrackedJobResponse)
async def create_user_tracked_job(
    payload: TrackedJobCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a job opportunity to candidate's Tracker. Free users: max 3 tracked jobs."""
    check_job_tracker_quota(current_user, db)
    new_job = UserJobApplication(
        user_id=current_user.id,
        job_title=payload.job_title,
        company_name=payload.company_name,
        location=payload.location,
        work_mode=payload.work_mode,
        salary_range=payload.salary_range,
        match_score=payload.match_score,
        job_url=payload.job_url,
        status=payload.status or "wishlist",
        notes=payload.notes,
        application_kit_json=payload.application_kit_json,
        applied_date=datetime.date.today().strftime("%b %d, %Y") if payload.status == "applied" else None
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    kit_dict = None
    if new_job.application_kit_json:
        try:
            kit_dict = json.loads(new_job.application_kit_json)
        except Exception:
            pass
            
    return TrackedJobResponse(
        id=new_job.id,
        job_title=new_job.job_title,
        company_name=new_job.company_name,
        location=new_job.location,
        work_mode=new_job.work_mode,
        salary_range=new_job.salary_range,
        match_score=new_job.match_score,
        job_url=new_job.job_url,
        status=new_job.status,
        applied_date=new_job.applied_date,
        notes=new_job.notes,
        has_application_kit=bool(kit_dict),
        application_kit=kit_dict,
        created_at=new_job.created_at.strftime("%b %d, %Y"),
        updated_at=new_job.updated_at.strftime("%b %d, %Y")
    )


@router.patch("/api/user/job-tracker/{job_id}", response_model=TrackedJobResponse)
async def update_user_tracked_job(
    job_id: int,
    payload: TrackedJobUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update job application status, applied date, or notes."""
    stmt = select(UserJobApplication).where(
        UserJobApplication.id == job_id,
        UserJobApplication.user_id == current_user.id
    )
    job = db.scalars(stmt).first()
    if not job:
        raise HTTPException(status_code=404, detail="Tracked job not found.")
        
    if payload.status is not None:
        job.status = payload.status
        if payload.status == "applied" and not job.applied_date:
            job.applied_date = datetime.date.today().strftime("%b %d, %Y")
    if payload.notes is not None:
        job.notes = payload.notes
    if payload.applied_date is not None:
        job.applied_date = payload.applied_date
    if payload.salary_range is not None:
        job.salary_range = payload.salary_range
    if payload.application_kit_json is not None:
        job.application_kit_json = payload.application_kit_json
        
    db.commit()
    db.refresh(job)
    
    kit_dict = None
    if job.application_kit_json:
        try:
            kit_dict = json.loads(job.application_kit_json)
        except Exception:
            pass
            
    return TrackedJobResponse(
        id=job.id,
        job_title=job.job_title,
        company_name=job.company_name,
        location=job.location,
        work_mode=job.work_mode,
        salary_range=job.salary_range,
        match_score=job.match_score,
        job_url=job.job_url,
        status=job.status,
        applied_date=job.applied_date,
        notes=job.notes,
        has_application_kit=bool(kit_dict),
        application_kit=kit_dict,
        created_at=job.created_at.strftime("%b %d, %Y"),
        updated_at=job.updated_at.strftime("%b %d, %Y")
    )


@router.delete("/api/user/job-tracker/{job_id}")
async def delete_user_tracked_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a job from candidate's tracker."""
    stmt = select(UserJobApplication).where(
        UserJobApplication.id == job_id,
        UserJobApplication.user_id == current_user.id
    )
    job = db.scalars(stmt).first()
    if not job:
        raise HTTPException(status_code=404, detail="Tracked job not found.")
        
    db.delete(job)
    db.commit()
    return {"success": True, "message": "Job removed from tracker."}
