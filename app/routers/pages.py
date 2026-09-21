import os
import json
import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response, BackgroundTasks, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import OnlinePaymentOrder
from app.state import templates
from app.routers.payments import sync_order_status_from_payhere

router = APIRouter(tags=["Pages & Public Views"])

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


@router.get("/api/health")
async def health_check():
    """Health status and API readiness."""
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy",
        "gemini_api_configured": has_gemini_key,
        "engine": "Gemini Flash + ReportLab ATS + Custom Portfolio Engine",
        "version": "1.3.0"
    }


@router.get("/paneladmin", response_class=HTMLResponse)
async def serve_admin_page(request: Request):
    """Serve dedicated, enterprise-hardened standalone Administrator Control Center via obfuscated URL."""
    response = templates.TemplateResponse(request=request, name="admin.html")
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


@router.get("/admin")
async def trap_legacy_admin():
    """Honeypot / bot decoy: Return HTTP 404 on /admin to prevent automated scanner enumeration."""
    raise HTTPException(status_code=404, detail="Not Found")


@router.get("/privacy", response_class=HTMLResponse)
async def serve_privacy_policy(request: Request):
    """Serve official GDPR & CCPA compliant Privacy Policy."""
    return templates.TemplateResponse(request=request, name="legal/privacy.html", context={"active_page": "privacy"})


@router.get("/terms", response_class=HTMLResponse)
async def serve_terms_of_service(request: Request):
    """Serve official Terms of Service & Subscription Agreement."""
    return templates.TemplateResponse(request=request, name="legal/terms.html", context={"active_page": "terms"})


@router.get("/refund", response_class=HTMLResponse)
@router.get("/refund-policy", response_class=HTMLResponse)
async def serve_refund_policy(request: Request):
    """Serve official Refund & Cancellation Policy."""
    return templates.TemplateResponse(request=request, name="legal/refund.html", context={"active_page": "refund"})


@router.get("/security", response_class=HTMLResponse)
async def serve_security_whitepaper(request: Request):
    """Serve official Enterprise Security & Compliance Whitepaper."""
    return templates.TemplateResponse(request=request, name="legal/security.html", context={"active_page": "security"})


@router.get("/contact", response_class=HTMLResponse)
@router.get("/support", response_class=HTMLResponse)
async def serve_contact_page(request: Request):
    """Serve official Contact & Support page with human assistance channels."""
    return templates.TemplateResponse(request=request, name="legal/contact.html", context={"active_page": "contact"})


@router.get("/pricing", response_class=HTMLResponse)
async def serve_pricing_page(request: Request):
    """
    Dedicated, high-converting Pricing route for search engines & direct traffic.
    Serves the landing page with custom SEO metadata and auto-scrolls to #pricing.
    """
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={
            "page_title": "DreemFolio AI Pricing — Fair Country Plans, 7-Day Sprint & Lifetime Access",
            "page_description": "Explore transparent, affordable pricing for DreemFolio AI. 100% ATS score tailoring, cover letters, and live developer portfolios. Special PPP discounts for Sri Lanka.",
            "canonical_url": "https://dreemfolio.com/pricing",
            "auto_scroll": "pricing"
        }
    )


@router.get("/features", response_class=HTMLResponse)
async def serve_features_page(request: Request):
    """
    Dedicated, high-converting Features route for search engines & direct traffic.
    Serves the landing page with custom SEO metadata and auto-scrolls to #features.
    """
    return templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={
            "page_title": "DreemFolio AI Features — 100% ATS Resume Tailor, Cover Letters & Live Web Portfolios",
            "page_description": "Discover how DreemFolio AI tailors resumes to any job description, generates ATS-safe PDFs, builds modern photo CVs, drafts cover letters, and publishes developer portfolios.",
            "canonical_url": "https://dreemfolio.com/features",
            "auto_scroll": "features"
        }
    )


