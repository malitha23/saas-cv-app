"""
PDF Generator Dispatcher & Compatibility Layer.

All individual template implementations have been modularized into `app/cv_templates/`
for easy customization and maintenance:
- app/cv_templates/common.py            -> Shared styling helpers, colors, fonts, watermark, avatar
- app/cv_templates/ats_templates.py     -> ATS Classic, Modern (Navy), Minimal (Compact)
- app/cv_templates/visual_sidebar.py    -> Visual Sidebar with Photo & Progress Bars
- app/cv_templates/banner_periwinkle.py -> Periwinkle Header Banner Layout
- app/cv_templates/creative_gradient.py -> Indigo Banner / Creative Gradient Layout
- app/cv_templates/emerald_prestige.py  -> Emerald Prestige Executive Layout
- app/cv_templates/tech_noir.py         -> Tech Noir Modern Tech Layout
- app/cv_templates/cover_letter.py      -> AI Cover Letter PDF
"""

from app.cv_templates import (
    generate_resume_pdf,
    generate_cover_letter_pdf,
    _ats_pdf,
    _visual_sidebar_pdf,
    _banner_periwinkle_pdf,
    _creative_gradient_pdf,
    _emerald_prestige_pdf,
    _tech_noir_pdf,
)

from app.cv_templates.common import (
    _add,
    _hex_to_rgb,
    _is_safe_remote_url,
    _load_avatar_image,
    _get_font_names,
    _draw_diagonal_watermark,
    _draw_sidebar_para,
    _draw_skill_progress_bar,
    _sync_resume_social_links,
)

__all__ = [
    "generate_resume_pdf",
    "generate_cover_letter_pdf",
    "_ats_pdf",
    "_visual_sidebar_pdf",
    "_banner_periwinkle_pdf",
    "_creative_gradient_pdf",
    "_emerald_prestige_pdf",
    "_tech_noir_pdf",
    "_add",
    "_hex_to_rgb",
    "_is_safe_remote_url",
    "_load_avatar_image",
    "_get_font_names",
    "_draw_diagonal_watermark",
    "_draw_sidebar_para",
    "_draw_skill_progress_bar",
    "_sync_resume_social_links",
]
