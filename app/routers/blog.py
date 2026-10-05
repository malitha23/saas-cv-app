import logging
from typing import Optional
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

from app.state import templates
from app.blog_data import BLOG_DATABASE, get_all_blog_posts, get_blog_post

logger = logging.getLogger("dreemfolio.blog")

router = APIRouter(tags=["Blog & Career Insights"])


@router.get("/blog", response_class=HTMLResponse)
@router.get("/blog/", response_class=HTMLResponse)
async def render_blog_catalog(request: Request):
    """
    Render the authoritative Blog & Career Knowledge Hub.
    Lists all SEO articles, recruitment guides, and ATS optimization benchmarks.
    """
    posts = get_all_blog_posts()
    categories = sorted(list({p.get("category", "Guides") for p in posts}))
    
    return templates.TemplateResponse(
        request=request,
        name="blogs/index.html",
        context={
            "posts": posts,
            "categories": categories,
            "active_page": "blog",
            "page_title": "DreemFolio AI Career & ATS Resume Blog — 2026 Hiring Guides",
            "page_description": "Authoritative guides on passing Applicant Tracking Systems (ATS), optimizing tech resumes, avoiding CV rejection errors, and winning remote jobs in 2026.",
            "canonical_url": "https://www.dreemfolio.com/blog"
        }
    )


@router.get("/blog/{slug}", response_class=HTMLResponse)
async def render_blog_post(slug: str, request: Request):
    """
    Render individual SEO-optimized blog article dynamically from BLOG_DATABASE.
    Injects Open Graph, Twitter Cards, Schema.org JSON-LD, and high-converting CTAs.
    """
    post = get_blog_post(slug)
    if not post:
        raise HTTPException(
            status_code=404,
            detail=f"Blog post '{slug}' was not found. Please visit our blog hub at /blog."
        )

    # Collect other posts for Related Articles carousel/grid
    all_posts = get_all_blog_posts()
    related_posts = [p for p in all_posts if p["slug"] != slug][:3]

    template_file = post.get("template", "blogs/ats_cv_guide.html")
    
    return templates.TemplateResponse(
        request=request,
        name=template_file,
        context={
            "post": post,
            "slug": slug,
            "related_posts": related_posts,
            "active_page": f"blog/{slug}",
            "canonical_url": f"https://www.dreemfolio.com/blog/{slug}"
        }
    )
