import os
import re
import time
import hmac
import logging
from typing import Optional
import httpx
from fastapi import APIRouter, HTTPException, Response, Request, Depends, Query
from fastapi.responses import HTMLResponse

logger = logging.getLogger("dreemfolio.portfolio")

from app.models import User
from app.schemas import TailoredResume, VerifyPinRequest, VerifyPinResponse, DomainVerifyRequest
from app.auth import get_current_user, require_tier
from app.portfolio_generator import (
    generate_portfolio_html, generate_qr_code_svg,
    generate_vcard_content, generate_qr_code_png
)
from app.state import (
    PUBLISHED_PORTFOLIOS, PUBLISHED_RESUMES,
    CUSTOM_DOMAINS, PIN_ATTEMPT_STORE, _get_client_ip,
    save_published_portfolio, save_custom_domain_mapping, get_published_portfolio,
    resolve_custom_domain_slug
)

router = APIRouter(tags=["Portfolio & Branding"])


async def provision_cloudflare_custom_hostname(domain: str) -> dict:
    """
    Automated SSL provisioner using Cloudflare for SaaS (Custom Hostnames).
    Enables free Edge SSL termination for user-connected 3rd-party custom domains.
    """
    zone_id = os.getenv("CLOUDFLARE_ZONE_ID", "").strip()
    api_token = os.getenv("CLOUDFLARE_API_TOKEN", "").strip()
    if not zone_id or not api_token:
        return {"status": "skipped", "message": "Cloudflare API token or Zone ID not set in .env"}

    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/custom_hostnames"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "hostname": domain,
        "ssl": {
            "method": "http",
            "type": "dv",
            "settings": {
                "http2": "on",
                "min_tls_version": "1.2"
            }
        }
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            data = res.json()
            if data.get("success"):
                return {"status": "provisioned", "data": data.get("result", {})}
            errors = data.get("errors", [])
            for err in errors:
                if err.get("code") == 1406:
                    return {"status": "already_active", "message": "Hostname already registered on Cloudflare"}
            return {"status": "error", "errors": errors}
    except Exception as e:
        logger.warning(f"Cloudflare custom hostname provisioning exception: {e}")
        return {"status": "error", "message": str(e)}



@router.post("/api/generate-portfolio")
async def create_portfolio_preview(resume: TailoredResume, theme: str = "neon_dark"):
    """Generate customizable standalone responsive HTML portfolio."""
    try:
        clean_name = re.sub(r'[^a-zA-Z0-9]', '-', resume.personal_info.full_name.lower()).strip('-')
        slug = clean_name or "developer"
        html_code = generate_portfolio_html(resume, theme=theme, slug=slug)
        PUBLISHED_RESUMES[slug] = resume
        return {"success": True, "html": html_code, "theme": theme, "slug": slug}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Portfolio generation error: {str(e)}")


@router.post("/api/portfolio/sync-preview")
async def sync_portfolio_preview(resume: TailoredResume):
    """Sync candidate resume into memory cache so QR Smart Card & vCard can render immediately."""
    try:
        clean_name = re.sub(r'[^a-zA-Z0-9]', '-', resume.personal_info.full_name.lower()).strip('-')
        slug = clean_name or "developer"
        PUBLISHED_RESUMES[slug] = resume
        return {"success": True, "slug": slug}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/download-portfolio")
async def download_portfolio(
    resume: TailoredResume,
    theme: str = "neon_dark",
    current_user: User = Depends(get_current_user)
):
    """Download standalone index.html portfolio file ready for hosting. Requires authenticated account."""
    try:
        clean_name = re.sub(r'[^a-zA-Z0-9]', '-', resume.personal_info.full_name.lower()).strip('-')
        slug = clean_name or "developer"
        html_code = generate_portfolio_html(resume, theme=theme, slug=slug)
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


