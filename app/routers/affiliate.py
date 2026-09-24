import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import User, AffiliateWithdrawal, AffiliateCommission
from app.auth import get_current_user, require_admin
from app.services.affiliate_service import (
    get_affiliate_settings,
    update_affiliate_settings,
    get_user_affiliate_summary,
    request_affiliate_withdrawal,
    admin_approve_payout,
    admin_reject_payout,
    get_admin_affiliate_overview,
    expire_stale_commissions
)

logger = logging.getLogger("dreemfolio.affiliate_router")

router = APIRouter(tags=["Refer & Earn / Affiliate Program"])


# ─────────────────────────────────────────────────────────────────────────────
# PYDANTIC SCHEMAS
# ─────────────────────────────────────────────────────────────────────────────
class WithdrawalRequestSchema(BaseModel):
    amount: float = Field(..., gt=0, description="Amount to withdraw in LKR")
    bank_name: str = Field(..., min_length=2, max_length=100, description="Name of the bank")
    account_number: str = Field(..., min_length=4, max_length=50, description="Bank account number")
    account_holder_name: str = Field(..., min_length=2, max_length=150, description="Name of account holder")
    branch_name: str = Field(..., min_length=2, max_length=100, description="Branch name")
    contact_phone: Optional[str] = Field(None, max_length=50, description="Contact phone number")


class AdminUpdateAffiliateSettingsSchema(BaseModel):
    enabled: Optional[bool] = None
    commission_rate: Optional[float] = Field(None, ge=1.0, le=100.0)
    min_withdrawal: Optional[float] = Field(None, ge=100.0)
    expiry_days: Optional[int] = Field(None, ge=7, le=365)
    commission_rule: Optional[str] = Field(None, pattern="^(first_purchase|all_purchases)$")


class AdminApprovePayoutSchema(BaseModel):
    payout_reference: str = Field(..., min_length=1, max_length=100, description="Bank slip / transaction ref ID")
    admin_notes: Optional[str] = Field(None, max_length=500)


class AdminRejectPayoutSchema(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500, description="Reason for rejecting the payout")


# ─────────────────────────────────────────────────────────────────────────────
# CANDIDATE / USER ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/api/affiliate/settings")
async def get_public_affiliate_settings(db: Session = Depends(get_db)):
    """Publicly inspect current affiliate program parameters."""
    return get_affiliate_settings(db)


