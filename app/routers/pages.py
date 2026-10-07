import os
import json
import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, Response, BackgroundTasks, Query, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.database import get_db
from app.models import OnlinePaymentOrder, UserReview, User
from app.schemas import CreateUserReviewRequest
from app.auth import get_optional_user
from app.reviews_service import get_public_reviews_data, sanitize_review_text
from app.state import templates
from app.routers.payments import sync_order_status_from_payhere
from app.guide_service import get_dynamic_guide_catalog
from app.pricing import _get_country_pricing_dict, get_dynamic_pricing_context
from app.blog_data import BLOG_DATABASE

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
async def serve_terms_of_service(request: Request, db: Session = Depends(get_db)):
    """Serve official Terms of Service & Subscription Agreement."""
    return templates.TemplateResponse(
        request=request,
        name="legal/terms.html",
        context={
            "active_page": "terms",
            "pricing": get_dynamic_pricing_context(db)
        }
    )


@router.get("/refund", response_class=HTMLResponse)
async def serve_refund_policy(request: Request):
    """Serve official Refund & Cancellation Policy."""
    return templates.TemplateResponse(request=request, name="legal/refund.html", context={"active_page": "refund"})


@router.get("/refund-policy")
async def redirect_refund_policy():
    """Canonical 301 redirect for legacy refund policy alias."""
    return RedirectResponse(url="/refund", status_code=301)


@router.get("/security", response_class=HTMLResponse)
async def serve_security_whitepaper(request: Request):
    """Serve official Enterprise Security & Compliance Whitepaper."""
    return templates.TemplateResponse(request=request, name="legal/security.html", context={"active_page": "security"})


@router.get("/contact", response_class=HTMLResponse)
async def serve_contact_page(request: Request):
    """Serve official Contact & Support page with human assistance channels."""
    return templates.TemplateResponse(request=request, name="legal/contact.html", context={"active_page": "contact"})


@router.get("/support")
async def redirect_support():
    """Canonical 301 redirect for legacy support alias."""
    return RedirectResponse(url="/contact", status_code=301)


@router.get("/guide", response_class=HTMLResponse)
async def serve_feature_guide_page(
    request: Request,
    country: Optional[str] = Query("LK"),
    db: Session = Depends(get_db)
):
    """
    Dedicated, dynamic Feature & Quota Support Guide (Google Support Docs style).
    Binds live DB quotas and subscription plans with zero hardcoding.
    """
    country_code = (country or "LK").upper()
    guide_data = get_dynamic_guide_catalog(db, country_code=country_code)
    all_country_pricing = _get_country_pricing_dict(db)

    return templates.TemplateResponse(
        request=request,
        name="guide.html",
        context={
            "guide": guide_data,
            "all_country_pricing": all_country_pricing,
            "active_country": country_code,
            "active_page": "guide",
            "page_title": "DreemFolio AI Guide — Features, Quotas & Support",
            "page_description": "User guide for DreemFolio AI resume builder, cover letters, and live portfolios. Detailed breakdown of Free, Pro, and Elite subscription plan quotas.",
            "canonical_url": "https://www.dreemfolio.com/guide"
        }
    )


@router.get("/support/guide")
async def redirect_support_guide():
    """Canonical 301 redirect for legacy guide alias."""
    return RedirectResponse(url="/guide", status_code=301)


@router.get("/api/guide/data")
async def get_guide_api_data(
    country: Optional[str] = Query("LK"),
    db: Session = Depends(get_db)
):
    """API returning the dynamic guide catalog in JSON format for client-side filtering."""
    country_code = (country or "LK").upper()
    return get_dynamic_guide_catalog(db, country_code=country_code)


@router.get("/pricing")
async def serve_pricing_page():
    """Canonical 301 redirect to pricing section on authoritative homepage."""
    return RedirectResponse(url="/#pricing", status_code=301)


@router.get("/features")
async def serve_features_page():
    """Canonical 301 redirect to features section on authoritative homepage."""
    return RedirectResponse(url="/#features", status_code=301)