@router.post("/api/publish-portfolio")
async def publish_portfolio(
    resume: TailoredResume,
    theme: str = "neon_dark",
    current_user: User = Depends(require_tier("pro"))
):
    """Publish live portfolio to a public URL e.g. /p/malith-sayuranga. Gated to Pro & Elite tiers."""
    try:
        clean_name = re.sub(r'[^a-zA-Z0-9]', '-', resume.personal_info.full_name.lower()).strip('-')
        slug = clean_name or "developer"
        
        html_code = generate_portfolio_html(resume, theme=theme, slug=slug)
        save_published_portfolio(slug, html_code, resume.personal_info.custom_domain)
        PUBLISHED_RESUMES[slug] = resume
        
        live_url = f"/p/{slug}"
        
        return {
            "success": True,
            "slug": slug,
            "live_url": live_url,
            "custom_domain": resume.personal_info.custom_domain,
            "qr_url": f"/api/portfolio/qr/{slug}",
            "vcard_url": f"/api/portfolio/vcard/{slug}",
            "message": f"Portfolio published live at {live_url}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Publish error: {str(e)}")


@router.get("/api/portfolio/qr/{slug}")
async def get_portfolio_qr(
    slug: str,
    request: Request,
    mode: str = "vcard",
    format: str = "svg",
    download: bool = False
):
    """
    Generate dynamic scalable QR code for the portfolio or digital business card.
    - mode='vcard': Direct phone contact card (scans directly into iOS/Android contacts with 1 tap, 100% offline).
    - mode='url': Direct portfolio web link.
    - format='svg': Scalable vector for graphic design & printing.
    - format='png': High-res raster image for phone wallpapers, gallery, and WhatsApp.
    - download=True: Sets Content-Disposition: attachment for direct file download.
    """
    base_url = str(request.base_url).rstrip('/')
    portfolio_url = f"{base_url}/p/{slug}"

    if mode == "vcard":
        if slug in PUBLISHED_RESUMES:
            resume = PUBLISHED_RESUMES[slug]
            qr_data = generate_vcard_content(resume, portfolio_url)
        else:
            candidate_name = slug.replace('-', ' ').title()
            qr_data = f"BEGIN:VCARD\r\nVERSION:3.0\r\nFN:{candidate_name}\r\nURL:{portfolio_url}\r\nNOTE:Verified Candidate Credentials by DreemFolio\r\nEND:VCARD\r\n"
    else:
        qr_data = portfolio_url

    disp = "attachment" if download else "inline"

    if format.lower() == "png":
        png_data = generate_qr_code_png(qr_data)
        return Response(
            content=png_data,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f'{disp}; filename="{slug}-smart-card-qr.png"'
            }
        )
    else:
        svg_data = generate_qr_code_svg(qr_data)
        return Response(
            content=svg_data,
            media_type="image/svg+xml",
            headers={
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f'{disp}; filename="{slug}-smart-card-qr.svg"'
            }
        )


@router.get("/api/portfolio/vcard/{slug}")
async def get_portfolio_vcard(slug: str, request: Request, pin: Optional[str] = Query(None)):
    """
    Generate and download mobile-compatible vCard 3.0 file (.vcf) for instant contact saving.
    Security Gate: If portfolio is PIN-protected, personal phone & email are redacted
    unless verified against the access PIN to prevent scraper harvesting.
    """
    base_url = str(request.base_url).rstrip('/')
    portfolio_url = f"{base_url}/p/{slug}"

    if slug in PUBLISHED_RESUMES:
        resume = PUBLISHED_RESUMES[slug]
        sec = getattr(resume, "security_config", None)
        
        include_private = True
        if sec and sec.is_pin_protected and sec.access_pin:
            expected = sec.access_pin.strip()
            provided = (pin or "").strip()
            if not provided or not hmac.compare_digest(expected.encode("utf-8"), provided.encode("utf-8")):
                include_private = False

        vcard_str = generate_vcard_content(resume, portfolio_url, include_private=include_private)
        clean_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', resume.personal_info.full_name) or slug
    else:
        clean_name = slug.replace('-', ' ').title()
        vcard_str = f"BEGIN:VCARD\r\nVERSION:3.0\r\nFN:{clean_name}\r\nURL:{portfolio_url}\r\nNOTE:Verified Candidate by DreemFolio SaaS\r\nEND:VCARD\r\n"
        clean_filename = slug

    return Response(
        content=vcard_str,
        media_type="text/vcard; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{clean_filename}.vcf"'}
    )


