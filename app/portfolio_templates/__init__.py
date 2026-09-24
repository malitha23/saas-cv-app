"""
Portfolio Web Templates Package.
Individual modules for each portfolio theme:
- bento_grid.py       -> Apple / Linear Style Bento Grid Studio
- split_sidebar.py    -> Executive Split-Pane with Sticky Drawer
- terminal_dev.py     -> Cyber Hacker / Terminal Developer CLI
- editorial_swiss.py  -> Minimalist Swiss Typographic Editorial
- neon_glass.py       -> Cosmic Neo-Glassmorphism 3D Glow
- motion_zenith.py    -> Awwwards Kinetic Motion Studio
- galaxy_canvas.py    -> Interactive HTML5 Particle Constellation
- aurora_white.py     -> Scandinavian Minimalist Clean White Studio
- common.py           -> Shared sanitizers, vCard, QR codes, PIN gate, badges
"""

import re
from app.schemas import TailoredResume
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

from app.portfolio_templates.bento_grid import render_bento_grid
from app.portfolio_templates.split_sidebar import render_split_sidebar
from app.portfolio_templates.terminal_dev import render_terminal_dev
from app.portfolio_templates.editorial_swiss import render_editorial_swiss
from app.portfolio_templates.neon_glass import render_neon_glass
from app.portfolio_templates.motion_zenith import render_motion_zenith
from app.portfolio_templates.galaxy_canvas import render_galaxy_canvas
from app.portfolio_templates.aurora_white import render_aurora_white

