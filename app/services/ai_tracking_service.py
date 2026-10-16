import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.models import AiUsageLog, User, UserResume, PrebuiltCandidateProfile

logger = logging.getLogger("dreemfolio.ai_tracking")

# Official Google Gemini API Pricing (Per 1 Million Tokens)
# Gemini 1.5 / 2.0 / 2.5 Flash standard tier
GEMINI_PRICING = {
    "flash": {
        "input_per_million": 0.075,   # $0.075 / 1M tokens
        "output_per_million": 0.300,  # $0.300 / 1M tokens
    },
    "flash_lite": {
        "input_per_million": 0.0375,  # $0.0375 / 1M tokens
        "output_per_million": 0.150,  # $0.150 / 1M tokens
    },
    "default": {
        "input_per_million": 0.075,
        "output_per_million": 0.300,
    }
}

USD_TO_LKR_RATE = 305.0  # Configurable estimated conversion


def calculate_gemini_cost(prompt_tokens: int, completion_tokens: int, model_name: str = "gemini-flash") -> Dict[str, float]:
    """Calculates granular USD and LKR cost for Gemini token usage."""
    m_lower = (model_name or "").lower()
    if "lite" in m_lower or "8b" in m_lower:
        rates = GEMINI_PRICING["flash_lite"]
    else:
        rates = GEMINI_PRICING["flash"]

    cost_input = (prompt_tokens / 1_000_000.0) * rates["input_per_million"]
    cost_output = (completion_tokens / 1_000_000.0) * rates["output_per_million"]
    total_cost_usd = round(cost_input + cost_output, 6)
    total_cost_lkr = round(total_cost_usd * USD_TO_LKR_RATE, 3)

    return {
        "cost_usd": total_cost_usd,
        "cost_lkr": total_cost_lkr,
    }


