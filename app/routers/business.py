import os
import uuid
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.database import get_db
from app.models import User, PrebuiltCandidateProfile, BusinessCreditTransaction, OnlinePaymentOrder
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

logger = logging.getLogger("dreemfolio.business_router")

router = APIRouter(prefix="/api/business", tags=["Business & Candidate Onboarding"])


@router.post("/prebuild", response_model=PrebuildProfileResponse)
async def api_prebuild_candidate(
    request: Request,
    candidate_email: str = Form(..., description="Candidate's email address"),
    target_role: Optional[str] = Form(None, description="Target job title or profession"),
    file: UploadFile = File(..., description="Candidate resume PDF or Word file"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Magic Candidate Onboarding:
    Admin and Business users upload a candidate CV. AI extracts, formats, and structures
    the resume into an ATS profile and auto-publishes a live web portfolio.
    Issues a cryptographically secure, 1-click claim URL.
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
        base_url=base_url
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
        claimed_user_name = None
        if p.claimed_by:
            claimed_user_name = p.claimed_by.full_name or p.claimed_by.email

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
            created_at=p.created_at.strftime("%b %d, %Y %I:%M %p"),
            claimed_at=p.claimed_at.strftime("%b %d, %Y %I:%M %p") if p.claimed_at else None,
            claimed_by_name=claimed_user_name,
            creator_name=creator_user_name
        ))

    return results


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
    matched_pack = next((p for p in CREDIT_PACKS if p["pack_id"] == req.pack_id), None)
    if not matched_pack:
        raise HTTPException(status_code=400, detail="Invalid credit pack selected.")

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
