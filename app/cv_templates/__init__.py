"""
CV & Cover Letter Templates Package.
Provides individual modules for each template format:
- ats_templates.py       -> Classic, Modern (Navy), Minimal (Compact)
- visual_sidebar.py      -> Sidebar Photo & Progress Bars
- banner_periwinkle.py   -> Periwinkle Banner
- creative_gradient.py   -> Indigo Banner / Creative Gradient
- emerald_prestige.py    -> Emerald Prestige Executive
- tech_noir.py           -> Tech Noir Modern Tech
- cover_letter.py        -> Professional Cover Letter
- common.py              -> Shared styling helpers, colors, fonts, watermark
"""

from app.schemas import TailoredResume
from app.cv_templates.common import _sync_resume_social_links
from app.cv_templates.ats_templates import _ats_pdf
from app.cv_templates.visual_sidebar import _visual_sidebar_pdf
from app.cv_templates.banner_periwinkle import _banner_periwinkle_pdf
from app.cv_templates.creative_gradient import _creative_gradient_pdf
from app.cv_templates.emerald_prestige import _emerald_prestige_pdf
from app.cv_templates.tech_noir import _tech_noir_pdf
from app.cv_templates.cover_letter import generate_cover_letter_pdf


def generate_resume_pdf(resume: TailoredResume) -> bytes:
    """Public entry point: dispatches resume to the selected template style."""
    _sync_resume_social_links(resume)
    style = resume.template_style or "classic"
    if style == "visual_sidebar":
        return _visual_sidebar_pdf(resume)
    elif style == "banner_periwinkle":
        return _banner_periwinkle_pdf(resume)
    elif style == "creative_gradient":
        return _creative_gradient_pdf(resume)
    elif style == "emerald_prestige":
        return _emerald_prestige_pdf(resume)
    elif style == "tech_noir":
        return _tech_noir_pdf(resume)
    return _ats_pdf(resume, style)


__all__ = [
    "generate_resume_pdf",
    "generate_cover_letter_pdf",
    "_ats_pdf",
    "_visual_sidebar_pdf",
    "_banner_periwinkle_pdf",
    "_creative_gradient_pdf",
    "_emerald_prestige_pdf",
    "_tech_noir_pdf",
]
