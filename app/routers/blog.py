import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

from app.state import templates
from app.blog_data import (
    BLOG_DATABASE,
    get_all_blog_posts,
    get_localized_blog_post,
)

logger = logging.getLogger("dreemfolio.blog")

router = APIRouter(tags=["Blog & Career Insights"])

SUPPORTED_LANGUAGES = {"en", "si", "ta"}


@router.get("/blog", response_class=HTMLResponse)
@router.get("/blog/", response_class=HTMLResponse)
@router.get("/blog/si", response_class=HTMLResponse)
@router.get("/blog/si/", response_class=HTMLResponse)
@router.get("/blog/ta", response_class=HTMLResponse)
@router.get("/blog/ta/", response_class=HTMLResponse)
async def render_blog_catalog(request: Request):
    """
    Render the authoritative Blog & Career Knowledge Hub.
    Supports English (/blog), Sinhala (/blog/si), and Tamil (/blog/ta).
    """
    path = request.url.path.strip("/")
    parts = path.split("/")
    lang = "en"
    if len(parts) >= 2 and parts[1] in SUPPORTED_LANGUAGES:
        lang = parts[1]

    posts = get_all_blog_posts(lang=lang)
    categories = sorted(list({p.get("category", "Guides") for p in posts}))
    
    titles = {
        "en": "DreemFolio AI Career & ATS Resume Blog — 2026 Hiring Guides",
        "si": "DreemFolio AI වෘත්තීය සහ ATS CV බ්ලොග් අඩවිය — 2026 මඟපෙන්වීම්",
        "ta": "DreemFolio AI தொழில் & ATS CV வலைப்பதிவு — 2026 வழிகாட்டிகள்"
    }
    descriptions = {
        "en": "Authoritative guides on passing Applicant Tracking Systems (ATS), optimizing tech resumes, avoiding CV rejection errors, and winning remote jobs in 2026.",
        "si": "Applicant Tracking Systems (ATS) හරහා සාර්ථකව CV සමත් කරගන්නා ආකාරය, Tech CV සකස් කිරීම, සහ විදේශීය Remote රැකියා දිනාගැනීමේ සම්පූර්ණ මඟපෙන්වීම්.",
        "ta": "Applicant Tracking Systems (ATS) இல் தேர்ச்சி பெறுதல், தொழில்நுட்ப CV களை மேம்படுத்துதல் மற்றும் சர்வதேச ரிமோட் வேலைகளை வெல்வதற்கான அதிகாரப்பூர்வ வழிகாட்டிகள்."
    }

    canonical = f"https://www.dreemfolio.com/blog/{lang}" if lang != "en" else "https://www.dreemfolio.com/blog"

    return templates.TemplateResponse(
        request=request,
        name="blogs/index.html",
        context={
            "posts": posts,
            "categories": categories,
            "current_lang": lang,
            "active_page": f"blog/{lang}" if lang != "en" else "blog",
            "page_title": titles.get(lang, titles["en"]),
            "page_description": descriptions.get(lang, descriptions["en"]),
            "canonical_url": canonical,
            "en_url": "https://www.dreemfolio.com/blog",
            "si_url": "https://www.dreemfolio.com/blog/si",
            "ta_url": "https://www.dreemfolio.com/blog/ta"
        }
    )


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def render_blog_post_en(slug: str, request: Request):
    """Serve default English blog post."""
    # If slug is accidentally a language code, forward to catalog
    if slug in SUPPORTED_LANGUAGES:
        return await render_blog_catalog(request)
    return await _serve_post(slug=slug, lang="en", request=request)


@router.get("/blog/{lang}/{slug}", response_class=HTMLResponse)
async def render_blog_post_localized(lang: str, slug: str, request: Request):
    """Serve localized blog post (Sinhala /blog/si/{slug} or Tamil /blog/ta/{slug})."""
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(status_code=404, detail="Language code not supported.")
    return await _serve_post(slug=slug, lang=lang, request=request)


async def _serve_post(slug: str, lang: str, request: Request):
    post = get_localized_blog_post(slug, lang=lang)
    if not post:
        raise HTTPException(
            status_code=404,
            detail=f"Blog post '{slug}' was not found. Please visit our blog hub at /blog."
        )

    all_posts = get_all_blog_posts(lang=lang)
    related_posts = [p for p in all_posts if p["slug"] != slug][:3]
    template_file = post.get("template", "blogs/ats_cv_guide.html")
    
    canonical_url = f"https://www.dreemfolio.com/blog/{lang}/{slug}" if lang != "en" else f"https://www.dreemfolio.com/blog/{slug}"

    return templates.TemplateResponse(
        request=request,
        name=template_file,
        context={
            "post": post,
            "slug": slug,
            "current_lang": lang,
            "related_posts": related_posts,
            "active_page": f"blog/{lang}/{slug}" if lang != "en" else f"blog/{slug}",
            "canonical_url": canonical_url,
            "en_url": f"https://www.dreemfolio.com/blog/{slug}",
            "si_url": f"https://www.dreemfolio.com/blog/si/{slug}",
            "ta_url": f"https://www.dreemfolio.com/blog/ta/{slug}"
        }
    )
