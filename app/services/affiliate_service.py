import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_

from app.models import User, SaasSetting, AffiliateCommission, AffiliateWithdrawal
from app.email_service import enqueue_email, send_raw_email, get_admin_emails
from app.auth import get_saas_setting

logger = logging.getLogger("dreemfolio.affiliate")

# Default affiliate configuration constants
DEFAULT_AFFILIATE_SETTINGS = {
    "affiliate_program_enabled": "true",
    "affiliate_commission_rate": "20.0",     # 20% commission on paid plans
    "affiliate_min_withdrawal": "2000.0",    # LKR 2,000 minimum payout threshold
    "affiliate_expiry_days": "90",           # Commission expires in 90 days if inactive
    "affiliate_commission_rule": "first_purchase"  # 'first_purchase' or 'all_purchases'
}


def get_affiliate_settings(db: Session) -> Dict[str, Any]:
    """Retrieve dynamic Affiliate & Referral program settings from SaasSetting table."""
    settings = dict(DEFAULT_AFFILIATE_SETTINGS)
    try:
        keys = list(DEFAULT_AFFILIATE_SETTINGS.keys())
        stmt = select(SaasSetting).where(SaasSetting.key.in_(keys))
        rows = db.scalars(stmt).all()
        for r in rows:
            settings[r.key] = r.value
    except Exception as e:
        logger.warning("Failed to load affiliate settings from DB, using defaults: %s", e)

    return {
        "enabled": settings["affiliate_program_enabled"].lower() in ("true", "1", "yes"),
        "commission_rate": float(settings.get("affiliate_commission_rate", 20.0)),
        "min_withdrawal": float(settings.get("affiliate_min_withdrawal", 2000.0)),
        "expiry_days": int(settings.get("affiliate_expiry_days", 90)),
        "commission_rule": settings.get("affiliate_commission_rule", "first_purchase"),
    }


def update_affiliate_settings(
    db: Session,
    enabled: Optional[bool] = None,
    commission_rate: Optional[float] = None,
    min_withdrawal: Optional[float] = None,
    expiry_days: Optional[int] = None,
    commission_rule: Optional[str] = None
) -> Dict[str, Any]:
    """Update dynamic affiliate configurations in SaasSetting table."""
    updates = {}
    if enabled is not None:
        updates["affiliate_program_enabled"] = "true" if enabled else "false"
    if commission_rate is not None:
        updates["affiliate_commission_rate"] = str(round(max(1.0, min(100.0, commission_rate)), 2))
    if min_withdrawal is not None:
        updates["affiliate_min_withdrawal"] = str(round(max(100.0, min_withdrawal), 2))
    if expiry_days is not None:
        updates["affiliate_expiry_days"] = str(max(7, min(365, expiry_days)))
    if commission_rule is not None and commission_rule in ("first_purchase", "all_purchases"):
        updates["affiliate_commission_rule"] = commission_rule

    for k, v in updates.items():
        stmt = select(SaasSetting).where(SaasSetting.key == k)
        setting = db.scalars(stmt).first()
        if setting:
            setting.value = v
            setting.updated_at = datetime.utcnow()
        else:
            db.add(SaasSetting(key=k, value=v, description=f"Affiliate Program Config: {k}"))

    db.commit()
    return get_affiliate_settings(db)


def get_overdue_commissions_preview(db: Session) -> Dict[str, Any]:
    """
    Preview count and sum of commissions currently past their expiration date without modifying DB.
    Enables safe dry-run audit before executing real expiry sweeps.
    """
    now = datetime.utcnow()
    stmt = (
        select(AffiliateCommission)
        .where(
            AffiliateCommission.status == "active",
            AffiliateCommission.expires_at <= now
        )
    )
    overdue = db.scalars(stmt).all()
    return {
        "count": len(overdue),
        "total_amount": round(sum(c.commission_amount for c in overdue), 2)
    }


