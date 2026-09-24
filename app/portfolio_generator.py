"""
Portfolio Generator Dispatcher & Compatibility Layer.

All individual portfolio theme templates have been modularized into `app/portfolio_templates/`
for easy customization and styling:
- app/portfolio_templates/common.py          -> Shared sanitizers, QR codes, vCard, PIN gate, badges
- app/portfolio_templates/aurora_white.py    -> Scandinavian Minimalist Clean White / Light Studio
- app/portfolio_templates/motion_zenith.py   -> Awwwards Kinetic Motion Studio (Typewriter, 3D Tilt)
- app/portfolio_templates/galaxy_canvas.py   -> Interactive HTML5 Particle Constellation & Counters
- app/portfolio_templates/bento_grid.py      -> Apple / Linear Style Bento Grid Studio
- app/portfolio_templates/split_sidebar.py   -> Executive Split-Pane with Sticky Profile Drawer
- app/portfolio_templates/terminal_dev.py    -> Cyber Hacker / Terminal Developer CLI
- app/portfolio_templates/editorial_swiss.py -> Minimalist Swiss Typographic Editorial
- app/portfolio_templates/neon_glass.py      -> Cosmic Neo-Glassmorphism 3D Glow
"""

from app.portfolio_templates import (
    generate_portfolio_html,
    render_bento_grid,
    render_split_sidebar,
    render_terminal_dev,
    render_editorial_swiss,
    render_neon_glass,
    render_motion_zenith,
    render_galaxy_canvas,
    render_aurora_white,
)

from app.portfolio_templates.common import (
    sanitize_text,
    sanitize_url,
    sanitize_resume_for_portfolio,
    compute_portfolio_hmac,
    generate_qr_code_svg,
    generate_qr_code_png,
    generate_vcard_content,
    render_proof_of_work_section,
    render_pin_gate_overlay,
    render_verification_badge,
    render_viral_portfolio_badge,
    get_social_svg,
    get_social_icon,
    get_font_meta,
    hex_to_rgba,
)

__all__ = [
    "generate_portfolio_html",
    "generate_qr_code_svg",
    "generate_qr_code_png",
    "generate_vcard_content",
    "sanitize_text",
    "sanitize_url",
    "sanitize_resume_for_portfolio",
    "compute_portfolio_hmac",
    "render_proof_of_work_section",
    "render_pin_gate_overlay",
    "render_verification_badge",
    "render_viral_portfolio_badge",
    "get_social_svg",
    "get_social_icon",
    "get_font_meta",
    "hex_to_rgba",
    "render_bento_grid",
    "render_split_sidebar",
    "render_terminal_dev",
    "render_editorial_swiss",
    "render_neon_glass",
    "render_motion_zenith",
    "render_galaxy_canvas",
    "render_aurora_white",
]