@router.get("/robots.txt", response_class=Response)
async def serve_robots_txt():
    """Serve dynamic, crawler-friendly robots.txt for Google, Bing, and major AI search engines."""
    content = """User-agent: *
Allow: /
Allow: /ai-resume-builder
Allow: /blog
Allow: /blog/
Allow: /app
Allow: /guide
Allow: /contact
Allow: /privacy
Allow: /terms
Allow: /refund
Allow: /security
Allow: /llms.txt
Allow: /static/
Disallow: /api/
Disallow: /admin
Disallow: /paneladmin
Disallow: /portfolio/preview/

# AI Search & Training Crawlers (Welcome ChatGPT, Perplexity, Claude & Gemini)
User-agent: GPTBot
Allow: /
Allow: /blog
Allow: /llms.txt

User-agent: OAI-SearchBot
Allow: /
Allow: /blog
Allow: /llms.txt

User-agent: PerplexityBot
Allow: /
Allow: /blog
Allow: /llms.txt

User-agent: ClaudeBot
Allow: /
Allow: /blog
Allow: /llms.txt

User-agent: Google-Extended
Allow: /
Allow: /blog
Allow: /llms.txt

User-agent: Applebot-Extended
Allow: /
Allow: /blog
Allow: /llms.txt

# Search Engine Sitemaps & LLM Context
Sitemap: https://www.dreemfolio.com/sitemap.xml
Host: www.dreemfolio.com
"""
    return Response(content=content, media_type="text/plain")