def expire_stale_commissions(db: Session) -> int:
    """
    Automated Balance Expiry Engine.
    Scans for active commissions past their expiration date and transitions them to 'expired'.
    Protects SaaS balance sheet and liabilities.
    """
    now = datetime.utcnow()
    stmt = (
        select(AffiliateCommission)
        .where(
            AffiliateCommission.status == "active",
            AffiliateCommission.expires_at <= now
        )
    )
    stale_commissions = db.scalars(stmt).all()
    count = 0
    for c in stale_commissions:
        c.status = "expired"
        c.expired_at = now
        count += 1

    if count > 0:
        db.commit()
        logger.info("🛡️ Automated Affiliate Engine: Expired %d stale commissions past due date.", count)
    return count


def record_commission_on_payment(
    buyer: User,
    order_amount: float,
    order_id: str,
    db: Session
) -> Optional[AffiliateCommission]:
    """
    Idempotent Revenue-Share Trigger.
    Called whenever an online payment (PayHere) or bank slip upgrade completes successfully.
    """
    try:
        expire_stale_commissions(db)
        settings = get_affiliate_settings(db)
        if not settings["enabled"]:
            logger.info("Affiliate program disabled. Skipping commission for order %s", order_id)
            return None

        # Buyer must have been invited by a referrer
        if not buyer or not buyer.referred_by_id:
            return None

        referrer_id = buyer.referred_by_id

        # Anti-fraud: cannot refer oneself
        if referrer_id == buyer.id:
            logger.warning("Anti-fraud: User #%d attempted self-referral commission on order %s", buyer.id, order_id)
            return None

        referrer = db.scalars(select(User).where(User.id == referrer_id)).first()
        if not referrer or not referrer.is_active:
            return None

        # Idempotency check: don't award twice for the same order_id
        existing_order_comm = db.scalars(
            select(AffiliateCommission).where(AffiliateCommission.order_id == str(order_id))
        ).first()
        if existing_order_comm:
            logger.info("Affiliate commission already recorded for order_id=%s. Skipping.", order_id)
            return existing_order_comm

        # Rule check: first_purchase only
        if settings["commission_rule"] == "first_purchase":
            prev_comm = db.scalars(
                select(AffiliateCommission).where(AffiliateCommission.buyer_id == buyer.id)
            ).first()
            if prev_comm:
                logger.info(
                    "Affiliate rule 'first_purchase' in effect: Buyer #%d already generated commission. Skipping order %s.",
                    buyer.id, order_id
                )
                return None

        rate = settings["commission_rate"]
        commission_amount = round(float(order_amount) * (rate / 100.0), 2)
        if commission_amount <= 0.0:
            return None

        expiry_days = settings["expiry_days"]
        expires_at = datetime.utcnow() + timedelta(days=expiry_days)

        commission = AffiliateCommission(
            referrer_id=referrer.id,
            buyer_id=buyer.id,
            order_id=str(order_id),
            order_amount=float(order_amount),
            commission_rate=float(rate),
            commission_amount=commission_amount,
            status="active",
            expires_at=expires_at,
            created_at=datetime.utcnow()
        )
        db.add(commission)
        db.commit()
        db.refresh(commission)

        logger.info(
            "🎉 Affiliate Commission Awarded: Referrer #%d earned LKR %.2f (%g%%) from Buyer #%d (Order: %s, Expires: %s)",
            referrer.id, commission_amount, rate, buyer.id, order_id, expires_at.strftime("%Y-%m-%d")
        )

        # Notify Referrer via Transactional Email
        try:
            buyer_mask = (buyer.full_name[:2] + "***") if buyer.full_name else "A friend"
            subject = f"🎉 You earned LKR {commission_amount:,.2f} with DreemFolio Refer & Earn!"
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #1e293b; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <h2 style="color: #4f46e5; margin: 0;">DreemFolio AI — Refer & Earn</h2>
                    <p style="color: #64748b; font-size: 14px; margin-top: 4px;">Partner Program Reward Alert</p>
                </div>
                <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin-bottom: 20px;">
                    <p style="margin: 0 0 10px; font-size: 16px;">Hello <strong>{referrer.full_name or 'Partner'}</strong>,</p>
                    <p style="margin: 0 0 14px; font-size: 15px; line-height: 1.5;">
                        Great news! <strong>{buyer_mask}</strong> whom you referred just upgraded their DreemFolio AI subscription!
                    </p>
                    <div style="background: #ecfdf5; border-left: 4px solid #10b981; padding: 14px; border-radius: 4px;">
                        <span style="font-size: 13px; color: #065f46; text-transform: uppercase; font-weight: bold; display: block;">Commission Earned</span>
                        <span style="font-size: 26px; font-weight: 800; color: #047857;">LKR {commission_amount:,.2f}</span>
                    </div>
                </div>
                <p style="font-size: 14px; color: #475569; line-height: 1.6;">
                    This commission has been added to your available balance. This reward remains active for <strong>{expiry_days} days</strong> (until {expires_at.strftime('%B %d, %Y')}).
                    Once your available balance reaches <strong>LKR {settings['min_withdrawal']:,.2f}</strong>, you can request an instant bank transfer payout.
                </p>
                <div style="text-align: center; margin-top: 24px;">
                    <a href="https://dreemfolio.com/profile" style="background: #4f46e5; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: bold; font-size: 14px; display: inline-block;">
                        View Referral Dashboard
                    </a>
                </div>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
                <p style="font-size: 12px; color: #94a3b8; text-align: center; margin: 0;">
                    DreemFolio AI Partner & Affiliate Network • Colombo, Sri Lanka
                </p>
            </div>
            """
            enqueue_email(
                to_email=referrer.email,
                subject=subject,
                html_body=html_content,
                plain_body=f"You earned LKR {commission_amount:,.2f} commission with DreemFolio Refer & Earn from {buyer_mask}!",
                db=db
            )
        except Exception as mail_err:
            logger.warning("Failed to queue commission email to referrer: %s", mail_err)

        return commission
    except Exception as e:
        logger.error("Error awarding affiliate commission on order %s: %s", order_id, e, exc_info=True)
        return None


def get_user_affiliate_summary(user: User, db: Session) -> Dict[str, Any]:
    """
    Computes comprehensive, real-time stats for the user's Refer & Earn dashboard.
    Accounts for active earnings, pending withdrawals, expired commissions, and payout history.
    """
    expire_stale_commissions(db)
    settings = get_affiliate_settings(db)

    # Ensure user has a valid referral code
    if not user.referral_code:
        from app.routers.auth import generate_unique_referral_code
        user.referral_code = generate_unique_referral_code(db)
        db.commit()
        db.refresh(user)

    # 1. Total referred registered users
    total_referrals_stmt = select(func.count(User.id)).where(User.referred_by_id == user.id)
    total_referrals_count = db.scalar(total_referrals_stmt) or 0

    # 2. Commissions breakdown
    comm_stmt = select(AffiliateCommission).where(AffiliateCommission.referrer_id == user.id)
    all_commissions = db.scalars(comm_stmt).all()

    active_earnings = 0.0
    total_earned = 0.0
    total_expired = 0.0
    paid_referrals_set = set()
    earliest_expiring_comm = None
    now = datetime.utcnow()

    for c in all_commissions:
        total_earned += c.commission_amount
        paid_referrals_set.add(c.buyer_id)
        if c.status == "active":
            active_earnings += c.commission_amount
            if earliest_expiring_comm is None or c.expires_at < earliest_expiring_comm:
                earliest_expiring_comm = c.expires_at
        elif c.status == "expired":
            total_expired += c.commission_amount

    # 3. Withdrawals breakdown
    with_stmt = (
        select(AffiliateWithdrawal)
        .where(AffiliateWithdrawal.user_id == user.id)
        .order_by(AffiliateWithdrawal.requested_at.desc())
    )
    all_withdrawals = db.scalars(with_stmt).all()

    pending_withdrawal_amount = 0.0
    total_paid_out = 0.0
    has_pending_withdrawal = False

    for w in all_withdrawals:
        if w.status == "pending":
            pending_withdrawal_amount += w.amount
            has_pending_withdrawal = True
        elif w.status == "paid":
            total_paid_out += w.amount

    # Available balance can be withdrawn: active earnings minus currently pending withdrawals
    available_balance = max(0.0, round(active_earnings - pending_withdrawal_amount, 2))
    min_limit = settings["min_withdrawal"]
    can_withdraw = (available_balance >= min_limit) and (not has_pending_withdrawal) and settings["enabled"]

    # Dynamic Currency Conversion (USD Base Rate, default: 300.0 LKR = 1 USD)
    usd_rate_str = get_saas_setting(db, "lkr_per_usd", "300.0")
    try:
        usd_rate = float(usd_rate_str)
        if usd_rate <= 0:
            usd_rate = 300.0
    except (ValueError, TypeError):
        usd_rate = 300.0

    # Format recent commissions (hide buyer identity for privacy)
    recent_commissions_data = []
    for c in sorted(all_commissions, key=lambda x: x.created_at, reverse=True)[:15]:
        buyer_ref = f"User #{c.buyer_id}"
        if c.buyer:
            parts = c.buyer.full_name.split()
            if len(parts) >= 2:
                buyer_ref = f"{parts[0]} {parts[1][0]}."
            elif parts:
                buyer_ref = f"{parts[0][:4]}***"

        days_left = max(0, (c.expires_at - now).days) if c.status == "active" else 0
        recent_commissions_data.append({
            "id": c.id,
            "buyer_name": buyer_ref,
            "order_amount": c.order_amount,
            "order_amount_usd": round(c.order_amount / usd_rate, 2),
            "commission_rate": c.commission_rate,
            "commission_amount": c.commission_amount,
            "commission_amount_usd": round(c.commission_amount / usd_rate, 2),
            "status": c.status,
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M"),
            "expires_at": c.expires_at.strftime("%Y-%m-%d"),
            "days_left": days_left
        })

    # Format recent withdrawals
    recent_withdrawals_data = []
    for w in all_withdrawals[:10]:
        w_curr = getattr(w, "currency", "LKR") or "LKR"
        w_method = getattr(w, "payout_method", "bank") or "bank"
        recent_withdrawals_data.append({
            "id": w.id,
            "amount": w.amount,
            "amount_usd": round(w.amount / usd_rate, 2),
            "currency": w_curr,
            "payout_method": w_method,
            "bank_name": w.bank_name,
            "account_number_masked": f"***{w.account_number[-4:]}" if len(w.account_number) >= 4 else w.account_number,
            "account_holder_name": w.account_holder_name,
            "branch_name": w.branch_name,
            "status": w.status,
            "payout_reference": w.payout_reference,
            "admin_notes": w.admin_notes,
            "requested_at": w.requested_at.strftime("%Y-%m-%d %H:%M"),
            "processed_at": w.processed_at.strftime("%Y-%m-%d %H:%M") if w.processed_at else None
        })

    days_until_earliest_expiry = None
    if earliest_expiring_comm:
        days_until_earliest_expiry = max(0, (earliest_expiring_comm - now).days)

    return {
        "program_enabled": settings["enabled"],
        "commission_rate": settings["commission_rate"],
        "min_withdrawal_limit": min_limit,
        "min_withdrawal_limit_usd": round(min_limit / usd_rate, 2),
        "expiry_days_config": settings["expiry_days"],
        "referral_code": getattr(user, "referral_code", None),
        "usd_rate": usd_rate,
        "total_referrals_count": total_referrals_count,
        "paid_referrals_count": len(paid_referrals_set),
        "available_balance": available_balance,
        "available_balance_usd": round(available_balance / usd_rate, 2),
        "active_earnings": round(active_earnings, 2),
        "active_earnings_usd": round(active_earnings / usd_rate, 2),
        "pending_withdrawal_amount": round(pending_withdrawal_amount, 2),
        "pending_withdrawal_amount_usd": round(pending_withdrawal_amount / usd_rate, 2),
        "total_earned": round(total_earned, 2),
        "total_earned_usd": round(total_earned / usd_rate, 2),
        "total_paid_out": round(total_paid_out, 2),
        "total_paid_out_usd": round(total_paid_out / usd_rate, 2),
        "total_expired": round(total_expired, 2),
        "total_expired_usd": round(total_expired / usd_rate, 2),
        "can_withdraw": can_withdraw,
        "has_pending_withdrawal": has_pending_withdrawal,
        "days_until_earliest_expiry": days_until_earliest_expiry,
        "commissions": recent_commissions_data,
        "withdrawals": recent_withdrawals_data
    }


def request_affiliate_withdrawal(
    user: User,
    amount: float,
    bank_name: str,
    account_number: str,
    account_holder_name: str,
    branch_name: Optional[str] = None,
    contact_phone: Optional[str] = None,
    currency: str = "LKR",
    payout_method: str = "bank",
    db: Session = None
) -> AffiliateWithdrawal:
    """Submit a payout withdrawal request to be approved & transferred by Admin."""
    summary = get_user_affiliate_summary(user, db)
    settings = get_affiliate_settings(db)
    usd_rate = summary.get("usd_rate", 300.0)

    if not settings["enabled"]:
        raise ValueError("The affiliate and referral program is currently paused.")

    if summary["has_pending_withdrawal"]:
        raise ValueError("You already have a pending withdrawal request under review. Please wait until it is processed.")

    clean_curr = (currency or "LKR").strip().upper()
    clean_method = (payout_method or "bank").strip().lower()

    if clean_curr == "USD":
        # Converted to base LKR units
        amount_lkr = round(float(amount) * usd_rate, 2)
        min_usd = round(settings["min_withdrawal"] / usd_rate, 2)
        if float(amount) < min_usd:
            raise ValueError(f"Minimum withdrawal limit is ${min_usd:,.2f} USD (approx LKR {settings['min_withdrawal']:,.2f}).")
    else:
        amount_lkr = round(float(amount), 2)
        if amount_lkr < settings["min_withdrawal"]:
            raise ValueError(f"Minimum withdrawal limit is LKR {settings['min_withdrawal']:,.2f}.")

    if amount_lkr > summary["available_balance"]:
        if clean_curr == "USD":
            raise ValueError(f"Insufficient available balance. Your balance is ${summary['available_balance_usd']:,.2f} USD.")
        else:
            raise ValueError(f"Insufficient available balance. Your balance is LKR {summary['available_balance']:,.2f}.")

    clean_branch = (branch_name or "").strip()
    if not clean_branch:
        clean_branch = "International / Online" if clean_method in ["paypal", "wise", "payoneer", "crypto"] else "Main"

    withdrawal = AffiliateWithdrawal(
        user_id=user.id,
        amount=amount_lkr,
        currency=clean_curr,
        payout_method=clean_method,
        bank_name=bank_name.strip(),
        account_number=account_number.strip(),
        account_holder_name=account_holder_name.strip(),
        branch_name=clean_branch,
        contact_phone=contact_phone.strip() if contact_phone else None,
        status="pending",
        requested_at=datetime.utcnow()
    )
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)

    # Notify Admins via Email
    try:
        admin_emails = get_admin_emails(db)
        display_amt = f"${float(amount):,.2f} USD" if clean_curr == "USD" else f"LKR {amount_lkr:,.2f}"
        admin_subject = f"💸 [Affiliate Payout Request] {display_amt} via {clean_method.upper()} from {user.email}"
        admin_body = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; color: #1e293b;">
            <h3 style="color: #4f46e5;">New Affiliate Withdrawal Request</h3>
            <p>Candidate <strong>{user.full_name} ({user.email})</strong> has requested an affiliate payout:</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 15px;">
                <tr><td style="padding: 6px; font-weight: bold; width: 140px;">Requested Amount:</td><td style="padding: 6px; color: #047857; font-weight: bold;">{display_amt} (Base: LKR {amount_lkr:,.2f})</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">Payout Method:</td><td style="padding: 6px; text-transform: uppercase; font-weight: bold;">{clean_method}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">Payment Destination / Bank:</td><td style="padding: 6px;">{withdrawal.bank_name}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">Branch / Country:</td><td style="padding: 6px;">{withdrawal.branch_name}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">Account / PayPal Email:</td><td style="padding: 6px; font-family: monospace; font-weight: bold; color: #4338ca;">{withdrawal.account_number}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">Beneficiary Name:</td><td style="padding: 6px;">{withdrawal.account_holder_name}</td></tr>
                <tr><td style="padding: 6px; font-weight: bold;">Contact Phone:</td><td style="padding: 6px;">{withdrawal.contact_phone or 'N/A'}</td></tr>
            </table>
            <p style="margin-top: 20px;">
                Please review and approve this payout in the <a href="https://dreemfolio.com/admin#affiliate">Admin Control Center</a>.
            </p>
        </div>
        """
        for admin_e in admin_emails:
            enqueue_email(
                to_email=admin_e,
                subject=admin_subject,
                html_body=admin_body,
                plain_body=f"Affiliate withdrawal request: LKR {amount_clean:,.2f} by {user.email}",
                db=db
            )
    except Exception as notify_err:
        logger.warning("Failed to queue admin notification for withdrawal request: %s", notify_err)

    return withdrawal