@router.get("/api/affiliate/dashboard")
async def get_affiliate_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns candidate's active balance, commissions history,
    earliest expiry countdown, and payout eligibility.
    """
    try:
        summary = get_user_affiliate_summary(current_user, db)
        return summary
    except Exception as e:
        logger.error("Error retrieving affiliate dashboard for user #%d: %s", current_user.id, e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load referral dashboard metrics."
        )


@router.post("/api/affiliate/withdraw")
async def submit_withdrawal_request(
    req: WithdrawalRequestSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit a bank transfer withdrawal request for accumulated referral earnings.
    """
    try:
        withdrawal = request_affiliate_withdrawal(
            user=current_user,
            amount=req.amount,
            bank_name=req.bank_name,
            account_number=req.account_number,
            account_holder_name=req.account_holder_name,
            branch_name=req.branch_name,
            contact_phone=req.contact_phone,
            db=db
        )
        return {
            "success": True,
            "message": f"Withdrawal request for LKR {withdrawal.amount:,.2f} submitted successfully! Our finance team will review and transfer the funds to your account.",
            "withdrawal_id": withdrawal.id
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error("Failed to process withdrawal request for user #%d: %s", current_user.id, e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit withdrawal request.")


# ─────────────────────────────────────────────────────────────────────────────
# ADMINISTRATOR CONTROL CENTER ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/api/admin/affiliate/overview")
async def admin_get_affiliate_overview(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Administrator dashboard showing total commissions, pending payouts,
    earnings expiry stats, and top referrers leaderboard.
    """
    return get_admin_affiliate_overview(db)


@router.post("/api/admin/affiliate/settings")
async def admin_set_affiliate_settings(
    req: AdminUpdateAffiliateSettingsSchema,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update affiliate program parameters (Commission %, Expiry Days, Min Withdrawal).
    """
    updated = update_affiliate_settings(
        db=db,
        enabled=req.enabled,
        commission_rate=req.commission_rate,
        min_withdrawal=req.min_withdrawal,
        expiry_days=req.expiry_days,
        commission_rule=req.commission_rule
    )
    return {
        "success": True,
        "message": "Affiliate program settings updated successfully!",
        "settings": updated
    }


@router.get("/api/admin/affiliate/withdrawals")
async def admin_list_withdrawals(
    status_filter: Optional[str] = Query("all", description="all, pending, paid, rejected"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all candidate withdrawal requests with bank credentials and audit trail."""
    stmt = select(AffiliateWithdrawal).order_by(AffiliateWithdrawal.requested_at.desc())
    if status_filter and status_filter.lower() in ("pending", "paid", "rejected"):
        stmt = stmt.where(AffiliateWithdrawal.status == status_filter.lower())

    withdrawals = db.scalars(stmt).all()
    results = []
    for w in withdrawals:
        results.append({
            "id": w.id,
            "user_id": w.user_id,
            "user_email": w.user.email if w.user else "Unknown",
            "user_name": w.user.full_name if w.user else "Unknown",
            "amount": w.amount,
            "bank_name": w.bank_name,
            "account_number": w.account_number,
            "account_holder_name": w.account_holder_name,
            "branch_name": w.branch_name,
            "contact_phone": w.contact_phone,
            "status": w.status,
            "payout_reference": w.payout_reference,
            "admin_notes": w.admin_notes,
            "requested_at": w.requested_at.strftime("%Y-%m-%d %H:%M"),
            "processed_at": w.processed_at.strftime("%Y-%m-%d %H:%M") if w.processed_at else None,
            "processed_by_admin": w.processed_by_admin
        })
    return results


@router.post("/api/admin/affiliate/withdrawals/{withdrawal_id}/approve")
async def admin_approve_withdrawal_endpoint(
    withdrawal_id: int,
    req: AdminApprovePayoutSchema,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Confirm bank transfer was executed. Marks payout as paid and deducts active commissions.
    """
    try:
        w = admin_approve_payout(
            withdrawal_id=withdrawal_id,
            admin_user=admin,
            payout_reference=req.payout_reference,
            admin_notes=req.admin_notes,
            db=db
        )
        return {
            "success": True,
            "message": f"Withdrawal #{withdrawal_id} (LKR {w.amount:,.2f}) approved and marked as Paid!",
            "payout_reference": w.payout_reference
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error("Failed to approve withdrawal #%d: %s", withdrawal_id, e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to approve withdrawal.")


@router.post("/api/admin/affiliate/withdrawals/{withdrawal_id}/reject")
async def admin_reject_withdrawal_endpoint(
    withdrawal_id: int,
    req: AdminRejectPayoutSchema,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Reject withdrawal request and release reserved funds back to user's balance.
    """
    try:
        w = admin_reject_payout(
            withdrawal_id=withdrawal_id,
            admin_user=admin,
            reason=req.reason,
            db=db
        )
        return {
            "success": True,
            "message": f"Withdrawal #{withdrawal_id} rejected. Balance restored to candidate.",
            "reason": req.reason
        }
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error("Failed to reject withdrawal #%d: %s", withdrawal_id, e, exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reject withdrawal.")


@router.post("/api/admin/affiliate/run-expiry")
async def admin_run_expiry_job(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Trigger manual sweep of expired commissions."""
    count = expire_stale_commissions(db)
    return {
        "success": True,
        "expired_commissions_count": count,
        "message": f"Successfully evaluated and expired {count} commissions."
    }