@router.get("/robots.txt", response_class=Response)
async def serve_robots_txt():
    """Serve dynamic, crawler-friendly robots.txt for Google, Bing, and major search engines."""
    content = """User-agent: *
Allow: /
Allow: /app
Allow: /pricing
Allow: /features
Allow: /contact
Allow: /support
Allow: /privacy
Allow: /terms
Allow: /refund
Allow: /refund-policy
Allow: /security
Allow: /static/
Disallow: /api/
Disallow: /admin
Disallow: /portfolio/preview/

# Search Engine Sitemaps
Sitemap: https://dreemfolio.com/sitemap.xml
Host: https://dreemfolio.com
"""
    return Response(content=content, media_type="text/plain")


@router.get("/sitemap.xml", response_class=Response)
async def serve_sitemap_xml():
    """Serve dynamic XML Sitemap complying with sitemaps.org standard."""
    today = datetime.date.today().isoformat()
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://dreemfolio.com/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://dreemfolio.com/pricing</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.95</priority>
  </url>
  <url>
    <loc>https://dreemfolio.com/features</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://dreemfolio.com/app</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://dreemfolio.com/contact</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://dreemfolio.com/security</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.75</priority>
  </url>
  <url>
    <loc>https://dreemfolio.com/privacy</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://dreemfolio.com/terms</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://dreemfolio.com/refund</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
</urlset>"""
    return Response(content=sitemap, media_type="application/xml")


@router.get("/manifest.json")
async def serve_manifest():
    """Serve Web App Manifest for PWA and Mobile SEO."""
    manifest_path = os.path.join(static_dir, "manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    return JSONResponse(content={"name": "DreemFolio AI"})


@router.get("/favicon.ico")
async def serve_favicon():
    """Serve SVG favicon for root icon requests."""
    svg_path = os.path.join(static_dir, "favicon.svg")
    if os.path.exists(svg_path):
        with open(svg_path, "r", encoding="utf-8") as f:
            return Response(content=f.read(), media_type="image/svg+xml")
    return Response(content="", status_code=204)


@router.get("/payment/status", response_class=HTMLResponse)
@router.get("/payment/success", response_class=HTMLResponse)
@router.get("/payment/failed", response_class=HTMLResponse)
async def serve_payment_status(
    request: Request,
    background_tasks: BackgroundTasks,
    order_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Renders the dedicated Payment Status page (Success or Failed with clear reasons).
    Actively synchronizes payment state with PayHere Retrieval API if still pending.
    """
    order = None
    if order_id:
        order = db.scalars(select(OnlinePaymentOrder).where(OnlinePaymentOrder.order_id == order_id)).first()

    # If order is still pending/initiated, verify directly with PayHere Retrieval API
    if order and order.status in ["initiated", "pending"]:
        sync_order_status_from_payhere(order, db, background_tasks)
        db.refresh(order)

    # Determine effective status
    effective_status = (order.status if order else None) or status or "failed"
    if request.url.path.endswith("/success"):
        effective_status = "success"
    elif request.url.path.endswith("/failed") and effective_status == "success":
        effective_status = "failed"

    # Keep URL query in sync with actual real-time database state
    if order and status and status.lower().strip() != effective_status.lower().strip():
        return RedirectResponse(
            url=f"/payment/status?order_id={order.order_id}&status={effective_status}",
            status_code=303
        )

    # Plan title formatting
    plan_names = {
        "sprint": "7-Day Sprint Pass",
        "pro": "Pro Career Plan (30 Days)",
        "elite": "Executive Elite (30 Days)"
    }
    raw_plan = order.target_plan if order else "pro"
    plan_title = plan_names.get(raw_plan.lower(), f"{raw_plan.title()} Plan")

    # Amount formatting
    if order:
        curr_symbol = "Rs. " if order.currency == "LKR" else "$"
        formatted_amount = f"{curr_symbol}{order.amount:,.2f}"
    else:
        formatted_amount = ""

    # Failure reasons in English and Sinhala
    failure_reason_en = ""
    failure_reason_si = ""

    if effective_status == "canceled":
        failure_reason_en = "The transaction was canceled by the user during the PayHere checkout session. No charges were deducted from your card or account."
        failure_reason_si = "PayHere ගෙවීම් පිටුවේදී ඔබ විසින් ගෙවීම අවලංගු කරන ලදී. ඔබගේ ගිණුමෙන් කිසිදු මුදලක් අය වී නොමැත."
    elif effective_status == "amount_tampered":
        failure_reason_en = "Security integrity verification failed: The transaction amount or currency did not match the official order price."
        failure_reason_si = "ආරක්ෂණ පරීක්ෂාව අසාර්ථක විය: ගෙවීමට උත්සාහ කළ මුදල සහ ඇණවුමේ නිල මුදල අතර නොගැලපීමක් පවතී."
    elif effective_status == "pending":
        failure_reason_en = "Your payment was submitted and is awaiting final clearance from your issuing bank or PayHere."
        failure_reason_si = "ඔබගේ ගෙවීම ඉදිරිපත් කර ඇති අතර ඔබගේ බැංකුවේ හෝ PayHere හි අවසන් අනුමැතිය බලාපොරොත්තුවෙන් පවතී."
    else:
        msg = (order.status_message if order and order.status_message else "").strip()
        if msg:
            failure_reason_en = f"Gateway message: {msg}. Please verify your card details, account balance, and e-commerce activation."
        else:
            failure_reason_en = "The payment could not be processed by your bank or the card network. Please check your card balance, expiration, and online transaction permissions."
        failure_reason_si = "ඔබගේ බැංකුව හෝ ගෙවීම් පද්ධතිය මඟින් ගනුදෙනුව අනුමත නොකරන ලදී. කරුණාකර ඔබගේ කාඩ්පතේ ශේෂය සහ Online Payments පහසුකම පරීක්ෂා කරන්න, නැතහොත් Direct Bank Transfer මඟින් ගෙවීම සිදුකරන්න."

    if effective_status == "success":
        page_title = "Payment Successful"
    elif effective_status == "pending":
        page_title = "Payment Processing"
    elif effective_status == "canceled":
        page_title = "Payment Canceled"
    else:
        page_title = "Payment Failed"
    formatted_date = order.created_at.strftime("%b %d, %Y - %I:%M %p") if (order and order.created_at) else datetime.datetime.utcnow().strftime("%b %d, %Y - %I:%M %p")

    return templates.TemplateResponse(
        request=request,
        name="payment_status.html",
        context={
            "order": order,
            "order_id": order_id or "",
            "status": effective_status,
            "plan_title": plan_title,
            "formatted_amount": formatted_amount,
            "failure_reason_en": failure_reason_en,
            "failure_reason_si": failure_reason_si,
            "page_title": page_title,
            "formatted_date": formatted_date
        }
    )