@router.get("/llms.txt", response_class=Response)
async def serve_llms_txt():
    """Serve LLM discovery standard specification for AI search engines."""
    llms_path = os.path.join(static_dir, "llms.txt")
    if os.path.exists(llms_path):
        with open(llms_path, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        content = "# DreemFolio AI\n\n> Free AI Resume Builder, ATS Optimizer & Career Portfolio Studio.\n"
    return Response(content=content, media_type="text/plain; charset=utf-8")



@router.get("/sitemap.xml", response_class=Response)
async def serve_sitemap_xml():
    """Serve dynamic XML Sitemap complying with sitemaps.org standard with auto-updating blog entries."""
    today = datetime.date.today().isoformat()
    static_urls = [
        ("https://www.dreemfolio.com/", today, "daily", "1.0"),
        ("https://www.dreemfolio.com/ai-resume-builder", today, "daily", "0.95"),
        ("https://www.dreemfolio.com/app", today, "daily", "0.95"),
        ("https://www.dreemfolio.com/blog", today, "daily", "0.90"),
        ("https://www.dreemfolio.com/blog/si", today, "daily", "0.90"),
        ("https://www.dreemfolio.com/blog/ta", today, "daily", "0.90"),
        ("https://www.dreemfolio.com/guide", today, "weekly", "0.85"),
        ("https://www.dreemfolio.com/contact", today, "monthly", "0.80"),
        ("https://www.dreemfolio.com/security", today, "monthly", "0.75"),
        ("https://www.dreemfolio.com/privacy", today, "monthly", "0.70"),
        ("https://www.dreemfolio.com/terms", today, "monthly", "0.70"),
        ("https://www.dreemfolio.com/refund", today, "monthly", "0.60"),
    ]
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<?xml-stylesheet type="text/xsl" href="/sitemap.xsl"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # 1. Primary Static Pages
    for loc, lastmod, freq, priority in static_urls:
        xml_content += f'  <url>\n    <loc>{loc}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>{freq}</changefreq>\n    <priority>{priority}</priority>\n  </url>\n'
    
    # 2. Auto Loop All Dynamic Blog Posts (en, si, ta) from BLOG_DATABASE
    for slug, data in BLOG_DATABASE.items():
        lastmod = data.get("published_date") or today
        priority = data.get("priority", "0.85")
        # English (Default)
        xml_content += f'  <url>\n    <loc>https://www.dreemfolio.com/blog/{slug}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>{priority}</priority>\n  </url>\n'
        # Sinhala Localization
        xml_content += f'  <url>\n    <loc>https://www.dreemfolio.com/blog/si/{slug}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>{priority}</priority>\n  </url>\n'
        # Tamil Localization
        xml_content += f'  <url>\n    <loc>https://www.dreemfolio.com/blog/ta/{slug}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>weekly</changefreq>\n    <priority>{priority}</priority>\n  </url>\n'
    
    xml_content += '</urlset>'
    response = Response(content=xml_content, media_type="application/xml")
    response.headers["Cache-Control"] = "public, max-age=300, s-maxage=300, must-revalidate"
    return response


@router.get("/sitemap.xsl", response_class=Response)
async def serve_sitemap_xsl():
    """Serve modern, branded XSLT stylesheet for human-friendly viewing of sitemap.xml in web browsers."""
    xsl_content = '''<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="2.0" 
                xmlns:html="http://www.w3.org/TR/REC-html40"
                xmlns:sitemap="http://www.sitemaps.org/schemas/sitemap/0.9"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="html" version="1.0" encoding="UTF-8" indent="yes"/>
  <xsl:template match="/">
    <html xmlns="http://www.w3.org/1999/xhtml" lang="en">
      <head>
        <title>XML Sitemap | DreemFolio AI</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f1f5f9; padding: 2rem 1rem; margin: 0; }
          .container { max-width: 1060px; margin: 0 auto; background: #0f172a; border: 1px solid #1e293b; border-radius: 20px; padding: 2rem; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.5); }
          .badge { display: inline-flex; align-items: center; gap: 0.35rem; background: rgba(99,102,241,0.15); color: #a5b4fc; border: 1px solid rgba(99,102,241,0.3); border-radius: 9999px; padding: 0.3rem 0.85rem; font-size: 0.75rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.75rem; }
          h1 { font-size: 1.65rem; font-weight: 800; margin: 0 0 0.5rem 0; color: #fff; letter-spacing: -0.025em; }
          p { color: #94a3b8; font-size: 0.875rem; line-height: 1.5; margin-top: 0; margin-bottom: 1.5rem; }
          .stats { display: flex; gap: 1.5rem; padding: 1rem 1.25rem; background: #020617; border: 1px solid #1e293b; border-radius: 12px; margin-bottom: 1.5rem; font-size: 0.8125rem; color: #cbd5e1; }
          .stats strong { color: #38bdf8; font-family: monospace; font-size: 1rem; }
          table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
          th { text-align: left; padding: 0.85rem 1rem; background: #1e293b; color: #94a3b8; font-weight: 700; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.05em; border-bottom: 1px solid #334155; }
          td { padding: 0.75rem 1rem; border-bottom: 1px solid #1e293b; word-break: break-all; }
          tr:hover td { background: rgba(99,102,241,0.06); }
          a { color: #818cf8; text-decoration: none; font-weight: 500; }
          a:hover { text-decoration: underline; color: #c7d2fe; }
          .priority { font-family: monospace; font-weight: 700; color: #34d399; }
          .changefreq { font-family: monospace; color: #cbd5e1; font-size: 0.75rem; }
          .date { color: #64748b; font-family: monospace; font-size: 0.75rem; }
        </style>
      </head>
      <body>
        <div class="container">
          <span class="badge">&#9889; Search Engine Discovery Index</span>
          <h1>DreemFolio AI &bull; XML Sitemap</h1>
          <p>This dynamic XML sitemap is maintained automatically for search engines (Google, Bing, Perplexity, GPTBot). It indexes all public landing pages, career tools, and localized ATS knowledge posts.</p>
          <div class="stats">
            <div>Total Indexed URLs: <strong><xsl:value-of select="count(sitemap:urlset/sitemap:url)"/></strong></div>
            <div>Encoding: <strong>UTF-8</strong></div>
            <div>Standard: <strong>Sitemaps.org 0.9</strong></div>
          </div>
          <table>
            <thead>
              <tr>
                <th style="width: 54%;">Page URL</th>
                <th style="width: 14%;">Priority</th>
                <th style="width: 16%;">Change Frequency</th>
                <th style="width: 16%;">Last Updated</th>
              </tr>
            </thead>
            <tbody>
              <xsl:for-each select="sitemap:urlset/sitemap:url">
                <tr>
                  <td>
                    <xsl:variable name="itemURL">
                      <xsl:value-of select="sitemap:loc"/>
                    </xsl:variable>
                    <a href="{$itemURL}"><xsl:value-of select="sitemap:loc"/></a>
                  </td>
                  <td class="priority"><xsl:value-of select="sitemap:priority"/></td>
                  <td class="changefreq"><xsl:value-of select="sitemap:changefreq"/></td>
                  <td class="date"><xsl:value-of select="sitemap:lastmod"/></td>
                </tr>
              </xsl:for-each>
            </tbody>
          </table>
        </div>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>'''
    return Response(content=xsl_content, media_type="application/xml")


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

    # If order is canceled from query and still initiated, mark it canceled immediately
    if order and order.status in ["initiated", "pending"] and (status or "").lower() == "canceled":
        order.status = "canceled"
        order.status_message = "Canceled by candidate during checkout."
        db.commit()
        db.refresh(order)
    elif order and order.status in ["initiated", "pending"]:
        sync_order_status_from_payhere(order, db, background_tasks)
        db.refresh(order)
        # If still in initiated state after PayHere sync, candidate closed/backed out of the gateway without paying
        if order.status == "initiated":
            order.status = "canceled"
            order.status_message = "Checkout session was closed or canceled before payment completion."
            db.commit()
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

    if effective_status in ["canceled", "incomplete"]:
        failure_reason_en = "The checkout session was closed or canceled before payment was completed. No charges were deducted from your card or account. You can safely try again or choose another payment option."
        failure_reason_si = "ගෙවීම සම්පූර්ණ කිරීමට පෙර Checkout සැසිය අවසන් කර හෝ අවලංගු කර ඇත. ඔබගේ කාඩ්පතෙන් හෝ බැංකු ගිණුමෙන් කිසිදු මුදලක් අය වී නොමැත. ඔබට නැවත පහසුවෙන්ම උත්සාහ කළ හැක."
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
    elif effective_status in ["canceled", "incomplete"]:
        page_title = "Checkout Incomplete"
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


@router.get("/api/reviews/public")
async def get_public_reviews(db: Session = Depends(get_db)):
    """Public reviews API returning verified candidate ratings and reviews for client-side rendering."""
    return get_public_reviews_data(db)


@router.post("/api/reviews")
async def submit_user_review(
    req: CreateUserReviewRequest,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Allow candidates to submit feedback & star ratings at the end of CV tailoring or download.
    Includes XSS sanitization, length bounds, and automated approval for 4-5 star ratings.
    """
    clean_name = sanitize_review_text(req.reviewer_name or "", 100).strip() or "Candidate"
    clean_role = sanitize_review_text(req.reviewer_role or "", 100).strip() or "Software Engineer"
    clean_company = sanitize_review_text(req.reviewer_company or "", 100).strip()
    raw_text = sanitize_review_text(req.review_text or "", 1500).strip()
    rating = max(1, min(5, req.rating or 5))

    # Auto-fallback if feedback is empty so review text is optional
    if not raw_text:
        default_feedback = {
            5: "Outstanding experience! The AI resume builder and ATS checker worked seamlessly.",
            4: "Great experience tailoring my resume with DreemFolio AI. Highly recommended!",
            3: "Good tool with helpful resume formatting and keyword suggestions.",
            2: "Fair experience, looking forward to more features and updates.",
            1: "Feedback submitted to help improve the platform."
        }
        clean_text = default_feedback.get(rating, "Great experience with DreemFolio AI.")
    else:
        clean_text = raw_text

    # High satisfaction reviews (4-5 stars) auto-approved for landing page showcase
    is_approved = rating >= 4

    user_id = current_user.id if current_user else None
    avatar = current_user.avatar_url if (current_user and current_user.avatar_url) else req.avatar_url

    review = UserReview(
        user_id=user_id,
        reviewer_name=clean_name,
        reviewer_role=clean_role,
        reviewer_company=clean_company or None,
        rating=rating,
        review_text=clean_text,
        avatar_url=avatar,
        is_approved=is_approved,
        is_featured=is_approved,
        source="candidate_feedback",
        created_at=datetime.datetime.utcnow(),
        updated_at=datetime.datetime.utcnow()
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return {
        "success": True,
        "id": review.id,
        "is_approved": is_approved,
        "message": "Thank you for your valuable feedback! Your review helps inspire and guide other candidates."
    }


@router.get("/", response_class=HTMLResponse)
async def serve_landing(request: Request, db: Session = Depends(get_db)):
    """Serve the modern, high-converting Landing Page with OWASP security headers and verified social reviews."""
    payment_param = request.query_params.get("payment")
    if payment_param:
        order_id = request.query_params.get("order_id", "")
        return RedirectResponse(url=f"/payment/status?order_id={order_id}&status={payment_param}", status_code=303)

    reviews_data = get_public_reviews_data(db)

    response = templates.TemplateResponse(
        request=request,
        name="landing.html",
        context={
            "reviews": reviews_data["reviews"],
            "average_rating": reviews_data["average_rating"],
            "total_reviews": reviews_data["total_reviews"],
            "pricing": get_dynamic_pricing_context(db),
            "demo_video_url": "https://youtu.be/z1SQa7D1YPs",
            "active_page": "home"
        }
    )
    ref_param = request.query_params.get("ref")
    if ref_param and ref_param.strip():
        response.set_cookie(
            key="dreemfolio_ref",
            value=ref_param.strip(),
            max_age=30 * 24 * 3600,  # 30-day affiliate attribution window
            httponly=False,
            samesite="lax",
            path="/"
        )
    return response


@router.get("/ai-resume-builder", response_class=HTMLResponse)
@router.get("/ai-resume-builder/", response_class=HTMLResponse)
async def serve_ai_resume_builder(request: Request, db: Session = Depends(get_db)):
    """Serve the high-converting, authoritative AI Resume Builder SEO Money Page."""
    response = templates.TemplateResponse(
        request=request,
        name="ai_resume_builder.html",
        context={"pricing": get_dynamic_pricing_context(db)}
    )
    ref_param = request.query_params.get("ref")
    if ref_param and ref_param.strip():
        response.set_cookie(
            key="dreemfolio_ref",
            value=ref_param.strip(),
            max_age=30 * 24 * 3600,  # 30-day affiliate attribution window
            httponly=False,
            samesite="lax",
            path="/"
        )
    return response


@router.get("/app", response_class=HTMLResponse)
@router.get("/app/", response_class=HTMLResponse)
async def serve_app(request: Request, db: Session = Depends(get_db)):
    """Serve the complete ATS AI Resume Builder, Editor & Portfolio Studio application."""
    response = templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"pricing": get_dynamic_pricing_context(db)}
    )
    ref_param = request.query_params.get("ref")
    if ref_param and ref_param.strip():
        response.set_cookie(
            key="dreemfolio_ref",
            value=ref_param.strip(),
            max_age=30 * 24 * 3600,  # 30-day affiliate attribution window
            httponly=False,
            samesite="lax",
            path="/"
        )
    return response


@router.get("/builder")
@router.get("/builder/")
@router.get("/workspace")
@router.get("/workspace/")
async def redirect_legacy_app_routes():
    """Canonical 301 redirect for legacy app workspace routes."""
    return RedirectResponse(url="/app", status_code=301)


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