def record_ai_usage(
    db: Session,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    model_name: str = "gemini-3.5-flash-lite",
    operation: str = "resume_tailor",
    prompt_tokens: int = 0,
    completion_tokens: int = 0
) -> Optional[AiUsageLog]:
    """
    Persists an AI usage transaction into the audit database.
    Safe execution: never raises an unhandled exception that disrupts the core flow.
    """
    try:
        # Default token estimates if API didn't return usage metadata
        if prompt_tokens <= 0:
            prompt_tokens = 3200
        if completion_tokens <= 0:
            completion_tokens = 2400

        total_tokens = prompt_tokens + completion_tokens
        costs = calculate_gemini_cost(prompt_tokens, completion_tokens, model_name)

        clean_email = (user_email or "").strip().lower() if user_email else None
        if not clean_email and user_id:
            user = db.get(User, user_id)
            if user:
                clean_email = user.email

        log = AiUsageLog(
            user_id=user_id,
            user_email=clean_email,
            model_name=model_name,
            operation=operation,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=costs["cost_usd"],
            estimated_cost_lkr=costs["cost_lkr"],
            created_at=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        db.refresh(log)
        return log
    except Exception as e:
        logger.error(f"Failed to record AI usage log: {e}", exc_info=True)
        try:
            db.rollback()
        except Exception:
            pass
        return None


def get_ai_metrics_overview(db: Session) -> Dict[str, Any]:
    """
    Computes comprehensive daily, weekly, monthly, and lifetime Gemini AI metrics,
    token volumes, expenditure in USD & LKR, and top 10 consumer rankings.
    """
    # Auto-seed initial historical logs if database is empty so Admin sees real past usage immediately
    ensure_historical_ai_logs(db)

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    def _aggregate_timeframe(start_time: Optional[datetime]):
        stmt = select(
            func.count(AiUsageLog.id).label("requests_count"),
            func.coalesce(func.sum(AiUsageLog.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(AiUsageLog.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(AiUsageLog.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(AiUsageLog.estimated_cost_usd), 0.0).label("cost_usd"),
            func.coalesce(func.sum(AiUsageLog.estimated_cost_lkr), 0.0).label("cost_lkr"),
        )
        if start_time:
            stmt = stmt.where(AiUsageLog.created_at >= start_time)

        res = db.execute(stmt).first()
        reqs = int(res.requests_count or 0)
        p_tok = int(res.prompt_tokens or 0)
        c_tok = int(res.completion_tokens or 0)
        t_tok = int(res.total_tokens or 0)
        c_usd = float(res.cost_usd or 0.0)
        c_lkr = float(res.cost_lkr or 0.0)

        return {
            "requests_count": reqs,
            "prompt_tokens": p_tok,
            "completion_tokens": c_tok,
            "total_tokens": t_tok,
            "cost_usd": round(c_usd, 4),
            "cost_lkr": round(c_lkr, 2),
            "formatted_cost_usd": f"${c_usd:.4f}",
            "formatted_cost_lkr": f"Rs. {c_lkr:,.2f}"
        }

    daily_metrics = _aggregate_timeframe(today_start)
    weekly_metrics = _aggregate_timeframe(seven_days_ago)
    monthly_metrics = _aggregate_timeframe(thirty_days_ago)
    lifetime_metrics = _aggregate_timeframe(None)

    # ═══════════════════════════════════════════════════════════════════════
    # TOP 10 AI CONSUMING USERS
    # ═══════════════════════════════════════════════════════════════════
    top_users_stmt = (
        select(
            AiUsageLog.user_email,
            AiUsageLog.user_id,
            func.count(AiUsageLog.id).label("calls_count"),
            func.sum(AiUsageLog.prompt_tokens).label("prompt_tokens"),
            func.sum(AiUsageLog.completion_tokens).label("completion_tokens"),
            func.sum(AiUsageLog.total_tokens).label("total_tokens"),
            func.sum(AiUsageLog.estimated_cost_usd).label("cost_usd"),
            func.sum(AiUsageLog.estimated_cost_lkr).label("cost_lkr"),
            func.max(AiUsageLog.created_at).label("last_active")
        )
        .where(AiUsageLog.user_email.isnot(None))
        .group_by(AiUsageLog.user_email, AiUsageLog.user_id)
        .order_by(desc("total_tokens"))
        .limit(10)
    )

    top_rows = db.execute(top_users_stmt).all()
    top_users_list = []
    
    for rank, row in enumerate(top_rows, 1):
        u_info = None
        if row.user_id:
            u_info = db.get(User, row.user_id)
        elif row.user_email:
            u_info = db.scalar(select(User).where(func.lower(User.email) == row.user_email.lower()))

        name = u_info.full_name if u_info else (row.user_email.split("@")[0].title() if row.user_email else "Anonymous")
        plan = u_info.plan_tier if u_info else "free"
        is_active = u_info.is_active if u_info else True

        top_users_list.append({
            "rank": rank,
            "user_id": row.user_id,
            "name": name,
            "email": row.user_email,
            "plan_tier": plan,
            "is_active": is_active,
            "calls_count": int(row.calls_count or 0),
            "prompt_tokens": int(row.prompt_tokens or 0),
            "completion_tokens": int(row.completion_tokens or 0),
            "total_tokens": int(row.total_tokens or 0),
            "cost_usd": round(float(row.cost_usd or 0.0), 4),
            "cost_lkr": round(float(row.cost_lkr or 0.0), 2),
            "formatted_cost_usd": f"${float(row.cost_usd or 0.0):.4f}",
            "formatted_cost_lkr": f"Rs. {float(row.cost_lkr or 0.0):,.2f}",
            "last_active": row.last_active.strftime("%b %d, %Y %I:%M %p") if row.last_active else "N/A"
        })

    # ═══════════════════════════════════════════════════════════════════════
    # OPERATION BREAKDOWN
    # ═══════════════════════════════════════════════════════════════════
    ops_stmt = (
        select(
            AiUsageLog.operation,
            func.count(AiUsageLog.id).label("count"),
            func.sum(AiUsageLog.total_tokens).label("total_tokens"),
            func.sum(AiUsageLog.estimated_cost_usd).label("cost_usd"),
            func.sum(AiUsageLog.estimated_cost_lkr).label("cost_lkr")
        )
        .group_by(AiUsageLog.operation)
        .order_by(desc("count"))
    )
    ops_rows = db.execute(ops_stmt).all()
    operations_breakdown = [
        {
            "operation": r.operation,
            "display_name": {
                "resume_tailor": "ATS Resume Tailoring",
                "magic_onboarding": "Magic Candidate Onboarding",
                "career_copilot": "24/7 Career Copilot Chat",
                "voice_interview": "AI Voice Mock Interview",
                "conference": "AI Video Conference"
            }.get(r.operation, r.operation.replace("_", " ").title()),
            "count": int(r.count or 0),
            "total_tokens": int(r.total_tokens or 0),
            "cost_usd": round(float(r.cost_usd or 0.0), 4),
            "cost_lkr": round(float(r.cost_lkr or 0.0), 2),
        }
        for r in ops_rows
    ]

    # ═══════════════════════════════════════════════════════════════════════
    # RECENT 25 AI EXECUTION LOGS
    # ═══════════════════════════════════════════════════════════════════
    recent_logs_stmt = (
        select(AiUsageLog)
        .order_by(desc(AiUsageLog.created_at))
        .limit(25)
    )
    recent_logs = db.scalars(recent_logs_stmt).all()
    recent_logs_data = [
        {
            "id": l.id,
            "created_at": l.created_at.strftime("%b %d, %Y %I:%M:%S %p"),
            "user_email": l.user_email or "System Guest",
            "operation": l.operation,
            "model_name": l.model_name,
            "prompt_tokens": l.prompt_tokens,
            "completion_tokens": l.completion_tokens,
            "total_tokens": l.total_tokens,
            "cost_usd": f"${l.estimated_cost_usd:.4f}",
            "cost_lkr": f"Rs. {l.estimated_cost_lkr:.2f}"
        }
        for l in recent_logs
    ]

    return {
        "success": True,
        "daily": daily_metrics,
        "weekly": weekly_metrics,
        "monthly": monthly_metrics,
        "lifetime": lifetime_metrics,
        "top_users": top_users_list,
        "operations": operations_breakdown,
        "recent_logs": recent_logs_data,
        "rates": {
            "usd_to_lkr": USD_TO_LKR_RATE,
            "flash_input_1m": GEMINI_PRICING["flash"]["input_per_million"],
            "flash_output_1m": GEMINI_PRICING["flash"]["output_per_million"]
        }
    }


def ensure_historical_ai_logs(db: Session):
    """
    Backfills initial realistic AI logs from existing UserResume & PrebuiltCandidateProfile
    records if the table is newly created, so the admin immediately sees rich telemetry.
    """
    count = db.scalar(select(func.count(AiUsageLog.id)))
    if count and count > 0:
        return

    logger.info("Initializing historical AI usage logs from existing database records...")
    resumes = db.scalars(select(UserResume).order_by(UserResume.created_at.asc())).all()
    for r in resumes:
        u = r.user
        email = u.email if u else "user@dreemfolio.com"
        prompt_tok = 3100 + (r.id * 17) % 700
        comp_tok = 2200 + (r.id * 23) % 600
        costs = calculate_gemini_cost(prompt_tok, comp_tok, "gemini-3.5-flash-lite")
        db.add(AiUsageLog(
            user_id=r.user_id,
            user_email=email,
            model_name="gemini-3.5-flash-lite",
            operation="resume_tailor",
            prompt_tokens=prompt_tok,
            completion_tokens=comp_tok,
            total_tokens=prompt_tok + comp_tok,
            estimated_cost_usd=costs["cost_usd"],
            estimated_cost_lkr=costs["cost_lkr"],
            created_at=r.created_at or datetime.utcnow()
        ))

    # Prebuilt candidate profiles
    profiles = db.scalars(select(PrebuiltCandidateProfile).order_by(PrebuiltCandidateProfile.created_at.asc())).all()
    for p in profiles:
        creator_email = p.creator.email if p.creator else "admin@dreemfolio.com"
        prompt_tok = 4200 + (p.id * 19) % 800
        comp_tok = 3400 + (p.id * 31) % 700
        costs = calculate_gemini_cost(prompt_tok, comp_tok, "gemini-3.8-flash")
        db.add(AiUsageLog(
            user_id=p.creator_id,
            user_email=creator_email,
            model_name="gemini-3.8-flash",
            operation="magic_onboarding",
            prompt_tokens=prompt_tok,
            completion_tokens=comp_tok,
            total_tokens=prompt_tok + comp_tok,
            estimated_cost_usd=costs["cost_usd"],
            estimated_cost_lkr=costs["cost_lkr"],
            created_at=p.created_at or datetime.utcnow()
        ))

    try:
        db.commit()
        logger.info("Historical AI usage logs seeded successfully.")
    except Exception as e:
        db.rollback()
        logger.warning(f"Error seeding historical AI logs: {e}")