def admin_approve_payout(
    withdrawal_id: int,
    admin_user: User,
    payout_reference: str,
    admin_notes: Optional[str],
    db: Session
) -> AffiliateWithdrawal:
    """
    Admin confirms bank transfer was executed.
    Marks withdrawal as 'paid', records transfer slip/ref, and moves active commissions to 'withdrawn'.
    """
    stmt = select(AffiliateWithdrawal).where(AffiliateWithdrawal.id == withdrawal_id)
    withdrawal = db.scalars(stmt).first()
    if not withdrawal:
        raise ValueError(f"Withdrawal request #{withdrawal_id} not found.")

    if withdrawal.status != "pending":
        raise ValueError(f"Withdrawal request #{withdrawal_id} is already '{withdrawal.status}'.")

    # Deduct from active commissions (oldest first)
    amount_remaining = withdrawal.amount
    comm_stmt = (
        select(AffiliateCommission)
        .where(
            AffiliateCommission.referrer_id == withdrawal.user_id,
            AffiliateCommission.status == "active"
        )
        .order_by(AffiliateCommission.created_at.asc())
    )
    active_comms = db.scalars(comm_stmt).all()
    for c in active_comms:
        if amount_remaining <= 0:
            break
        if c.commission_amount <= amount_remaining:
            amount_remaining -= c.commission_amount
            c.status = "withdrawn"
        else:
            # Partial withdrawal on this commission chunk: split it
            diff = c.commission_amount - amount_remaining
            c.commission_amount = amount_remaining
            c.status = "withdrawn"
            # Remainder stays active with original expiry
            remainder_comm = AffiliateCommission(
                referrer_id=c.referrer_id,
                buyer_id=c.buyer_id,
                order_id=c.order_id,
                order_amount=c.order_amount,
                commission_rate=c.commission_rate,
                commission_amount=round(diff, 2),
                status="active",
                expires_at=c.expires_at,
                created_at=c.created_at
            )
            db.add(remainder_comm)
            amount_remaining = 0

    now = datetime.utcnow()
    withdrawal.status = "paid"
    withdrawal.payout_reference = payout_reference.strip() if payout_reference else "COMPLETED"
    withdrawal.admin_notes = admin_notes.strip() if admin_notes else None
    withdrawal.processed_at = now
    withdrawal.processed_by_admin = admin_user.email

    db.commit()
    db.refresh(withdrawal)

    # Send confirmation email to candidate
    try:
        user = withdrawal.user
        subject = f"✅ Affiliate Payout Transferred: LKR {withdrawal.amount:,.2f} sent to your bank!"
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #1e293b; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0;">
            <h2 style="color: #047857; margin: 0 0 10px;">Payout Transferred Successfully!</h2>
            <p style="font-size: 15px; line-height: 1.5;">
                Hello <strong>{user.full_name}</strong>, your affiliate earnings payout has been successfully transferred to your bank account.
            </p>
            <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 18px; margin: 20px 0;">
                <p style="margin: 0 0 8px; font-size: 14px;"><strong>Transferred Amount:</strong> <span style="font-size: 18px; color: #047857; font-weight: bold;">LKR {withdrawal.amount:,.2f}</span></p>
                <p style="margin: 0 0 8px; font-size: 14px;"><strong>Bank Name:</strong> {withdrawal.bank_name}</p>
                <p style="margin: 0 0 8px; font-size: 14px;"><strong>Account Number:</strong> {withdrawal.account_number}</p>
                <p style="margin: 0 0 8px; font-size: 14px;"><strong>Bank Reference / Slip ID:</strong> <span style="font-family: monospace; font-weight: bold;">{withdrawal.payout_reference}</span></p>
                {f'<p style="margin: 0; font-size: 14px;"><strong>Note:</strong> {withdrawal.admin_notes}</p>' if withdrawal.admin_notes else ''}
            </div>
            <p style="font-size: 14px; color: #64748b;">
                Funds should reflect in your account within a few minutes to 1 business day depending on your bank network (CEFT/SLIPS). Keep sharing your referral link to earn more!
            </p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
            <p style="font-size: 12px; color: #94a3b8; text-align: center; margin: 0;">
                DreemFolio AI Finance & Partner Operations
            </p>
        </div>
        """
        enqueue_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            plain_body=f"Your affiliate payout of LKR {withdrawal.amount:,.2f} has been transferred (Ref: {withdrawal.payout_reference}).",
            db=db
        )
    except Exception as mail_err:
        logger.warning("Failed to queue payout confirmation email: %s", mail_err)

    return withdrawal


def admin_reject_payout(
    withdrawal_id: int,
    admin_user: User,
    reason: str,
    db: Session
) -> AffiliateWithdrawal:
    """
    Admin rejects payout request (e.g. invalid bank account).
    Releases the held balance back to the user's available balance and emails the reason.
    """
    stmt = select(AffiliateWithdrawal).where(AffiliateWithdrawal.id == withdrawal_id)
    withdrawal = db.scalars(stmt).first()
    if not withdrawal:
        raise ValueError(f"Withdrawal request #{withdrawal_id} not found.")

    if withdrawal.status != "pending":
        raise ValueError(f"Withdrawal request #{withdrawal_id} is already '{withdrawal.status}'.")

    now = datetime.utcnow()
    withdrawal.status = "rejected"
    withdrawal.admin_notes = reason.strip() if reason else "Declined by administrator."
    withdrawal.processed_at = now
    withdrawal.processed_by_admin = admin_user.email

    db.commit()
    db.refresh(withdrawal)

    # Notify candidate
    try:
        user = withdrawal.user
        subject = f"⚠️ Affiliate Withdrawal Request Update (LKR {withdrawal.amount:,.2f})"
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; color: #1e293b; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0;">
            <h2 style="color: #dc2626; margin: 0 0 10px;">Withdrawal Request Update</h2>
            <p style="font-size: 15px; line-height: 1.5;">
                Hello <strong>{user.full_name}</strong>, your affiliate payout request for <strong>LKR {withdrawal.amount:,.2f}</strong> could not be completed and was returned to your balance.
            </p>
            <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 18px; margin: 20px 0;">
                <p style="margin: 0; font-size: 14px; color: #991b1b;">
                    <strong>Reason for decline:</strong> {withdrawal.admin_notes}
                </p>
            </div>
            <p style="font-size: 14px; color: #475569;">
                Your funds remain safely in your available affiliate balance. Please review your bank details and submit a new request via your dashboard.
            </p>
            <div style="text-align: center; margin-top: 24px;">
                <a href="https://dreemfolio.com/profile" style="background: #4f46e5; color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: bold; font-size: 14px; display: inline-block;">
                    Open Referral Dashboard
                </a>
            </div>
        </div>
        """
        enqueue_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            plain_body=f"Your affiliate payout request was returned to your balance: {withdrawal.admin_notes}",
            db=db
        )
    except Exception as mail_err:
        logger.warning("Failed to queue payout rejection email: %s", mail_err)

    return withdrawal