@router.get("/", response_class=HTMLResponse)
async def serve_landing(request: Request):
    """Serve the modern, high-converting Landing Page with OWASP security headers."""
    payment_param = request.query_params.get("payment")
    if payment_param:
        order_id = request.query_params.get("order_id", "")
        return RedirectResponse(url=f"/payment/status?order_id={order_id}&status={payment_param}", status_code=303)
    return templates.TemplateResponse(request=request, name="landing.html")


@router.get("/app", response_class=HTMLResponse)
@router.get("/app/", response_class=HTMLResponse)
@router.get("/builder", response_class=HTMLResponse)
@router.get("/builder/", response_class=HTMLResponse)
@router.get("/workspace", response_class=HTMLResponse)
async def serve_app(request: Request):
    """Serve the complete ATS AI Resume Builder, Editor & Portfolio Studio application."""
    return templates.TemplateResponse(request=request, name="index.html")


@router.get("/reset-password", response_class=HTMLResponse)
@router.get("/reset-password/", response_class=HTMLResponse)
async def serve_reset_password_page(request: Request):
    """Serve the modern password reset page."""
    return templates.TemplateResponse(request=request, name="reset_password.html")


@router.get("/profile", response_class=HTMLResponse)
@router.get("/profile/", response_class=HTMLResponse)
async def serve_profile_page(request: Request):
    """Serve the user profile, billing history & subscription management page."""
    return templates.TemplateResponse(request=request, name="profile.html")