@router.post("/api/portfolio/verify-pin", response_model=VerifyPinResponse)
async def verify_portfolio_pin(req: VerifyPinRequest, request: Request):
    """
    Verify recruiter PIN code against protected portfolio.
    Security: Constant-time comparison, per-IP rate limiting, and 5-minute lockout after 5 failed attempts.
    """
    client_ip = _get_client_ip(request)
    store_key = f"{client_ip}:{req.slug}"
    attempt_info = PIN_ATTEMPT_STORE[store_key]
    now = time.time()

    # Check active lockout
    if now < attempt_info["lockout_until"]:
        cooldown_left = int(attempt_info["lockout_until"] - now)
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed PIN attempts. PIN verification is locked out for {cooldown_left} more seconds."
        )

    if req.slug not in PUBLISHED_RESUMES:
        raise HTTPException(status_code=404, detail="Portfolio not found.")
    resume = PUBLISHED_RESUMES[req.slug]
    sec = resume.security_config
    if not sec or not sec.is_pin_protected:
        return VerifyPinResponse(success=True, message="No PIN required for this portfolio.")
    
    # Constant-time comparison to eliminate timing side-channel attacks
    expected_pin = (sec.access_pin or "").strip()
    provided_pin = (req.pin or "").strip()

    is_correct = bool(expected_pin and hmac.compare_digest(expected_pin.encode("utf-8"), provided_pin.encode("utf-8")))

    if is_correct:
        # Reset failed attempts counter on success
        attempt_info["failed_count"] = 0
        attempt_info["lockout_until"] = 0.0
        return VerifyPinResponse(success=True, message="Access granted.")
    else:
        attempt_info["failed_count"] += 1
        if attempt_info["failed_count"] >= 5:
            attempt_info["lockout_until"] = now + 300  # 5-minute lockout
            attempt_info["failed_count"] = 0
            raise HTTPException(
                status_code=429,
                detail="Too many failed PIN attempts. PIN verification has been locked out for 5 minutes."
            )
        attempts_left = 5 - attempt_info["failed_count"]
        raise HTTPException(
            status_code=403,
            detail=f"Invalid 4-digit security PIN. Access denied. ({attempts_left} attempts remaining before lockout)"
        )


@router.post("/api/domain/verify")
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
    save_custom_domain_mapping(domain_clean, safe_slug)
    
    cf_res = await provision_cloudflare_custom_hostname(domain_clean)
    fallback_target = os.getenv("CLOUDFLARE_FALLBACK_ORIGIN", "cname.dreemfolio.com")

    return {
        "success": True,
        "domain": domain_clean,
        "cloudflare_provisioning": cf_res,
        "dns_records": [
            {
                "type": "CNAME / ALIAS",
                "name": "@" if domain_clean.count(".") == 1 else domain_clean.split(".")[0],
                "target": fallback_target,
                "ttl": "3600",
                "status": "Ready to configure (Zero IP Required)"
            }
        ],
        "ssl_status": "Auto-provisioned Cloudflare / Caddy On-Demand SSL",
        "message": f"Domain {domain_clean} mapped successfully to {req.slug}!"
    }


@router.get("/api/domain/check-allowed")
async def check_domain_allowed(domain: str = Query(...)):
    """
    On-Demand TLS security check endpoint for Caddy or automated SSL reverse proxies.
    Returns HTTP 200 if the domain is authorized to obtain an automated SSL certificate,
    or HTTP 403 to prevent certificate issuance abuse / rate limit exhaustion.
    """
    d = domain.strip().lower().replace("https://", "").replace("http://", "").rstrip('/')
    if not d:
        raise HTTPException(status_code=400, detail="Domain required")

    # 1. Allow our main host and all subdomains
    if d in ["dreemfolio.com", "www.dreemfolio.com"] or d.endswith(".dreemfolio.com"):
        return Response(content="Authorized", status_code=200)

    # 2. Check if any candidate has registered this custom domain
    slug = resolve_custom_domain_slug(d)
    if slug:
        return Response(content="Authorized", status_code=200)

    raise HTTPException(status_code=403, detail="Domain not registered on DreemFolio")


@router.get("/p/{slug}", response_class=HTMLResponse)
async def view_public_portfolio(slug: str):
    """Publicly accessible live candidate portfolio webpage."""
    content = get_published_portfolio(slug)
    if content:
        return HTMLResponse(content=content)
    raise HTTPException(status_code=404, detail="Portfolio not found. Please publish it first from the dashboard.")