def get_admin_affiliate_overview(db: Session) -> Dict[str, Any]:
    """Retrieve full ecosystem metrics for the Admin Affiliate Management Portal."""
    expire_stale_commissions(db)
    settings = get_affiliate_settings(db)

    # Total registered affiliates (users with referral_code who brought at least 1 referral)
    total_affiliates_stmt = select(func.count(func.distinct(User.referred_by_id))).where(User.referred_by_id.is_not(None))
    active_affiliates_count = db.scalar(total_affiliates_stmt) or 0

    # Commissions summary
    all_comms = db.scalars(select(AffiliateCommission)).all()
    total_commission_awarded = sum(c.commission_amount for c in all_comms)
    active_liability_balance = sum(c.commission_amount for c in all_comms if c.status == "active")
    total_expired_balance = sum(c.commission_amount for c in all_comms if c.status == "expired")

    # Withdrawals summary
    all_withs = db.scalars(select(AffiliateWithdrawal).order_by(AffiliateWithdrawal.requested_at.desc())).all()
    pending_withdrawals = [w for w in all_withs if w.status == "pending"]
    paid_withdrawals = [w for w in all_withs if w.status == "paid"]
    total_paid_out = sum(w.amount for w in paid_withdrawals)
    pending_payout_amount = sum(w.amount for w in pending_withdrawals)

    # Top referrers leaderboard
    top_referrers_stmt = (
        select(
            User.id,
            User.email,
            User.full_name,
            func.count(AffiliateCommission.id).label("total_sales"),
            func.sum(AffiliateCommission.commission_amount).label("total_earned")
        )
        .join(AffiliateCommission, AffiliateCommission.referrer_id == User.id)
        .group_by(User.id, User.email, User.full_name)
        .order_by(func.sum(AffiliateCommission.commission_amount).desc())
        .limit(10)
    )
    top_referrers_rows = db.execute(top_referrers_stmt).all()
    top_referrers = [
        {
            "id": r.id,
            "email": r.email,
            "full_name": r.full_name,
            "total_sales": r.total_sales,
            "total_earned": round(float(r.total_earned or 0.0), 2)
        }
        for r in top_referrers_rows
    ]

    return {
        "settings": settings,
        "metrics": {
            "active_affiliates_count": active_affiliates_count,
            "total_commission_awarded": round(total_commission_awarded, 2),
            "active_liability_balance": round(active_liability_balance, 2),
            "pending_payout_count": len(pending_withdrawals),
            "pending_payout_amount": round(pending_payout_amount, 2),
            "total_paid_out": round(total_paid_out, 2),
            "total_expired_balance": round(total_expired_balance, 2)
        },
        "pending_withdrawals": [
            {
                "id": w.id,
                "user_id": w.user_id,
                "user_email": w.user.email if w.user else "N/A",
                "user_name": w.user.full_name if w.user else "N/A",
                "amount": w.amount,
                "amount_usd": round(w.amount / float(get_saas_setting(db, "lkr_per_usd", "300.0") or 300.0), 2),
                "currency": getattr(w, "currency", "LKR") or "LKR",
                "payout_method": getattr(w, "payout_method", "bank") or "bank",
                "bank_name": w.bank_name,
                "account_number": w.account_number,
                "account_holder_name": w.account_holder_name,
                "branch_name": w.branch_name,
                "contact_phone": w.contact_phone,
                "requested_at": w.requested_at.strftime("%Y-%m-%d %H:%M")
            }
            for w in pending_withdrawals
        ],
        "top_referrers": top_referrers
    }