def generate_portfolio_html(resume: TailoredResume, theme: str = "neon_dark", slug: str = "") -> str:
    """
    Generate clean, modern, and secure HTML5 responsive portfolio.
    Themes:
      - 'aurora_white': Scandinavian Minimalist Clean White / Light Studio
      - 'motion_zenith': Awwwards Kinetic Motion Studio (Typewriter, 3D Card Tilt, Animated Skill Bars)
      - 'galaxy_canvas': Interactive HTML5 Constellation Particle Galaxy & Counters
      - 'bento_grid': Modern Apple / Linear Bento Grid Studio
      - 'split_sidebar': Executive Split-Pane with Sticky Profile Drawer
      - 'terminal_dev': Cyber Hacker / Terminal Developer CLI
      - 'editorial_swiss': Minimalist Swiss Typographic Editorial
      - 'neon_glass': Cosmic Neo-Glassmorphism 3D Glow
    """
    # Sanitize all resume inputs to eliminate Stored XSS
    safe_resume = sanitize_resume_for_portfolio(resume)

    # Active template selection
    selected_theme = theme or safe_resume.portfolio_theme or "bento_grid"
    if selected_theme in ["minimal_light", "light", "white", "snow"]:
        selected_theme = "aurora_white"
    elif selected_theme == "creative_indigo":
        selected_theme = "neon_glass"
    elif selected_theme == "neon_dark":
        selected_theme = "bento_grid"

    # Accent Color validation (block CSS breakout/injection)
    accent_color = safe_resume.portfolio_accent_color or "#6366f1"
    if not re.match(r"^#[0-9a-fA-F]{3,8}$", str(accent_color)):
        accent_color = "#6366f1"
    accent_glow = hex_to_rgba(accent_color, 0.3)

    # Typography / Font validation
    font_name = safe_resume.portfolio_font or "Inter"
    if font_name not in ["JetBrains Mono", "Outfit", "Playfair Display", "Plus Jakarta Sans", "Fira Code", "Inter"]:
        font_name = "Inter"
    font_url, font_family = get_font_meta(font_name)

    # Render layout with sanitized resume
    if selected_theme in ["aurora_white", "white", "light"]:
        layout_html = render_aurora_white(safe_resume, accent_color)
        body_bg = "bg-[#FAFAFC] text-slate-900"
    elif selected_theme == "motion_zenith":
        layout_html = render_motion_zenith(safe_resume, accent_color)
        body_bg = "bg-slate-950 text-slate-100"
    elif selected_theme == "galaxy_canvas":
        layout_html = render_galaxy_canvas(safe_resume, accent_color)
        body_bg = "bg-[#040711] text-slate-100"
    elif selected_theme == "split_sidebar":
        layout_html = render_split_sidebar(safe_resume, accent_color)
        body_bg = "bg-slate-950 text-slate-100"
    elif selected_theme == "terminal_dev":
        layout_html = render_terminal_dev(safe_resume, accent_color)
        body_bg = "bg-[#090D16] text-slate-100"
    elif selected_theme == "editorial_swiss":
        layout_html = render_editorial_swiss(safe_resume, accent_color)
        body_bg = "bg-[#0A0A0A] text-slate-100"
    elif selected_theme == "neon_glass":
        layout_html = render_neon_glass(safe_resume, accent_color)
        body_bg = "bg-slate-950 text-slate-100"
    else:  # Default: bento_grid
        layout_html = render_bento_grid(safe_resume, accent_color)
        body_bg = "bg-slate-950 text-slate-100"

    # Inject Proof-of-Work Section if evidence items exist
    proof_of_work_html = render_proof_of_work_section(safe_resume.proof_of_work, accent_color)
    if proof_of_work_html and "</main>" in layout_html:
        layout_html = layout_html.replace("</main>", proof_of_work_html + "\n</main>", 1)
    elif proof_of_work_html:
        layout_html += proof_of_work_html

    # High-Security PIN Gate & Cryptographic Verification
    clean_slug = slug or re.sub(r"[^a-zA-Z0-9_-]", "-", (safe_resume.personal_info.full_name or "candidate").lower()).strip("-")
    pin_gate_html = render_pin_gate_overlay(safe_resume, clean_slug)
    verification_html = render_verification_badge(safe_resume, clean_slug)
    viral_badge_html = render_viral_portfolio_badge(clean_slug)

    full_name = safe_resume.personal_info.full_name or "Professional Portfolio"
    role_title = safe_resume.target_job_title or "Portfolio"
    summary = safe_resume.professional_summary or ""
    safe_summary = sanitize_text(summary[:160]) if summary else f"{full_name}'s professional portfolio and verified credentials powered by DreemFolio AI."
    og_img = safe_resume.personal_info.avatar_url if (safe_resume.personal_info.avatar_url and not safe_resume.personal_info.avatar_url.startswith("data:")) else "https://www.dreemfolio.com/static/images/hero_showcase.jpg"

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{full_name} — {role_title} | Portfolio</title>
  
  <meta name="description" content="{safe_summary}">
  <meta property="og:site_name" content="DreemFolio AI">
  <meta property="og:type" content="profile">
  <meta property="og:title" content="{full_name} — {role_title} | Portfolio">
  <meta property="og:description" content="{safe_summary}">
  <meta property="og:image" content="{og_img}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{full_name} — {role_title} | Portfolio">
  <meta name="twitter:description" content="{safe_summary}">
  <meta name="twitter:image" content="{og_img}">
  <link rel="icon" type="image/png" href="/static/images/logo.png?v=2">
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{font_url}" rel="stylesheet">
  <script src="https://unpkg.com/lucide@latest"></script>

  <style>
    :root {{
      --accent: {accent_color};
      --accent-glow: {accent_glow};
      --font-family: {font_family};
    }}
    body {{
      font-family: var(--font-family);
    }}
  </style>
</head>
<body class="{body_bg} min-h-screen antialiased selection:bg-[var(--accent)] selection:text-black relative">
  {pin_gate_html}
  {verification_html}
  {layout_html}
  {viral_badge_html}

  <script>
    function hydrateIcons() {{
      if (window.lucide && typeof window.lucide.createIcons === 'function') {{
        window.lucide.createIcons();
      }}
    }}
    document.addEventListener('DOMContentLoaded', hydrateIcons);
    window.addEventListener('load', hydrateIcons);
    setTimeout(hydrateIcons, 50);
    setTimeout(hydrateIcons, 250);
    setTimeout(hydrateIcons, 800);
  </script>
</body>
</html>
"""
