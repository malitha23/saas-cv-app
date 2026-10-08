import re
import hashlib
import datetime
import logging
from typing import Optional
from fastapi import APIRouter, Request, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import SiteVisitor, MarketingLead, CookieConsentLog

logger = logging.getLogger("dreemfolio.analytics")

router = APIRouter(tags=["Analytics & Lead Capture"])

BOT_USER_AGENTS = [
    "bot", "crawler", "spider", "googlebot", "bingbot", "slurp", "duckduckbot",
    "baiduspider", "yandexbot", "sogou", "exabot", "facebot", "ia_archiver",
    "semrushbot", "ahrefsbot", "mj12bot", "dotbot", "petalbot", "screaming frog",
    "uptimerobot", "pingdom", "curl", "python-requests", "postman", "headlesschrome",
    "lighthouse", "bytespider", "gptbot", "chatgpt-user"
]


def _extract_client_ip(request: Request) -> str:
    """Extract real client IP respecting Cloudflare and reverse proxies."""
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip and cf_ip.strip():
        return cf_ip.split(",")[0].strip()

    x_forwarded = request.headers.get("x-forwarded-for")
    if x_forwarded and x_forwarded.strip():
        return x_forwarded.split(",")[0].strip()

    x_real = request.headers.get("x-real-ip")
    if x_real and x_real.strip():
        return x_real.strip()

    if request.client and request.client.host:
        return request.client.host.strip()

    return "127.0.0.1"


def _anonymize_ip(ip: str) -> str:
    """GDPR / Sri Lanka PDPA compliant IP anonymization."""
    if not ip:
        return "0.0.0.0"
    if ":" in ip:
        # IPv6: keep first 3 segments
        parts = ip.split(":")
        return ":".join(parts[:3]) + "::xxx"
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.xxx"
    return "xxx.xxx.xxx.xxx"


def _detect_device(user_agent: str, screen_width: Optional[int] = None) -> str:
    """Detect device category from User-Agent and optional screen width."""
    ua = (user_agent or "").lower()
    if screen_width and screen_width > 0:
        if screen_width < 768:
            return "mobile"
        elif screen_width < 1024:
            return "tablet"
        return "desktop"

    if any(t in ua for t in ["ipad", "tablet", "playbook", "silk"]):
        return "tablet"
    if any(m in ua for m in ["mobile", "android", "iphone", "ipod", "blackberry", "iemobile", "opera mini"]):
        return "mobile"
    return "desktop"


def _is_bot_user_agent(user_agent: str) -> bool:
    """Check if User-Agent belongs to a known crawler or bot."""
    ua = (user_agent or "").lower()
    return any(bot in ua for bot in BOT_USER_AGENTS)


class PageViewRequest(BaseModel):
    path: str = Field(..., max_length=255)
    referrer: Optional[str] = Field(default="", max_length=500)
    screen_width: Optional[int] = Field(default=None)


class CookieConsentRequest(BaseModel):
    consent_type: Optional[str] = Field(default="essential_and_analytics", max_length=50)


class MarketingLeadRequest(BaseModel):
    email: str = Field(..., max_length=255)
    source: Optional[str] = Field(default="cookie_banner", max_length=100)


@router.post("/api/track/pageview")
async def track_pageview(
    data: PageViewRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Lightweight, asynchronous pageview & visitor beacon.
    Deduplicates unique human sessions and isolates bot crawler activity.
    """
    try:
        raw_ip = _extract_client_ip(request)
        ua = request.headers.get("user-agent", "")[:500]
        country = (request.headers.get("cf-ipcountry") or "UNKNOWN").upper()[:10]

        # Anonymized daily hash for unique visitors (PDPA & GDPR compliant)
        today_str = datetime.date.today().isoformat()
        hash_seed = f"dreemfolio_salt_{raw_ip}_{today_str}_{ua[:40]}"
        visitor_hash = hashlib.sha256(hash_seed.encode("utf-8")).hexdigest()[:32]

        is_bot = _is_bot_user_agent(ua)
        device = _detect_device(ua, data.screen_width)
        anonymized_ip = _anonymize_ip(raw_ip)
        clean_path = (data.path or "/").strip()[:255]
        clean_referrer = (data.referrer or "").strip()[:500] or None

        visitor_record = SiteVisitor(
            visitor_hash=visitor_hash,
            ip_address=anonymized_ip,
            country_code=country,
            path=clean_path,
            referrer=clean_referrer,
            device_type=device,
            user_agent=ua,
            is_bot=is_bot,
            cookie_consented=False,
            created_at=datetime.datetime.utcnow()
        )
        db.add(visitor_record)
        db.commit()
    except Exception as e:
        logger.warning("Failed to record pageview: %s", e)
        db.rollback()

    return {"status": "ok"}


@router.post("/api/track/consent")
async def track_cookie_consent(
    data: CookieConsentRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Log user acceptance of cookie & local storage privacy policy.
    Provides verified compliance audit log.
    """
    try:
        raw_ip = _extract_client_ip(request)
        country = (request.headers.get("cf-ipcountry") or "UNKNOWN").upper()[:10]
        today_str = datetime.date.today().isoformat()
        visitor_hash = hashlib.sha256(f"dreemfolio_salt_{raw_ip}_{today_str}".encode("utf-8")).hexdigest()[:32]

        consent_log = CookieConsentLog(
            visitor_hash=visitor_hash,
            country_code=country,
            consent_type=data.consent_type or "essential_and_analytics",
            created_at=datetime.datetime.utcnow()
        )
        db.add(consent_log)

        # Also flag recent visitor rows for this session as consented
        recent_visitors = db.scalars(
            select(SiteVisitor)
            .where(SiteVisitor.visitor_hash == visitor_hash)
            .order_by(SiteVisitor.id.desc())
            .limit(10)
        ).all()
        for v in recent_visitors:
            v.cookie_consented = True

        db.commit()
    except Exception as e:
        logger.warning("Failed to record cookie consent: %s", e)
        db.rollback()

    return {"status": "ok"}


@router.post("/api/marketing/lead")
async def capture_marketing_lead(
    data: MarketingLeadRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Capture visitor sales & marketing email lead (from cookie bar, exit intent, or lead magnet).
    Stores clean lead record for marketing campaigns.
    """
    clean_email = (data.email or "").strip().lower()
    if not clean_email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    try:
        raw_ip = _extract_client_ip(request)
        country = (request.headers.get("cf-ipcountry") or "UNKNOWN").upper()[:10]
        anonymized_ip = _anonymize_ip(raw_ip)
        source = (data.source or "cookie_banner").strip()[:100]

        # Check if already captured to avoid redundant duplicate noise
        existing_lead = db.scalar(
            select(MarketingLead).where(MarketingLead.email == clean_email)
        )
        if not existing_lead:
            new_lead = MarketingLead(
                email=clean_email,
                source=source,
                country_code=country,
                ip_address=anonymized_ip,
                consent_given=True,
                created_at=datetime.datetime.utcnow()
            )
            db.add(new_lead)
            db.commit()
            logger.info("🎯 New marketing lead captured: %s (Source: %s, Country: %s)", clean_email, source, country)

        return {
            "success": True,
            "message": "Thank you! You've been subscribed to DreemFolio ATS tips & exclusive career updates."
        }
    except Exception as e:
        logger.error("Error capturing marketing lead: %s", e)
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not record subscription. Please try again.")
