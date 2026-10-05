"""
Authoritative Blog Database and SEO Content Catalog for DreemFolio AI.
Maintains structured blog metadata, publishing dates, author credentials,
categories, target search keywords, and schema markup contexts.
"""

from typing import Dict, Any, List, Optional

BLOG_DATABASE: Dict[str, Dict[str, Any]] = {
    "how-to-write-an-ats-friendly-cv": {
        "slug": "how-to-write-an-ats-friendly-cv",
        "title": "How to Write an ATS-Friendly Resume in 2026",
        "subtitle": "Step-by-step blueprint to pass modern Applicant Tracking Systems (Workday, Greenhouse, Lever) with 95%+ match scores.",
        "description": "Learn step-by-step how to write an ATS-friendly CV that passes Applicant Tracking Systems. Discover formatting rules, keyword optimization, and free ATS checkers.",
        "template": "blogs/ats_cv_guide.html",
        "published_date": "2026-10-05",
        "modified_date": "2026-10-05",
        "author": {
            "name": "DreemFolio AI Career Team",
            "role": "Senior Talent Acquisition & Resume Strategists",
            "avatar": "/static/images/logo.png"
        },
        "reading_time": "7 min read",
        "category": "ATS Resume Guide",
        "badge": "Top Recruiter Pick",
        "priority": "0.9",
        "target_keywords": [
            "ATS friendly CV",
            "pass ATS scanner",
            "free ATS checker",
            "ATS resume format 2026",
            "Applicant Tracking System resume",
            "ATS score check"
        ],
        "og_image": "https://www.dreemfolio.com/static/images/hero_showcase.jpg"
    },
    "top-10-resume-errors-that-cause-rejection": {
        "slug": "top-10-resume-errors-that-cause-rejection",
        "title": "Top 10 Resume Errors That Cause Rejection (And How to Fix Them)",
        "subtitle": "The critical formatting, typography, and keyword mistakes that trigger instant rejection in 2026 recruiting funnels.",
        "description": "Discover the top 10 resume errors that cause instant ATS and recruiter rejection. Learn how to fix formatting traps, missing metrics, and keyword mistakes.",
        "template": "blogs/resume_errors_guide.html",
        "published_date": "2026-10-05",
        "modified_date": "2026-10-05",
        "author": {
            "name": "DreemFolio AI Career Team",
            "role": "Recruitment Operations & Career Mentors",
            "avatar": "/static/images/logo.png"
        },
        "reading_time": "8 min read",
        "category": "Resume Optimization",
        "badge": "Essential Reading",
        "priority": "0.85",
        "target_keywords": [
            "resume formatting mistakes",
            "CV rejection reasons",
            "ATS parsing errors",
            "why resumes get rejected",
            "resume red flags",
            "fix resume errors"
        ],
        "og_image": "https://www.dreemfolio.com/static/images/hero_showcase.jpg"
    },
    "tailor-cv-for-remote-jobs": {
        "slug": "tailor-cv-for-remote-jobs",
        "title": "How to Tailor Your CV for Remote Tech Jobs",
        "subtitle": "Proven tactics to stand out among 1,000+ global applicants for remote software engineer and engineering roles.",
        "description": "Optimize your resume specifically for remote software engineer and tech roles. Highlight async communication, remote tech stacks, and live portfolios.",
        "template": "blogs/remote_cv_guide.html",
        "published_date": "2026-10-05",
        "modified_date": "2026-10-05",
        "author": {
            "name": "DreemFolio AI Career Team",
            "role": "Global Tech Hiring Advisors",
            "avatar": "/static/images/logo.png"
        },
        "reading_time": "6 min read",
        "category": "Remote Tech Jobs",
        "badge": "Tech Special",
        "priority": "0.85",
        "target_keywords": [
            "remote job CV",
            "tech resume template",
            "software engineer ATS resume",
            "remote developer resume",
            "global tech jobs CV",
            "remote work resume tailoring"
        ],
        "og_image": "https://www.dreemfolio.com/static/images/hero_showcase.jpg"
    }
}


def get_all_blog_posts() -> List[Dict[str, Any]]:
    """Return all blog posts sorted by published date (newest first)."""
    posts = list(BLOG_DATABASE.values())
    posts.sort(key=lambda p: p.get("published_date", ""), reverse=True)
    return posts


def get_blog_post(slug: str) -> Optional[Dict[str, Any]]:
    """Retrieve single blog post metadata by slug."""
    return BLOG_DATABASE.get(slug)
