import re
import html
import json
from typing import Dict, Any, List, Optional
from app.schemas import TailoredResume, SocialLink


def sanitize_text(val: Any) -> str:
    """Safely escape HTML special characters (&, <, >, \", ') to prevent Stored XSS."""
    if val is None:
        return ""
    return html.escape(str(val), quote=True)


def sanitize_url(url: Optional[str], allow_data_image: bool = False) -> str:
    """
    Sanitize URLs for href and src attributes.
    Strictly prevents javascript:, vbscript:, file:, blob:, and malformed protocol attacks.
    """
    if not url or not isinstance(url, str):
        return ""
    cleaned = url.strip()
    lower = cleaned.lower()

    # Block dangerous schemes
    if any(lower.startswith(bad) for bad in ("javascript:", "vbscript:", "file:", "blob:")):
        return "#"

    if allow_data_image and lower.startswith("data:image/"):
        # Ensure it is a valid image mime type and no scripts embedded
        if any(mime in lower for mime in ("png", "jpeg", "jpg", "webp", "gif")):
            return cleaned
        return ""

    if cleaned.startswith(("#", "/", "mailto:", "tel:")):
        return html.escape(cleaned, quote=True)

    if cleaned.startswith(("http://", "https://")):
        return html.escape(cleaned, quote=True)

    # If it's a domain/handle without scheme, format safely as https://
    if "." in cleaned and not ":" in cleaned.split("/")[0]:
        return html.escape(f"https://{cleaned}", quote=True)

    return "#"


def sanitize_resume_for_portfolio(resume: TailoredResume) -> TailoredResume:
    """Recursively clone and sanitize all resume fields to eliminate Stored XSS across all portfolio themes."""
    res = resume.model_copy(deep=True)

    if res.personal_info:
        info = res.personal_info
        info.full_name = sanitize_text(info.full_name)
        info.email = sanitize_text(info.email)
        info.phone = sanitize_text(info.phone)
        info.location = sanitize_text(info.location)
        info.linkedin = sanitize_url(info.linkedin)
        info.portfolio = sanitize_url(info.portfolio)
        info.github = sanitize_url(info.github)
        info.avatar_url = sanitize_url(info.avatar_url, allow_data_image=True)
        info.hero_headline = sanitize_text(info.hero_headline)
        info.availability_badge = sanitize_text(info.availability_badge)
        info.custom_domain = sanitize_text(info.custom_domain)

        # Ensure direct fields (linkedin, github, portfolio) are synced into social_links if not already present
        existing_names = {sl.name.lower() for sl in info.social_links}
        synced_social_links = list(info.social_links)
        if info.linkedin and not any("linkedin" in n for n in existing_names):
            synced_social_links.append(SocialLink(name="LinkedIn", url=info.linkedin, icon="linkedin", enabled=True))
        if info.github and not any("github" in n for n in existing_names):
            synced_social_links.append(SocialLink(name="GitHub", url=info.github, icon="github", enabled=True))
        if info.portfolio and not any("portfolio" in n or "website" in n for n in existing_names):
            synced_social_links.append(SocialLink(name="Portfolio", url=info.portfolio, icon="globe", enabled=True))

        safe_links = []
        for sl in synced_social_links:
            safe_links.append(SocialLink(
                name=sanitize_text(sl.name),
                url=sanitize_url(sl.url),
                icon=sanitize_text(sl.icon),
                enabled=sl.enabled
            ))
        info.social_links = safe_links

    res.target_job_title = sanitize_text(res.target_job_title)
    res.professional_summary = sanitize_text(res.professional_summary)
    res.portfolio_cta_text = sanitize_text(res.portfolio_cta_text)
    res.portfolio_cta_url = sanitize_url(res.portfolio_cta_url)

    # Projects
    safe_projects = []
    for p in res.projects:
        p_copy = p.model_copy(deep=True)
        p_copy.name = sanitize_text(p_copy.name)
        p_copy.link = sanitize_url(p_copy.link)
        p_copy.demo_url = sanitize_url(p_copy.demo_url)
        p_copy.technologies = [sanitize_text(t) for t in p_copy.technologies]
        p_copy.description_bullets = [sanitize_text(b) for b in p_copy.description_bullets]
        safe_projects.append(p_copy)
    res.projects = safe_projects

    # Work experience
    safe_exp = []
    for exp in res.work_experience:
        e_copy = exp.model_copy(deep=True)
        e_copy.job_title = sanitize_text(e_copy.job_title)
        e_copy.company = sanitize_text(e_copy.company)
        e_copy.location = sanitize_text(e_copy.location)
        e_copy.start_date = sanitize_text(e_copy.start_date)
        e_copy.end_date = sanitize_text(e_copy.end_date)
        e_copy.bullet_points = [sanitize_text(b) for b in e_copy.bullet_points]
        safe_exp.append(e_copy)
    res.work_experience = safe_exp

    # Education
    safe_edu = []
    for edu in res.education:
        ed_copy = edu.model_copy(deep=True)
        ed_copy.degree = sanitize_text(ed_copy.degree)
        ed_copy.institution = sanitize_text(ed_copy.institution)
        ed_copy.location = sanitize_text(ed_copy.location)
        ed_copy.graduation_year = sanitize_text(ed_copy.graduation_year)
        ed_copy.details = sanitize_text(ed_copy.details)
        safe_edu.append(ed_copy)
    res.education = safe_edu

    # Skill Categories
    safe_skills = []
    for cat in getattr(res, "skill_categories", []):
        cat_copy = cat.model_copy(deep=True)
        cat_copy.category_name = sanitize_text(cat_copy.category_name)
        cat_copy.skills = [sanitize_text(s) for s in cat_copy.skills]
        safe_skills.append(cat_copy)
    res.skill_categories = safe_skills

    # Certifications
    safe_certs = []
    for cert in res.certifications:
        c_copy = cert.model_copy(deep=True)
        c_copy.name = sanitize_text(c_copy.name)
        c_copy.issuer = sanitize_text(c_copy.issuer)
        c_copy.year = sanitize_text(c_copy.year)
        safe_certs.append(c_copy)
    res.certifications = safe_certs

    return res



def get_social_svg(name: str, icon: str = "", css_class: str = "w-4 h-4") -> str:
    """Return inline SVG for social platforms (ensures GitHub, LinkedIn, Twitter, Email etc. always render 100%)."""
    n = (name or "").lower()
    i = (icon or "").lower()
    
    if "github" in n or "github" in i:
        return f'<svg class="{css_class}" fill="currentColor" viewBox="0 0 24 24"><path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>'
    
    if "linkedin" in n or "linkedin" in i:
        return f'<svg class="{css_class}" fill="currentColor" viewBox="0 0 24 24"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9v8.37H9.2V10.9H6.46M7.83 6.64a1.65 1.65 0 1 0 0 3.3 1.65 1.65 0 0 0 0-3.3z"/></svg>'
    
    if "twitter" in n or "x.com" in n or "twitter" in i:
        return f'<svg class="{css_class}" fill="currentColor" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>'
    
    if "mail" in n or "email" in n or "mail" in i:
        return f'<svg class="{css_class}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>'
    
    if "youtube" in n or "youtube" in i:
        return f'<svg class="{css_class}" fill="currentColor" viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>'
    
    if "instagram" in n or "instagram" in i:
        return f'<svg class="{css_class}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="20" x="2" y="2" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" x2="17.51" y1="6.5" y2="6.5"/></svg>'
    
    if "whatsapp" in n or "chat" in n or "whatsapp" in i:
        return f'<svg class="{css_class}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>'
    
    if "calendly" in n or "calendar" in n or "book" in n:
        return f'<svg class="{css_class}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>'

    # Default Globe
    return f'<svg class="{css_class}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>'


def get_social_icon(name: str, icon: str = "") -> str:
    """Map social platform name or icon to Lucide icon identifier (fallback)."""
    if icon:
        return icon
    n = name.lower()
    if "github" in n:
        return "github"
    if "linkedin" in n:
        return "linkedin"
    if "twitter" in n or "x.com" in n:
        return "twitter"
    if "instagram" in n:
        return "instagram"
    if "youtube" in n:
        return "youtube"
    if "mail" in n or "email" in n:
        return "mail"
    if "calendly" in n or "calendar" in n or "book" in n:
        return "calendar"
    if "whatsapp" in n or "chat" in n:
        return "message-circle"
    if "gitlab" in n:
        return "git-branch"
    if "medium" in n or "blog" in n:
        return "book-open"
    return "globe"


def get_font_meta(font_name: str) -> tuple[str, str]:
    """Return Google Font link URL and CSS font-family string."""
    fonts = {
        "JetBrains Mono": (
            "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700;800&display=swap",
            "'JetBrains Mono', monospace",
        ),
        "Outfit": (
            "https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap",
            "'Outfit', sans-serif",
        ),
        "Playfair Display": (
            "https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;0,900;1,400&family=Inter:wght@400;500;600&display=swap",
            "'Playfair Display', serif",
        ),
        "Plus Jakarta Sans": (
            "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap",
            "'Plus Jakarta Sans', sans-serif",
        ),
        "Fira Code": (
            "https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&display=swap",
            "'Fira Code', monospace",
        ),
        "Inter": (
            "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap",
            "'Inter', sans-serif",
        ),
    }
    return fonts.get(font_name, fonts["Inter"])


def hex_to_rgba(hex_code: str, alpha: float = 1.0) -> str:
    """Convert hex color to rgba string."""
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join([c * 2 for c in hex_code])
    if len(hex_code) != 6:
        return f"rgba(99, 102, 241, {alpha})"
    r = int(hex_code[0:2], 16)
    g = int(hex_code[2:4], 16)
    b = int(hex_code[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


# ─────────────────────────────────────────────────────────────────────────────
# 1. BENTO GRID STUDIO TEMPLATE (Apple / Linear Modern Modular Layout)
# ─────────────────────────────────────────────────────────────────────────────
def render_bento_grid(resume: TailoredResume, accent: str) -> str:
    info = resume.personal_info
    full_name = info.full_name or "Candidate Name"
    role_title = resume.target_job_title or "Software Engineer"
    summary = resume.professional_summary or ""
    avatar_url = info.avatar_url or ""
    badge_text = info.availability_badge or "Available for High-Impact Roles"
    cta_text = resume.portfolio_cta_text or "Get in Touch"
    cta_url = resume.portfolio_cta_url or (
        f"mailto:{info.email}" if info.email else "#contact"
    )

    # Avatar
    if avatar_url:
        avatar_elem = f'<img src="{avatar_url}" alt="{full_name}" class="w-24 h-24 sm:w-28 sm:h-28 rounded-2xl object-cover ring-2 ring-[var(--accent)] shadow-xl">'
    else:
        initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "CV"
        avatar_elem = f"""
          <div class="w-24 h-24 rounded-2xl bg-gradient-to-tr from-[var(--accent)] to-violet-600 p-0.5 shadow-xl flex items-center justify-center text-white font-extrabold text-2xl">
            <div class="w-full h-full bg-slate-950 rounded-2xl flex items-center justify-center">
              <span>{initials}</span>
            </div>
          </div>
        """

    # Socials
    social_links = []
    for link in info.social_links:
        if link.enabled and link.url.strip():
            href = (
                link.url
                if link.url.startswith("http") or link.url.startswith("mailto:")
                else f"https://{link.url}"
            )
            svg_icon = get_social_svg(link.name, link.icon, "w-4 h-4 text-[var(--accent)]")
            social_links.append(f"""
              <a href="{href}" target="_blank" rel="noopener noreferrer" title="{link.name}"
                class="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-[var(--accent)] hover:shadow-lg hover:shadow-[var(--accent-glow)] transition flex items-center gap-2 text-xs font-medium">
                {svg_icon}
                <span>{link.name}</span>
              </a>
            """)
    if not social_links and info.email:
        email_svg = get_social_svg("mail", "mail", "w-4 h-4 text-[var(--accent)]")
        social_links.append(f"""
          <a href="mailto:{info.email}" class="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-[var(--accent)] transition flex items-center gap-2 text-xs font-medium">
            {email_svg}
            <span>{info.email}</span>
          </a>
        """)

    socials_html = "".join(social_links)

    # Resume Download Button
    dl_button = ""
    if resume.portfolio_show_resume_download:
        dl_button = f"""
          <button onclick="window.parent.postMessage('download_resume', '*')"
            class="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 rounded-xl font-semibold text-xs flex items-center gap-2 transition shadow-sm">
            <i data-lucide="file-down" class="w-4 h-4 text-[var(--accent)]"></i>
            <span>Download ATS Resume</span>
          </button>
        """

    # Projects
    project_cards = []
    for p in resume.projects:
        tech = "".join(
            [
                f'<span class="px-2 py-0.5 text-[10px] font-mono bg-slate-900/80 border border-slate-800 text-slate-300 rounded-md">{t}</span>'
                for t in p.technologies
            ]
        )
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-400">• {b.lstrip("•- ")}</li>'
                for b in p.description_bullets[:2]
            ]
        )
        actions = []
        if p.demo_url:
            actions.append(
                f'<a href="{p.demo_url}" target="_blank" class="px-3 py-1 bg-[var(--accent)] text-slate-950 font-bold rounded-lg text-xs flex items-center gap-1.5 hover:brightness-110 transition"><i data-lucide="play" class="w-3.5 h-3.5"></i> Live Demo</a>'
            )
        if p.link:
            actions.append(
                f'<a href="{p.link}" target="_blank" class="px-3 py-1 bg-slate-800 text-slate-200 font-medium rounded-lg text-xs border border-slate-700 flex items-center gap-1.5 hover:border-[var(--accent)] transition"><i data-lucide="github" class="w-3.5 h-3.5"></i> Repo</a>'
            )

        project_cards.append(f"""
          <div class="bg-slate-950/60 border border-slate-800/80 rounded-2xl p-5 flex flex-col justify-between space-y-3 hover:border-[var(--accent)] transition group">
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <h4 class="font-bold text-sm text-white group-hover:text-[var(--accent)] transition">{p.name}</h4>
                <div class="flex flex-wrap gap-1">{tech}</div>
              </div>
              <ul class="space-y-1">{bullets}</ul>
            </div>
            <div class="flex items-center gap-2 pt-2 border-t border-slate-900">{"".join(actions)}</div>
          </div>
        """)

    # Experience
    exp_cards = []
    for exp in resume.work_experience:
        b_items = "".join(
            [
                f'<li class="text-xs text-slate-400">• {b.lstrip("•- ")}</li>'
                for b in exp.bullet_points[:3]
            ]
        )
        exp_cards.append(f"""
          <div class="relative pl-6 pb-6 border-l-2 border-slate-800 last:border-transparent last:pb-0">
            <div class="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full bg-slate-900 border-2 border-[var(--accent)]"></div>
            <div class="space-y-1">
              <div class="flex flex-wrap items-center justify-between gap-1">
                <span class="font-bold text-xs text-slate-200">{exp.job_title} · <span class="text-[var(--accent)]">{exp.company}</span></span>
                <span class="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded-full border border-slate-800">{exp.start_date} – {exp.end_date}</span>
              </div>
              <ul class="space-y-1 pt-1">{b_items}</ul>
            </div>
          </div>
        """)

    # Skills
    skills_badges = []
    for cat in resume.skill_categories:
        tags = "".join(
            [
                f'<span class="px-2.5 py-1 text-xs font-medium bg-slate-900/90 border border-slate-800/80 text-slate-300 rounded-lg hover:border-[var(--accent)] hover:text-white transition">{s}</span>'
                for s in cat.skills
            ]
        )
        skills_badges.append(f"""
          <div class="space-y-2">
            <h5 class="text-[11px] font-bold uppercase tracking-wider text-[var(--accent)]">{cat.category_name}</h5>
            <div class="flex flex-wrap gap-1.5">{tags}</div>
          </div>
        """)

    # Education
    edu_badges = []
    for edu in resume.education:
        edu_badges.append(f"""
          <div class="p-3 bg-slate-900/60 border border-slate-800/80 rounded-xl space-y-1">
            <div class="flex justify-between items-center text-xs font-bold text-slate-200">
              <span>{edu.degree}</span>
              <span class="text-[var(--accent)] text-[11px]">{edu.graduation_year}</span>
            </div>
            <p class="text-[11px] text-slate-400">{edu.institution}</p>
          </div>
        """)

    # Bento Quick metrics (supports custom portfolio_metrics)
    if resume.portfolio_metrics:
        bento_metric_items = "".join([f'''
          <div class="p-3 bg-slate-950 rounded-2xl border border-slate-800 text-center">
            <span class="text-xl sm:text-2xl font-extrabold text-[var(--accent)]">{m.get("value", "0")}</span>
            <p class="text-[9px] text-slate-400 uppercase font-semibold truncate">{m.get("label", "Metric")}</p>
          </div>
        ''' for m in resume.portfolio_metrics[:4]])
    else:
        bento_metric_items = f'''
          <div class="p-3 bg-slate-950 rounded-2xl border border-slate-800 text-center">
            <span class="text-2xl font-extrabold text-[var(--accent)]">{len(resume.projects)}+</span>
            <p class="text-[10px] text-slate-400 uppercase font-semibold">Key Projects</p>
          </div>
          <div class="p-3 bg-slate-950 rounded-2xl border border-slate-800 text-center">
            <span class="text-2xl font-extrabold text-white">{len(resume.work_experience)}+ Yrs</span>
            <p class="text-[10px] text-slate-400 uppercase font-semibold">Milestones</p>
          </div>
        '''

    return f"""
      <div class="max-w-6xl mx-auto px-4 sm:px-6 py-10 space-y-6">
        
        <!-- BENTO ROW 1: Hero & Highlights -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <!-- Bento Card 1: Hero Identity (2 Cols) -->
          <div class="lg:col-span-2 bg-slate-900/70 backdrop-blur border border-slate-800 rounded-3xl p-6 sm:p-8 flex flex-col sm:flex-row gap-6 items-center sm:items-start shadow-xl relative overflow-hidden group">
            <div class="absolute -right-10 -bottom-10 w-48 h-48 rounded-full bg-[var(--accent-glow)] blur-3xl pointer-events-none opacity-20"></div>
            {avatar_elem}
            <div class="space-y-3 text-center sm:text-left flex-1">
              <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>{badge_text}</span>
              </div>
              <div>
                <h1 class="text-2xl sm:text-4xl font-extrabold tracking-tight text-white">{full_name}</h1>
                <p class="text-sm sm:text-base font-semibold text-[var(--accent)] mt-0.5">{role_title}</p>
              </div>
              {f'<p class="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-xl">{summary}</p>' if resume.portfolio_show_bio else ''}
              <div class="flex flex-wrap gap-2 pt-2 justify-center sm:justify-start">
                <a href="{cta_url}" class="px-5 py-2.5 bg-[var(--accent)] hover:brightness-110 text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-[var(--accent-glow)] flex items-center gap-1.5 transition">
                  <i data-lucide="sparkles" class="w-4 h-4"></i>
                  <span>{cta_text}</span>
                </a>
                {dl_button}
              </div>
            </div>
          </div>

          <!-- Bento Card 2: Quick Metrics & Socials (1 Col) -->
          <div class="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-3xl p-6 flex flex-col justify-between space-y-4 shadow-xl">
            <div class="space-y-3">
              <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                <i data-lucide="zap" class="w-4 h-4 text-[var(--accent)]"></i>
                <span>Executive Metric</span>
              </div>
              <div class="grid grid-cols-2 gap-2">
                {bento_metric_items}
              </div>
            </div>
            <div class="space-y-2">
              <span class="text-[10px] font-bold uppercase text-slate-500 tracking-wider">Connect Directly</span>
              <div class="flex flex-wrap gap-2">{socials_html}</div>
            </div>
          </div>

        </div>

        <!-- BENTO ROW 2: Tech Stack & Projects -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <!-- Bento Card 3: Skills Stack (1 Col) -->
          {f'''
          <div class="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-3xl p-6 space-y-4 shadow-xl">
            <div class="flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
              <i data-lucide="cpu" class="w-4 h-4 text-[var(--accent)]"></i>
              <span>Technical Arsenal</span>
            </div>
            <div class="space-y-4">{"".join(skills_badges)}</div>
          </div>
          ''' if resume.portfolio_show_skills else ''}

          <!-- Bento Card 4: Featured Projects Spotlight (2 Cols) -->
          {f'''
          <div class="{"lg:col-span-2" if resume.portfolio_show_skills else "lg:col-span-3"} bg-slate-900/70 backdrop-blur border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-4 shadow-xl">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
              <div class="flex items-center gap-2 text-sm font-bold text-white">
                <i data-lucide="layers" class="w-4 h-4 text-[var(--accent)]"></i>
                <span>Featured Systems & Projects</span>
              </div>
              <span class="text-[11px] text-slate-400 font-mono">{len(resume.projects)} Production Builds</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">{"".join(project_cards)}</div>
          </div>
          ''' if resume.portfolio_show_projects else ''}

        </div>

        <!-- BENTO ROW 3: Experience & Education -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <!-- Bento Card 5: Experience Timeline (2 Cols) -->
          {f'''
          <div class="{"lg:col-span-2" if resume.portfolio_show_education else "lg:col-span-3"} bg-slate-900/70 backdrop-blur border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-4 shadow-xl">
            <div class="flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
              <i data-lucide="briefcase" class="w-4 h-4 text-[var(--accent)]"></i>
              <span>Career Trajectory</span>
            </div>
            <div class="pt-2 space-y-4">{"".join(exp_cards)}</div>
          </div>
          ''' if resume.portfolio_show_experience else ''}

          <!-- Bento Card 6: Education & Credentials (1 Col) -->
          {f'''
          <div class="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-3xl p-6 space-y-4 shadow-xl">
            <div class="flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
              <i data-lucide="graduation-cap" class="w-4 h-4 text-[var(--accent)]"></i>
              <span>Qualifications</span>
            </div>
            <div class="space-y-3">{"".join(edu_badges)}</div>
          </div>
          ''' if resume.portfolio_show_education else ''}

        </div>

      </div>
    """


# ─────────────────────────────────────────────────────────────────────────────
# 2. SPLIT SIDEBAR TEMPLATE (Executive Split-Screen / Senior Director)
# ─────────────────────────────────────────────────────────────────────────────
def render_split_sidebar(resume: TailoredResume, accent: str) -> str:
    info = resume.personal_info
    full_name = info.full_name or "Candidate Name"
    role_title = resume.target_job_title or "Engineering Leader"
    summary = resume.professional_summary or ""
    avatar_url = info.avatar_url or ""
    cta_text = resume.portfolio_cta_text or "Schedule Consultation"
    cta_url = resume.portfolio_cta_url or (
        f"mailto:{info.email}" if info.email else "#contact"
    )

    # Avatar
    if avatar_url:
        avatar_elem = f'<img src="{avatar_url}" alt="{full_name}" class="w-32 h-32 rounded-3xl object-cover ring-2 ring-[var(--accent)] shadow-2xl">'
    else:
        initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "ED"
        avatar_elem = f"""
          <div class="w-32 h-32 rounded-3xl bg-slate-900 border-2 border-[var(--accent)] flex items-center justify-center text-3xl font-extrabold text-white shadow-2xl">
            <span>{initials}</span>
          </div>
        """

    # Socials
    social_links = []
    for link in info.social_links:
        if link.enabled and link.url.strip():
            href = (
                link.url
                if link.url.startswith("http") or link.url.startswith("mailto:")
                else f"https://{link.url}"
            )
            svg_icon = get_social_svg(link.name, link.icon, "w-4 h-4 text-[var(--accent)]")
            social_links.append(f"""
              <a href="{href}" target="_blank" title="{link.name}" class="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-[var(--accent)] transition flex items-center justify-center">
                {svg_icon}
              </a>
            """)
    socials_bar = (
        f'<div class="flex items-center gap-2 pt-2">{"".join(social_links)}</div>'
        if social_links
        else ""
    )

    # Projects
    project_items = []
    for p in resume.projects:
        tech = "".join(
            [
                f'<span class="px-2 py-0.5 text-[10px] font-mono bg-slate-900 border border-slate-800 text-slate-300 rounded">{t}</span>'
                for t in p.technologies
            ]
        )
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-400">• {b.lstrip("•- ")}</li>'
                for b in p.description_bullets
            ]
        )
        links = []
        if p.demo_url:
            links.append(
                f'<a href="{p.demo_url}" target="_blank" class="text-xs text-[var(--accent)] hover:underline flex items-center gap-1 font-semibold"><i data-lucide="external-link" class="w-3 h-3"></i> Live Architecture</a>'
            )
        if p.link:
            links.append(
                f'<a href="{p.link}" target="_blank" class="text-xs text-slate-400 hover:text-white flex items-center gap-1"><i data-lucide="github" class="w-3 h-3"></i> Repository</a>'
            )

        project_items.append(f"""
          <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 space-y-3 hover:border-[var(--accent)] transition">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <h4 class="text-base font-bold text-white">{p.name}</h4>
              <div class="flex items-center gap-3">{"".join(links)}</div>
            </div>
            <div class="flex flex-wrap gap-1.5">{tech}</div>
            <ul class="space-y-1 pt-1">{bullets}</ul>
          </div>
        """)

    # Experience
    exp_items = []
    for exp in resume.work_experience:
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-300 leading-relaxed">• {b.lstrip("•- ")}</li>'
                for b in exp.bullet_points
            ]
        )
        exp_items.append(f"""
          <div class="border-b border-slate-800/80 pb-6 last:border-0 last:pb-0 space-y-2">
            <div class="flex flex-wrap justify-between items-baseline gap-1">
              <div>
                <h4 class="font-bold text-sm text-white">{exp.job_title}</h4>
                <p class="text-xs font-semibold text-[var(--accent)]">{exp.company} {f"· {exp.location}" if exp.location else ""}</p>
              </div>
              <span class="text-xs font-mono text-slate-400">{exp.start_date} — {exp.end_date}</span>
            </div>
            <ul class="space-y-1.5 pt-1">{bullets}</ul>
          </div>
        """)

    return f'''
      <div class="max-w-7xl mx-auto px-4 sm:px-8 py-12">
        <div class="flex flex-col lg:flex-row gap-12 lg:gap-16">
          
          <!-- LEFT STICKY PANE (40%) -->
          <div class="lg:w-5/12 lg:sticky lg:top-12 h-fit space-y-6">
            {avatar_elem}
            <div class="space-y-2">
              <h1 class="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">{full_name}</h1>
              <p class="text-base font-semibold text-[var(--accent)]">{role_title}</p>
              <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>{info.availability_badge or "Available"}</span>
              </div>
            </div>
            {f'<p class="text-sm text-slate-300 leading-relaxed">{summary}</p>' if resume.portfolio_show_bio else ''}
            
            <div class="space-y-3 pt-2">
              <div class="flex items-center gap-3">
                <a href="{cta_url}" class="px-5 py-2.5 bg-[var(--accent)] text-slate-950 font-bold rounded-xl text-xs shadow-lg shadow-[var(--accent-glow)] flex items-center gap-2 hover:brightness-110 transition">
                  <i data-lucide="send" class="w-3.5 h-3.5"></i>
                  <span>{cta_text}</span>
                </a>
                {f'''
                <button onclick="window.parent.postMessage('download_resume', '*')"
                  class="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 rounded-xl font-semibold text-xs flex items-center gap-2 transition">
                  <i data-lucide="download" class="w-3.5 h-3.5 text-[var(--accent)]"></i>
                  <span>Resume PDF</span>
                </button>
                ''' if resume.portfolio_show_resume_download else ''}
              </div>
              {socials_bar}
            </div>

            <!-- In-Page Jump Links -->
            <nav class="hidden lg:flex flex-col space-y-2 pt-6 border-t border-slate-800/80 text-xs font-semibold text-slate-400">
              <a href="#experience" class="hover:text-[var(--accent)] flex items-center gap-2 transition"><i data-lucide="chevron-right" class="w-3 h-3"></i> Career Milestones</a>
              <a href="#projects" class="hover:text-[var(--accent)] flex items-center gap-2 transition"><i data-lucide="chevron-right" class="w-3 h-3"></i> Key Architecture & Projects</a>
              <a href="#skills" class="hover:text-[var(--accent)] flex items-center gap-2 transition"><i data-lucide="chevron-right" class="w-3 h-3"></i> Core Technical Arsenal</a>
            </nav>
          </div>

          <!-- RIGHT SCROLLING PANE (60%) -->
          <div class="lg:w-7/12 space-y-12">
            
            <!-- Experience -->
            {f'''
            <section id="experience" class="space-y-6">
              <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
                <i data-lucide="briefcase" class="w-5 h-5 text-[var(--accent)]"></i>
                <h2 class="text-lg font-bold text-white">Career Milestones & Achievements</h2>
              </div>
              <div class="space-y-6">{"".join(exp_items)}</div>
            </section>
            ''' if resume.portfolio_show_experience else ''}

            <!-- Projects -->
            {f'''
            <section id="projects" class="space-y-6">
              <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
                <i data-lucide="layers" class="w-5 h-5 text-[var(--accent)]"></i>
                <h2 class="text-lg font-bold text-white">Key Systems & Architectures</h2>
              </div>
              <div class="space-y-4">{"".join(project_items)}</div>
            </section>
            ''' if resume.portfolio_show_projects else ''}

            <!-- Skills -->
            {f'''
            <section id="skills" class="space-y-6">
              <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
                <i data-lucide="cpu" class="w-5 h-5 text-[var(--accent)]"></i>
                <h2 class="text-lg font-bold text-white">Core Competencies & Stack</h2>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {"".join([f'<div class="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2"><h4 class="text-xs font-bold text-[var(--accent)] uppercase">{c.category_name}</h4><div class="flex flex-wrap gap-1.5">{"".join([f"<span class=\"px-2 py-0.5 text-xs bg-slate-950 border border-slate-800 text-slate-300 rounded\">{s}</span>" for s in c.skills])}</div></div>' for c in resume.skill_categories])}
              </div>
            </section>
            ''' if resume.portfolio_show_skills else ''}

          </div>

        </div>
      </div>
    '''


# ─────────────────────────────────────────────────────────────────────────────
# 3. CYBER TERMINAL CLI TEMPLATE (Hacker / Terminal Developer Aesthetic)
# ─────────────────────────────────────────────────────────────────────────────
def render_terminal_dev(resume: TailoredResume, accent: str) -> str:
    info = resume.personal_info
    full_name = info.full_name or "Candidate"
    role_title = resume.target_job_title or "Software Developer"
    summary = resume.professional_summary or ""
    user_slug = re.sub(r"[^a-zA-Z0-9]", "", full_name.lower().split()[0]) or "dev"

    # Avatar handling
    avatar_url = info.avatar_url or ""
    if avatar_url:
        avatar_elem = f'<img src="{avatar_url}" alt="{full_name}" class="w-24 h-24 rounded-2xl object-cover ring-2 ring-[var(--accent)] shadow-xl">'
    else:
        initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "DV"
        avatar_elem = f"""
            <div class="w-24 h-24 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-purple-600 p-0.5 shadow-xl">
                <div class="w-full h-full bg-slate-900 rounded-2xl flex items-center justify-center text-2xl font-black text-white">
                    {initials}
                </div>
            </div>
        """

    # Social links with modern styling
    socials = []
    for link in info.social_links:
        if link.enabled and link.url.strip():
            href = (
                link.url
                if link.url.startswith("http") or link.url.startswith("mailto:")
                else f"https://{link.url}"
            )
            svg_icon = get_social_svg(link.name, link.icon, "w-4 h-4 text-slate-400 group-hover:text-[var(--accent)] transition-colors")
            socials.append(f"""
                <a href="{href}" target="_blank" title="{link.name}"
                   class="group p-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-[var(--accent)] hover:bg-slate-800 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-[var(--accent-glow)] flex items-center justify-center">
                    {svg_icon}
                </a>
            """)
    socials_html = "".join(socials)

    # Projects with modern cards
    projects_html = []
    for idx, p in enumerate(resume.projects):
        tech_tags = "".join(
            [
                f'<span class="px-2.5 py-1 text-[10px] font-mono bg-slate-800/60 border border-slate-700/50 text-slate-300 rounded-lg">{t}</span>'
                for t in p.technologies
            ]
        )
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-400 leading-relaxed flex items-start gap-2"><span class="text-[var(--accent)] mt-0.5">▹</span>{b.lstrip("•- ")}</li>'
                for b in p.description_bullets[:3]
            ]
        )

        actions = []
        if p.demo_url:
            actions.append(
                f'<a href="{p.demo_url}" target="_blank" class="px-4 py-2 bg-[var(--accent)] text-slate-950 font-bold rounded-lg text-xs hover:brightness-110 transition-all duration-300 hover:scale-105 flex items-center gap-1.5 shadow-lg shadow-[var(--accent-glow)]"><i data-lucide="external-link" class="w-3.5 h-3.5"></i> Live Demo</a>'
            )
        if p.link:
            actions.append(
                f'<a href="{p.link}" target="_blank" class="px-4 py-2 bg-slate-800/60 border border-slate-700/50 text-slate-200 font-medium rounded-lg text-xs hover:border-[var(--accent)] hover:bg-slate-800 transition-all duration-300 flex items-center gap-1.5"><i data-lucide="github" class="w-3.5 h-3.5"></i> Source</a>'
            )

        projects_html.append(f"""
            <div class="group bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 hover:border-[var(--accent)] rounded-2xl p-6 transition-all duration-500 hover:-translate-y-1 hover:shadow-2xl hover:shadow-[var(--accent-glow)] stagger-item">
                <div class="flex flex-wrap items-start justify-between gap-3 mb-3">
                    <div class="flex items-center gap-3">
                        <span class="text-xs font-mono text-[var(--accent)] font-bold">#{idx+1:02d}</span>
                        <h4 class="text-base font-bold text-white group-hover:text-[var(--accent)] transition-colors">{p.name}</h4>
                    </div>
                    <div class="flex flex-wrap gap-1.5">{tech_tags}</div>
                </div>
                <ul class="space-y-1.5 mb-4">{bullets}</ul>
                <div class="flex flex-wrap gap-2 pt-3 border-t border-slate-800/50">{''.join(actions)}</div>
            </div>
        """)

    # Experience with timeline
    experience_html = []
    for exp in resume.work_experience:
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-400 leading-relaxed flex items-start gap-2"><span class="text-[var(--accent)] mt-0.5">▹</span>{b.lstrip("•- ")}</li>'
                for b in exp.bullet_points[:3]
            ]
        )
        experience_html.append(f"""
            <div class="relative pl-8 pb-8 border-l-2 border-slate-800 last:border-0 stagger-item">
                <div class="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full bg-slate-900 border-2 border-[var(--accent)] shadow-lg shadow-[var(--accent-glow)]"></div>
                <div class="flex flex-wrap items-center justify-between gap-2 mb-1">
                    <div>
                        <h4 class="font-bold text-sm text-white">{exp.job_title}</h4>
                        <span class="text-xs font-semibold text-[var(--accent)]">{exp.company}</span>
                    </div>
                    <span class="text-[10px] font-mono text-slate-500 bg-slate-900/60 px-2.5 py-1 rounded-full border border-slate-800">{exp.start_date} — {exp.end_date}</span>
                </div>
                <ul class="space-y-1 mt-2">{bullets}</ul>
            </div>
        """)

    # Skills with animated progress bars
    skills_html = []
    for cat in resume.skill_categories:
        skill_items = []
        for s in cat.skills[:4]:
            level = cat.skill_levels.get(s, 85)
            skill_items.append(f"""
                <div class="space-y-1">
                    <div class="flex justify-between text-xs">
                        <span class="text-slate-300 font-medium">{s}</span>
                        <span class="text-[var(--accent)] font-mono">{level}%</span>
                    </div>
                    <div class="w-full h-1.5 bg-slate-800/60 rounded-full overflow-hidden">
                        <div class="h-full rounded-full bg-gradient-to-r from-[var(--accent)] to-purple-500 transition-all duration-1000 ease-out skill-bar" style="width: 0%"></div>
                    </div>
                </div>
            """)
        skills_html.append(f"""
            <div class="p-5 bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-xl hover:border-[var(--accent)] transition-all duration-300 stagger-item">
                <h5 class="text-xs font-bold uppercase tracking-wider text-[var(--accent)] mb-3 flex items-center gap-2">
                    <i data-lucide="code-2" class="w-3.5 h-3.5"></i>
                    {cat.category_name}
                </h5>
                <div class="space-y-2.5">{''.join(skill_items)}</div>
            </div>
        """)

    # Education
    education_html = []
    for edu in resume.education:
        education_html.append(f"""
            <div class="flex items-center gap-4 p-4 bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-xl hover:border-[var(--accent)] transition-all duration-300 stagger-item">
                <div class="w-12 h-12 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/20 flex items-center justify-center text-[var(--accent)] text-lg">
                    <i data-lucide="graduation-cap" class="w-5 h-5"></i>
                </div>
                <div class="flex-1">
                    <h5 class="font-bold text-sm text-white">{edu.degree}</h5>
                    <p class="text-xs text-slate-400">{edu.institution}</p>
                </div>
                <span class="text-xs font-mono text-[var(--accent)] font-bold">{edu.graduation_year}</span>
            </div>
        """)

    # Quick metrics (support custom portfolio_metrics or fallback to defaults)
    if resume.portfolio_metrics:
        colors = ["text-[var(--accent)]", "text-white", "text-emerald-400", "text-purple-400", "text-cyan-400"]
        metrics = []
        for i, m in enumerate(resume.portfolio_metrics):
            metrics.append({
                "label": m.get("label", "Metric"),
                "value": m.get("value", "0"),
                "color": colors[i % len(colors)]
            })
    else:
        metrics = [
            {"label": "Projects", "value": f"{len(resume.projects)}+", "color": "text-[var(--accent)]"},
            {"label": "Experience", "value": f"{len(resume.work_experience)}+ Yrs", "color": "text-white"},
            {"label": "Skills", "value": f"{sum(len(c.skills) for c in resume.skill_categories)}+", "color": "text-purple-400"},
            {"label": "System Uptime", "value": "99.98%", "color": "text-emerald-400"}
        ]
    metrics_html = "".join([f"""
        <div class="text-center p-4 bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-xl hover:border-[var(--accent)] transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-[var(--accent-glow)] stagger-item">
            <div class="text-2xl font-black {m['color']}">{m['value']}</div>
            <p class="text-[10px] text-slate-400 uppercase font-semibold tracking-wider">{m['label']}</p>
        </div>
    """ for m in metrics])

    # Interactive quick commands (modern version)
    quick_commands = [
        {"cmd": "bio", "label": "$ cat bio.md"},
        {"cmd": "projects", "label": "$ ls -la projects/"},
        {"cmd": "skills", "label": "$ ./tech-stack"},
        {"cmd": "experience", "label": "$ journalctl --career"},
        {"cmd": "contact", "label": "$ echo $CONTACT"},
    ]
    commands_html = "".join([f"""
        <button onclick="runCommand('{c['cmd']}')" 
                class="px-3.5 py-2 bg-slate-800/60 border border-slate-700/50 hover:border-[var(--accent)] text-slate-300 hover:text-white rounded-lg text-[11px] font-mono transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-[var(--accent-glow)]">
            {c['label']}
        </button>
    """ for c in quick_commands])

    # Pre-computed JSON strings to avoid dict hashing syntax errors in f-strings
    projects_json_data = json.dumps([p.name for p in resume.projects])
    skills_json_data = json.dumps([s for cat in resume.skill_categories for s in cat.skills])
    exp_json_data = json.dumps([{"title": e.job_title, "company": e.company} for e in resume.work_experience[:3]])

    return f"""
    <div class="max-w-6xl mx-auto px-4 sm:px-6 py-12">
        
        <!-- HERO SECTION -->
        <div class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900/90 via-slate-900/50 to-slate-950/90 backdrop-blur-xl border border-slate-800/50 p-8 sm:p-12 mb-12 animate-fade-in-up">
            
            <!-- Ambient glow -->
            <div class="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-[var(--accent)] blur-[120px] opacity-20 pointer-events-none"></div>
            <div class="absolute -bottom-24 -left-24 w-72 h-72 rounded-full bg-purple-600 blur-[120px] opacity-20 pointer-events-none"></div>
            
            <div class="relative flex flex-col md:flex-row items-center gap-8">
                <!-- Avatar -->
                {avatar_elem}
                
                <!-- Info -->
                <div class="flex-1 text-center md:text-left">
                    <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold mb-4">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        <span>{info.availability_badge or "Available for Opportunities"}</span>
                    </div>
                    <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight mb-2">{full_name}</h1>
                    <p class="text-lg sm:text-xl font-semibold text-[var(--accent)] mb-3">{role_title}</p>
                    {f'<p class="text-sm text-slate-300 leading-relaxed max-w-2xl">{summary}</p>' if resume.portfolio_show_bio else ''}
                    
                    <!-- Socials -->
                    <div class="flex flex-wrap gap-2 mt-4 justify-center md:justify-start">
                        {socials_html}
                    </div>
                    
                    <!-- CTA -->
                    <div class="flex flex-wrap gap-3 mt-5 justify-center md:justify-start">
                        <a href="{resume.portfolio_cta_url or f"mailto:{info.email}"}" 
                           class="px-6 py-3 bg-[var(--accent)] text-slate-950 font-bold rounded-xl text-sm hover:brightness-110 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-2xl hover:shadow-[var(--accent-glow)] flex items-center gap-2">
                            <i data-lucide="sparkles" class="w-4 h-4"></i>
                            {resume.portfolio_cta_text or "Let's Connect"}
                        </a>
                        {f'''
                        <button onclick="window.parent.postMessage('download_resume', '*')"
                                class="px-6 py-3 bg-slate-800/60 border border-slate-700/50 text-slate-200 font-semibold rounded-xl text-sm hover:border-[var(--accent)] hover:bg-slate-800 transition-all duration-300 hover:-translate-y-0.5 flex items-center gap-2">
                            <i data-lucide="download" class="w-4 h-4 text-[var(--accent)]"></i>
                            Download CV
                        </button>
                        ''' if resume.portfolio_show_resume_download else ''}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- METRICS -->
        <div class="grid grid-cols-3 gap-4 mb-12">
            {metrics_html}
        </div>
        
        <!-- QUICK COMMANDS (subtle interactive bar) -->
        <div class="bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-4 mb-12 flex flex-wrap items-center gap-3 animate-fade-in-up">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-500 mr-2">⚡ Quick</span>
            {commands_html}
            <button onclick="clearTerminal()" 
                    class="px-3.5 py-2 bg-red-500/10 border border-red-500/20 hover:border-red-500 text-red-400 rounded-lg text-[11px] font-mono transition-all duration-300 hover:-translate-y-0.5">
                $ clear
            </button>
        </div>
        
        <!-- TERMINAL OUTPUT (hidden by default, appears when commands run) -->
        <div id="termOutput" class="hidden mb-12 bg-slate-900/60 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-6 space-y-4 font-mono animate-fade-in-up"></div>
        
        <!-- PROJECTS -->
        {f'''
        <section class="mb-12 animate-fade-in-up">
            <div class="flex items-center justify-between border-b border-slate-800/50 pb-4 mb-6">
                <h2 class="text-xl font-bold text-white flex items-center gap-3">
                    <i data-lucide="layers" class="w-5 h-5 text-[var(--accent)]"></i>
                    Featured Projects
                </h2>
                <span class="text-xs text-slate-500 font-mono">{len(resume.projects)} systems</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                {''.join(projects_html)}
            </div>
        </section>
        ''' if resume.portfolio_show_projects else ''}
        
        <!-- EXPERIENCE + SKILLS + EDUCATION GRID -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-12">
            
            <!-- Experience -->
            {f'''
            <div class="lg:col-span-2 bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-6 animate-fade-in-up">
                <h2 class="text-xl font-bold text-white flex items-center gap-3 border-b border-slate-800/50 pb-4 mb-6">
                    <i data-lucide="briefcase" class="w-5 h-5 text-[var(--accent)]"></i>
                    Career Timeline
                </h2>
                <div class="space-y-2">{''.join(experience_html)}</div>
            </div>
            ''' if resume.portfolio_show_experience else ''}
            
            <!-- Skills -->
            {f'''
            <div class="bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-6 animate-fade-in-up">
                <h2 class="text-xl font-bold text-white flex items-center gap-3 border-b border-slate-800/50 pb-4 mb-6">
                    <i data-lucide="cpu" class="w-5 h-5 text-[var(--accent)]"></i>
                    Tech Stack
                </h2>
                <div class="space-y-4">{''.join(skills_html)}</div>
            </div>
            ''' if resume.portfolio_show_skills else ''}
            
        </div>
        
        <!-- EDUCATION -->
        {f'''
        <section class="animate-fade-in-up">
            <div class="bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-6">
                <h2 class="text-xl font-bold text-white flex items-center gap-3 border-b border-slate-800/50 pb-4 mb-6">
                    <i data-lucide="graduation-cap" class="w-5 h-5 text-[var(--accent)]"></i>
                    Education
                </h2>
                <div class="space-y-3">{''.join(education_html)}</div>
            </div>
        </section>
        ''' if resume.portfolio_show_education else ''}
        
    </div>
    
    <!-- JavaScript for Interactions -->
    <script>
        // Terminal command runner (simplified, just shows output)
        function runCommand(cmd) {{
            const output = document.getElementById('termOutput');
            output.classList.remove('hidden');
            const div = document.createElement('div');
            div.className = 'space-y-2 border-l-2 border-[var(--accent)] pl-4 text-xs';
            
            if (cmd === 'bio') {{
                div.innerHTML = `<span class="text-[var(--accent)] font-bold">$ cat bio.md</span><p class="text-slate-300 leading-relaxed">{summary or "No bio available."}</p>`;
            }} else if (cmd === 'projects') {{
                const projects = {projects_json_data};
                div.innerHTML = `<span class="text-[var(--accent)] font-bold">$ ls -la projects/</span><div class="space-y-1 text-slate-300">` + 
                    projects.map((p, i) => `<div class="flex items-center gap-2"><span class="text-[var(--accent)]">▹</span> <span class="font-bold">${{p}}</span> <span class="text-slate-500 text-[10px]">(project_0${{i+1}})</span></div>`).join('') +
                    `</div>`;
            }} else if (cmd === 'skills') {{
                const skills = {skills_json_data};
                div.innerHTML = `<span class="text-[var(--accent)] font-bold">$ ./tech-stack</span><div class="flex flex-wrap gap-1.5">` + 
                    skills.map(s => `<span class="px-2 py-0.5 bg-slate-800/60 border border-slate-700/50 rounded text-slate-300 text-[10px]">${{s}}</span>`).join('') +
                    `</div>`;
            }} else if (cmd === 'experience') {{
                const exp = {exp_json_data};
                div.innerHTML = `<span class="text-[var(--accent)] font-bold">$ journalctl --career</span><div class="space-y-1 text-slate-300">` +
                    exp.map(e => `<div>+ <span class="text-white font-bold">${{e.title}}</span> @ <span class="text-[var(--accent)]">${{e.company}}</span></div>`).join('') +
                    `</div>`;
            }} else if (cmd === 'contact') {{
                div.innerHTML = `<span class="text-[var(--accent)] font-bold">$ echo $CONTACT</span><div class="flex gap-2 pt-1">{socials_html}</div>`;
            }} else {{
                div.innerHTML = `<span class="text-red-400">Command not found: ${{cmd}}. Try: bio, projects, skills, experience, contact</span>`;
            }}
            output.appendChild(div);
            output.scrollTop = output.scrollHeight;
        }}
        
        function clearTerminal() {{
            const output = document.getElementById('termOutput');
            output.innerHTML = '';
            output.classList.add('hidden');
        }}
        
        // Trigger skill bar animations on scroll
        document.addEventListener('DOMContentLoaded', function() {{
            const observer = new IntersectionObserver((entries) => {{
                entries.forEach(entry => {{
                    if (entry.isIntersecting) {{
                        const bars = entry.target.querySelectorAll('.skill-bar');
                        bars.forEach(bar => {{
                            const width = bar.style.width;
                            bar.style.width = '0%';
                            setTimeout(() => {{
                                bar.style.width = width;
                            }}, 100);
                        }});
                    }}
                }});
            }}, {{ threshold: 0.3 }});
            
            document.querySelectorAll('.skill-bar').forEach(bar => {{
                const parent = bar.closest('.space-y-2\\.5') || bar.closest('.space-y-4');
                if (parent) observer.observe(parent);
            }});
        }});
    </script>
    
    <style>
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .animate-fade-in-up {{
            animation: fadeInUp 0.7s ease-out both;
        }}
        .stagger-item {{
            opacity: 0;
            animation: fadeInUp 0.6s ease-out forwards;
        }}
        .stagger-item:nth-child(1) {{ animation-delay: 0.05s; }}
        .stagger-item:nth-child(2) {{ animation-delay: 0.10s; }}
        .stagger-item:nth-child(3) {{ animation-delay: 0.15s; }}
        .stagger-item:nth-child(4) {{ animation-delay: 0.20s; }}
        .stagger-item:nth-child(5) {{ animation-delay: 0.25s; }}
        .stagger-item:nth-child(6) {{ animation-delay: 0.30s; }}
        .stagger-item:nth-child(7) {{ animation-delay: 0.35s; }}
        .stagger-item:nth-child(8) {{ animation-delay: 0.40s; }}
        
        /* Smooth transitions */
        * {{
            transition-property: all;
        }}
    </style>
    """


# ─────────────────────────────────────────────────────────────────────────────
# 4. EDITORIAL SWISS TEMPLATE (Awwwards Typographic Luxury Magazine)
# ─────────────────────────────────────────────────────────────────────────────
def render_editorial_swiss(resume: TailoredResume, accent: str) -> str:
    info = resume.personal_info
    full_name = info.full_name or "Candidate Name"
    role_title = resume.target_job_title or "Software Architect"
    summary = resume.professional_summary or ""
    cta_text = resume.portfolio_cta_text or "Initiate Conversation"
    cta_url = resume.portfolio_cta_url or (
        f"mailto:{info.email}" if info.email else "#contact"
    )
    initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "SW"

    # Socials
    socials = []
    for link in info.social_links:
        if link.enabled and link.url.strip():
            href = (
                link.url
                if link.url.startswith("http") or link.url.startswith("mailto:")
                else f"https://{link.url}"
            )
            socials.append(
                f'<a href="{href}" target="_blank" class="hover:text-[var(--accent)] underline underline-offset-4 mr-6 text-xs font-mono transition duration-300">{link.name}</a>'
            )
    if info.email:
        socials.append(
            f'<a href="mailto:{info.email}" class="hover:text-[var(--accent)] underline underline-offset-4 mr-6 text-xs font-mono transition duration-300">{info.email}</a>'
        )

    # Marquee
    marquee_words = [
        full_name.upper(),
        role_title.upper(),
        "DISTRIBUTED SYSTEMS",
        "HIGH IMPACT ARCHITECTURE",
        "PRODUCTION VERIFIED",
        "ATS CERTIFIED",
    ]
    if resume.skill_categories:
        marquee_words.extend(
            [s.upper() for cat in resume.skill_categories for s in cat.skills[:2]]
        )
    marquee_content = " ✦ ".join(marquee_words)

    # Projects
    projects_html = []
    for idx, p in enumerate(resume.projects):
        tech_pills = "".join(
            [
                f'<span class="px-2 py-0.5 text-[10px] font-mono border border-slate-700 text-slate-300 rounded uppercase">{t}</span>'
                for t in p.technologies
            ]
        )
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-400 leading-relaxed">• {b.lstrip("•- ")}</li>'
                for b in p.description_bullets
            ]
        )
        actions = []
        if p.demo_url:
            actions.append(
                f'<a href="{p.demo_url}" target="_blank" class="px-3.5 py-1.5 bg-white text-black font-bold text-xs uppercase tracking-wider hover:bg-[var(--accent)] hover:text-white transition duration-300 flex items-center gap-1 shadow-md hover:shadow-lg hover:shadow-[var(--accent-glow)]">Live Site →</a>'
            )
        if p.link:
            actions.append(
                f'<a href="{p.link}" target="_blank" class="px-3.5 py-1.5 border border-slate-700 hover:border-white text-white font-mono text-xs transition duration-300 flex items-center gap-1 hover:bg-white/10">Source Code</a>'
            )

        projects_html.append(f"""
          <div class="py-6 border-b border-slate-800 space-y-4 group transition duration-300 hover:border-[var(--accent)] stagger-item">
            <div class="flex flex-wrap justify-between items-baseline gap-2 cursor-pointer">
              <div class="flex items-baseline gap-3">
                <span class="text-xs font-mono text-slate-500">[{idx+1:02d}]</span>
                <h4 class="text-xl sm:text-2xl font-bold text-white group-hover:text-[var(--accent)] tracking-tight transition duration-300 relative inline-block">
                  {p.name}
                  <span class="absolute bottom-0 left-0 w-0 h-0.5 bg-[var(--accent)] transition-all duration-300 group-hover:w-full"></span>
                </h4>
              </div>
              <div class="flex items-center gap-3">
                <div class="hidden sm:flex flex-wrap gap-1.5">{tech_pills}</div>
                <div class="flex gap-2">{"".join(actions)}</div>
              </div>
            </div>
            <div class="pl-8 border-l border-slate-800/80 space-y-2 max-w-4xl">
              <ul class="space-y-1">{bullets}</ul>
            </div>
          </div>
        """)

    # Experience
    experiences_html = []
    for exp in resume.work_experience:
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-300 leading-relaxed">• {b.lstrip("•- ")}</li>'
                for b in exp.bullet_points[:3]
            ]
        )
        experiences_html.append(f"""
          <div class="grid grid-cols-1 md:grid-cols-12 gap-6 py-6 border-b border-slate-800 stagger-item transition duration-300 hover:border-[var(--accent)]">
            <div class="md:col-span-4 space-y-1">
              <span class="text-xs font-mono text-[var(--accent)] uppercase font-semibold">{exp.start_date} — {exp.end_date}</span>
              <h4 class="font-bold text-base text-white">{exp.job_title}</h4>
              <p class="text-xs text-slate-400 italic">{exp.company} {f"// {exp.location}" if exp.location else ""}</p>
            </div>
            <div class="md:col-span-8">
              <ul class="space-y-1.5">{bullets}</ul>
            </div>
          </div>
        """)

    # Skills categories as a matrix
    skills_html = "".join([f"""
      <div class="space-y-2 border-l border-slate-800 pl-4 stagger-item transition duration-300 hover:border-[var(--accent)]">
        <span class="text-xs font-bold text-[var(--accent)] uppercase font-mono tracking-wider">{c.category_name}</span>
        <p class="text-xs text-slate-300 leading-relaxed">{" · ".join(c.skills)}</p>
      </div>
    """ for c in resume.skill_categories])

    return f"""
      <div class="max-w-6xl mx-auto px-6 py-16 space-y-16">

        <!-- Masthead -->
        <header class="border-b-2 border-white pb-12 space-y-8 animate-fade-in-up">
          <div class="flex justify-between items-center text-xs uppercase tracking-widest font-mono text-slate-400 border-b border-slate-800 pb-3">
            <span>VOL. 2026 // EDITION NO. 09</span>
            <span>PRINT & DIGITAL MONOGRAPH</span>
            <span>{info.location or "GENEVA // GLOBAL"}</span>
          </div>

          <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
            <div class="space-y-2 flex-1">
              <h1 class="text-4xl sm:text-7xl lg:text-8xl font-black text-white tracking-tighter uppercase leading-none">{full_name}</h1>
              <p class="text-xl sm:text-3xl font-light text-[var(--accent)] tracking-tight uppercase pt-1">{role_title}</p>
            </div>

            <!-- Rotating Monogram -->
            <div class="relative w-28 h-28 shrink-0 flex items-center justify-center group">
              <svg class="w-full h-full animate-[spin_20s_linear_infinite] group-hover:scale-110 transition-transform duration-700" viewBox="0 0 100 100">
                <path id="circlePath" d="M 50, 50 m -37, 0 a 37,37 0 1,1 74,0 a 37,37 0 1,1 -74,0" fill="transparent"/>
                <text class="text-[8.5px] uppercase font-mono tracking-widest fill-slate-300">
                  <textPath href="#circlePath" startOffset="0%">
                    ✦ VERIFIED ARCHITECT ✦ SENIOR ENGINEER ✦
                  </textPath>
                </text>
              </svg>
              <div class="absolute inset-0 flex items-center justify-center font-black text-xl text-white font-mono">
                <span>{initials}</span>
              </div>
            </div>
          </div>

          {f'<p class="text-base sm:text-xl text-slate-300 max-w-3xl font-light leading-relaxed pt-2 drop-cap">{summary}</p>' if resume.portfolio_show_bio else ''}

          <div class="flex flex-wrap items-center gap-4 pt-2">
            <a href="{cta_url}" class="px-7 py-3.5 bg-white text-black font-bold text-xs uppercase tracking-widest hover:bg-[var(--accent)] hover:text-white transition duration-300 shadow-lg hover:shadow-xl hover:shadow-[var(--accent-glow)]">
              {cta_text} →
            </a>
            {f'''
            <button onclick="window.parent.postMessage('download_resume', '*')"
              class="px-7 py-3.5 border border-slate-700 text-white font-semibold text-xs uppercase tracking-widest hover:border-white hover:bg-white/5 transition duration-300">
              Download CV Monograph (PDF)
            </button>
            ''' if resume.portfolio_show_resume_download else ''}
          </div>
        </header>

        <!-- Marquee -->
        <div class="overflow-hidden border-y border-slate-800 py-3 bg-slate-950/60 font-mono text-xs uppercase tracking-widest text-[var(--accent)]">
          <div class="whitespace-nowrap flex gap-8 animate-marquee">
            <span>{marquee_content}</span>
            <span>{marquee_content}</span>
          </div>
        </div>

        <!-- Projects -->
        {f'''
        <section class="space-y-6 animate-fade-in-up">
          <div class="flex justify-between items-baseline border-b border-white pb-3">
            <h3 class="text-sm font-mono tracking-widest uppercase text-slate-400">01 / SELECTED WORKS & SYSTEMS</h3>
            <span class="text-xs font-mono text-slate-500">{len(resume.projects)} EXHIBITS</span>
          </div>
          <div class="space-y-2">{"".join(projects_html)}</div>
        </section>
        ''' if resume.portfolio_show_projects else ''}

        <!-- Experience -->
        {f'''
        <section class="space-y-6 animate-fade-in-up">
          <div class="flex justify-between items-baseline border-b border-white pb-3">
            <h3 class="text-sm font-mono tracking-widest uppercase text-slate-400">02 / CAREER RECORD & ACHIEVEMENTS</h3>
            <span class="text-xs font-mono text-slate-500">{len(resume.work_experience)} MILESTONES</span>
          </div>
          <div class="space-y-2">{"".join(experiences_html)}</div>
        </section>
        ''' if resume.portfolio_show_experience else ''}

        <!-- Skills -->
        {f'''
        <section class="space-y-6 animate-fade-in-up">
          <div class="flex justify-between items-baseline border-b border-white pb-3">
            <h3 class="text-sm font-mono tracking-widest uppercase text-slate-400">03 / CORE COMPETENCIES</h3>
            <span class="text-xs font-mono text-slate-500">SYSTEM ARCHITECTURE</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-8 pt-2">
            {skills_html}
          </div>
        </section>
        ''' if resume.portfolio_show_skills else ''}

        <!-- Footer -->
        <footer class="pt-12 border-t-2 border-white flex flex-wrap justify-between items-center text-xs text-slate-400 gap-4 animate-fade-in-up">
          <div>{" ".join(socials)}</div>
          <div class="font-mono text-[11px] text-slate-500 uppercase">
            <span>© 2026 {full_name} · All Rights Reserved</span>
          </div>
        </footer>
      </div>

      <style>
        @keyframes marquee {{
          0% {{ transform: translateX(0%); }}
          100% {{ transform: translateX(-50%); }}
        }}
        @keyframes fadeInUp {{
          from {{ opacity: 0; transform: translateY(30px); }}
          to {{ opacity: 1; transform: translateY(0); }}
        }}
        .animate-fade-in-up {{
          animation: fadeInUp 0.8s ease-out both;
        }}
        .animate-marquee {{
          animation: marquee 35s linear infinite;
          will-change: transform;
        }}
        .stagger-item {{
          opacity: 0;
          animation: fadeInUp 0.6s ease-out forwards;
        }}
        .stagger-item:nth-child(1) {{ animation-delay: 0.05s; }}
        .stagger-item:nth-child(2) {{ animation-delay: 0.10s; }}
        .stagger-item:nth-child(3) {{ animation-delay: 0.15s; }}
        .stagger-item:nth-child(4) {{ animation-delay: 0.20s; }}
        .stagger-item:nth-child(5) {{ animation-delay: 0.25s; }}
        .stagger-item:nth-child(6) {{ animation-delay: 0.30s; }}
        .stagger-item:nth-child(7) {{ animation-delay: 0.35s; }}
        .stagger-item:nth-child(8) {{ animation-delay: 0.40s; }}
        .stagger-item:nth-child(9) {{ animation-delay: 0.45s; }}
        .stagger-item:nth-child(10) {{ animation-delay: 0.50s; }}
        /* drop‑cap for summary */
        .drop-cap::first-letter {{
          font-size: 3.5em;
          float: left;
          line-height: 1;
          margin-right: 0.15em;
          color: var(--accent);
          font-weight: 700;
          font-family: serif;
        }}
        /* smoother scrolling */
        html {{
          scroll-behavior: smooth;
        }}
        /* subtle glow on hover for buttons */
        .hover\\:shadow-\\[var\\(--accent-glow\\)\\]:hover {{
          box-shadow: 0 0 20px var(--accent-glow);
        }}
      </style>
    """


# ─────────────────────────────────────────────────────────────────────────────
# 5. NEON GLASS TEMPLATE (Futuristic Neo-Glassmorphism 3D Glow)
# ─────────────────────────────────────────────────────────────────────────────
def render_neon_glass(resume: TailoredResume, accent: str) -> str:
    info = resume.personal_info
    full_name = info.full_name or "Candidate"
    role_title = resume.target_job_title or "Full Stack Developer"
    summary = resume.professional_summary or ""
    avatar_url = info.avatar_url or ""
    badge_text = info.availability_badge or "Available for Impact"
    cta_text = resume.portfolio_cta_text or "Connect Now"
    cta_url = resume.portfolio_cta_url or (
        f"mailto:{info.email}" if info.email else "#contact"
    )

    # Avatar
    if avatar_url:
        avatar_elem = f'<img src="{avatar_url}" alt="{full_name}" class="w-28 h-28 rounded-full object-cover ring-4 ring-[var(--accent)] shadow-2xl shadow-[var(--accent-glow)]">'
    else:
        initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "NG"
        avatar_elem = f"""
          <div class="w-28 h-28 rounded-full bg-gradient-to-tr from-[var(--accent)] to-pink-500 p-1 shadow-2xl shadow-[var(--accent-glow)] flex items-center justify-center text-white text-3xl font-extrabold">
            <div class="w-full h-full bg-slate-950 rounded-full flex items-center justify-center">
              <span>{initials}</span>
            </div>
          </div>
        """

    # Socials
    social_links = []
    for link in info.social_links:
        if link.enabled and link.url.strip():
            href = (
                link.url
                if link.url.startswith("http") or link.url.startswith("mailto:")
                else f"https://{link.url}"
            )
            icon = get_social_icon(link.name, link.icon)
            social_links.append(f"""
              <a href="{href}" target="_blank"
                class="p-3 rounded-2xl bg-white/5 backdrop-blur-md border border-white/10 hover:border-[var(--accent)] hover:shadow-lg hover:shadow-[var(--accent-glow)] text-slate-200 transition flex items-center gap-2 text-xs font-medium">
                <i data-lucide="{icon}" class="w-4 h-4 text-[var(--accent)]"></i>
                <span>{link.name}</span>
              </a>
            """)
    socials_bar = (
        f'<div class="flex flex-wrap justify-center gap-3 pt-2">{"".join(social_links)}</div>'
        if social_links
        else ""
    )

    # Projects
    projects = []
    for p in resume.projects:
        tech = "".join(
            [
                f'<span class="px-2 py-0.5 text-[10px] bg-white/5 border border-white/10 rounded-md text-slate-300 font-medium">{t}</span>'
                for t in p.technologies
            ]
        )
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-300">• {b.lstrip("•- ")}</li>'
                for b in p.description_bullets[:2]
            ]
        )
        actions = []
        if p.demo_url:
            actions.append(
                f'<a href="{p.demo_url}" target="_blank" class="px-3 py-1 bg-[var(--accent)] text-slate-950 font-bold rounded-lg text-xs hover:brightness-110 transition flex items-center gap-1"><i data-lucide="play" class="w-3 h-3"></i> Live</a>'
            )
        if p.link:
            actions.append(
                f'<a href="{p.link}" target="_blank" class="px-3 py-1 bg-white/10 text-white rounded-lg text-xs hover:bg-white/20 transition flex items-center gap-1"><i data-lucide="github" class="w-3 h-3"></i> Code</a>'
            )

        projects.append(f"""
          <div class="bg-white/5 backdrop-blur-xl border border-white/10 hover:border-[var(--accent)] hover:shadow-xl hover:shadow-[var(--accent-glow)] rounded-3xl p-6 space-y-3 transition group">
            <div class="flex items-center justify-between">
              <h4 class="font-bold text-base text-white group-hover:text-[var(--accent)] transition">{p.name}</h4>
              <div class="flex items-center gap-2">{"".join(actions)}</div>
            </div>
            <div class="flex flex-wrap gap-1.5">{tech}</div>
            <ul class="space-y-1">{bullets}</ul>
          </div>
        """)

    return f'''
      <div class="relative overflow-hidden min-h-screen py-16 px-4 sm:px-8">
        
        <!-- Glowing Ambient Orbs -->
        <div class="absolute top-10 left-1/4 w-96 h-96 rounded-full bg-[var(--accent)] blur-[120px] opacity-20 pointer-events-none"></div>
        <div class="absolute bottom-20 right-1/4 w-96 h-96 rounded-full bg-purple-600 blur-[140px] opacity-20 pointer-events-none"></div>

        <div class="max-w-5xl mx-auto space-y-16 relative z-10">
          
          <!-- Hero Center Showcase -->
          <div class="bg-white/5 backdrop-blur-2xl border border-white/10 rounded-3xl p-8 sm:p-12 text-center space-y-6 shadow-2xl">
            <div class="flex justify-center">{avatar_elem}</div>
            <div class="space-y-2">
              <div class="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                <span>{badge_text}</span>
              </div>
              <h1 class="text-3xl sm:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-100 to-[var(--accent)] tracking-tight">{full_name}</h1>
              <p class="text-base sm:text-xl font-semibold text-[var(--accent)]">{role_title}</p>
            </div>
            {f'<p class="text-sm sm:text-base text-slate-300 max-w-2xl mx-auto leading-relaxed">{summary}</p>' if resume.portfolio_show_bio else ''}
            
            <div class="flex flex-wrap justify-center gap-3 pt-2">
              <a href="{cta_url}" class="px-6 py-3 bg-[var(--accent)] text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-[var(--accent-glow)] hover:brightness-110 transition flex items-center gap-2">
                <i data-lucide="sparkles" class="w-4 h-4"></i>
                <span>{cta_text}</span>
              </a>
              {f'''
              <button onclick="window.parent.postMessage('download_resume', '*')"
                class="px-5 py-3 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-semibold text-xs rounded-xl transition flex items-center gap-2">
                <i data-lucide="file-down" class="w-4 h-4 text-[var(--accent)]"></i>
                <span>Download ATS CV</span>
              </button>
              ''' if resume.portfolio_show_resume_download else ''}
            </div>

            {socials_bar}
          </div>

          <!-- Projects Showcase -->
          {f'''
          <div class="space-y-6">
            <div class="flex items-center gap-2 text-xl font-bold text-white">
              <i data-lucide="layers" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Featured Creations & Systems</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">{"".join(projects)}</div>
          </div>
          ''' if resume.portfolio_show_projects else ''}

          <!-- Experience Showcase -->
          {f'''
          <div class="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 space-y-6 shadow-xl">
            <div class="flex items-center gap-2 text-xl font-bold text-white border-b border-white/10 pb-4">
              <i data-lucide="briefcase" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Professional Milestone Timeline</span>
            </div>
            <div class="space-y-6">
              {"".join([f'<div class="border-l-2 border-[var(--accent)] pl-4 space-y-1"><div class="flex justify-between items-center"><h4 class="font-bold text-white text-sm">{e.job_title} · <span class="text-[var(--accent)]">{e.company}</span></h4><span class="text-xs text-slate-400 font-mono">{e.start_date} – {e.end_date}</span></div><p class="text-xs text-slate-300 pt-1 leading-relaxed">{" ".join([b.lstrip("•- ") for b in e.bullet_points[:2]])}</p></div>' for e in resume.work_experience])}
            </div>
          </div>
          ''' if resume.portfolio_show_experience else ''}

          <!-- Skills Showcase -->
          {f'''
          <div class="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 space-y-4">
            <div class="flex items-center gap-2 text-xl font-bold text-white border-b border-white/10 pb-4">
              <i data-lucide="cpu" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Technical Competencies</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
              {"".join([f'<div class="space-y-2"><h5 class="text-xs font-bold text-[var(--accent)] uppercase">{c.category_name}</h5><div class="flex flex-wrap gap-1.5">{"".join([f"<span class=\"px-2.5 py-1 text-xs bg-white/10 rounded-lg text-slate-200\">{s}</span>" for s in c.skills])}</div></div>' for c in resume.skill_categories])}
            </div>
          </div>
          ''' if resume.portfolio_show_skills else ''}

        </div>
      </div>
    '''


# ─────────────────────────────────────────────────────────────────────────────
# 6. KINETIC MOTION STUDIO TEMPLATE (Awwwards-Style Micro-Animations & 3D Tilt)
# ─────────────────────────────────────────────────────────────────────────────
def render_motion_zenith(resume: TailoredResume, accent: str) -> str:
    info = resume.personal_info
    full_name = info.full_name or "Candidate Name"
    role_title = resume.target_job_title or "Full Stack Software Engineer"
    summary = resume.professional_summary or ""
    avatar_url = info.avatar_url or ""
    badge_text = info.availability_badge or "Available for High-Impact Roles"
    cta_text = resume.portfolio_cta_text or "Initiate Collaboration"
    cta_url = resume.portfolio_cta_url or (
        f"mailto:{info.email}" if info.email else "#contact"
    )

    # Avatar with animated glowing rings
    if avatar_url:
        avatar_elem = f"""
          <div class="relative group">
            <div class="absolute -inset-1 rounded-3xl bg-gradient-to-r from-[var(--accent)] to-pink-500 opacity-70 blur-lg group-hover:opacity-100 transition duration-500 animate-pulse"></div>
            <img src="{avatar_url}" alt="{full_name}" class="relative w-32 h-32 sm:w-36 sm:h-36 rounded-2xl object-cover ring-2 ring-white/20 shadow-2xl">
          </div>
        """
    else:
        initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "MZ"
        avatar_elem = f"""
          <div class="relative group">
            <div class="absolute -inset-1 rounded-3xl bg-gradient-to-r from-[var(--accent)] to-pink-500 opacity-70 blur-lg group-hover:opacity-100 transition duration-500 animate-pulse"></div>
            <div class="relative w-32 h-32 rounded-2xl bg-slate-950 ring-2 ring-[var(--accent)] flex items-center justify-center text-3xl font-black text-white shadow-2xl">
              <span>{initials}</span>
            </div>
          </div>
        """

    # Dynamic Typewriter phrases
    phrases = [role_title]
    if resume.skill_categories:
        top_skills = [s for cat in resume.skill_categories for s in cat.skills[:2]]
        if top_skills:
            phrases.append(f"Crafting Modern {' & '.join(top_skills[:2])} Systems")
    phrases.append("Scalable Cloud & High-Impact Architecture")
    phrases_json = str(phrases).replace("'", '"')

    # Socials
    social_links = []
    for link in info.social_links:
        if link.enabled and link.url.strip():
            href = (
                link.url
                if link.url.startswith("http") or link.url.startswith("mailto:")
                else f"https://{link.url}"
            )
            icon = get_social_icon(link.name, link.icon)
            social_links.append(f"""
              <a href="{href}" target="_blank"
                class="p-3 rounded-2xl bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-white hover:border-[var(--accent)] hover:shadow-xl hover:shadow-[var(--accent-glow)] hover:-translate-y-1 transition transform duration-300 flex items-center gap-2 text-xs font-semibold">
                <i data-lucide="{icon}" class="w-4 h-4 text-[var(--accent)]"></i>
                <span>{link.name}</span>
              </a>
            """)
    if not social_links and info.email:
        social_links.append(f"""
          <a href="mailto:{info.email}" class="p-3 rounded-2xl bg-slate-900/90 border border-slate-800 text-slate-300 hover:text-white hover:border-[var(--accent)] hover:-translate-y-1 transition flex items-center gap-2 text-xs font-semibold">
            <i data-lucide="mail" class="w-4 h-4 text-[var(--accent)]"></i>
            <span>{info.email}</span>
          </a>
        """)
    socials_html = "".join(social_links)

    # 3D Tilt Project Cards
    project_cards = []
    for p in resume.projects:
        tech_tags = "".join(
            [
                f'<span class="px-2.5 py-0.5 text-[10px] font-mono bg-white/5 border border-white/10 text-slate-300 rounded-md">{t}</span>'
                for t in p.technologies
            ]
        )
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-400 leading-relaxed">• {b.lstrip("•- ")}</li>'
                for b in p.description_bullets[:2]
            ]
        )
        actions = []
        if p.demo_url:
            actions.append(
                f'<a href="{p.demo_url}" target="_blank" class="px-3.5 py-1.5 bg-[var(--accent)] hover:brightness-110 text-slate-950 font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-md shadow-[var(--accent-glow)] transition"><i data-lucide="play" class="w-3.5 h-3.5"></i> Live Demo</a>'
            )
        if p.link:
            actions.append(
                f'<a href="{p.link}" target="_blank" class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium rounded-xl text-xs flex items-center gap-1.5 transition"><i data-lucide="github" class="w-3.5 h-3.5"></i> Source</a>'
            )

        project_cards.append(f"""
          <div class="tilt-card bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 hover:border-[var(--accent)] rounded-3xl p-6 sm:p-7 flex flex-col justify-between space-y-4 shadow-xl transition-all duration-300 group">
            <div class="space-y-3">
              <div class="flex items-center justify-between">
                <div class="w-10 h-10 rounded-2xl bg-[var(--accent-glow)] border border-[var(--accent)] flex items-center justify-center text-[var(--accent)] font-bold group-hover:rotate-6 transition transform">
                  <i data-lucide="sparkles" class="w-5 h-5"></i>
                </div>
                <div class="flex flex-wrap gap-1 justify-end">{tech_tags}</div>
              </div>
              <h4 class="text-lg font-bold text-white group-hover:text-[var(--accent)] transition">{p.name}</h4>
              <ul class="space-y-1.5">{bullets}</ul>
            </div>
            <div class="flex items-center gap-2 pt-3 border-t border-slate-800/80">{"".join(actions)}</div>
          </div>
        """)

    # Animated Skill Bars
    skill_bars_html = []
    for cat in resume.skill_categories:
        cat_items = []
        for s in cat.skills[:4]:
            lvl = cat.skill_levels.get(s, 90)
            cat_items.append(f"""
              <div class="space-y-1">
                <div class="flex justify-between text-xs font-semibold">
                  <span class="text-slate-200">{s}</span>
                  <span class="text-[var(--accent)] font-mono">{lvl}%</span>
                </div>
                <div class="w-full h-2 rounded-full bg-slate-950 border border-slate-800 overflow-hidden">
                  <div class="h-full rounded-full bg-gradient-to-r from-[var(--accent)] to-pink-500 transition-all duration-1000 ease-out" style="width: {lvl}%"></div>
                </div>
              </div>
            """)
        skill_bars_html.append(f"""
          <div class="p-5 bg-slate-900/60 border border-slate-800/80 rounded-2xl space-y-3">
            <h5 class="text-xs font-bold uppercase tracking-wider text-[var(--accent)] flex items-center gap-1.5">
              <i data-lucide="cpu" class="w-3.5 h-3.5"></i> {cat.category_name}
            </h5>
            <div class="space-y-2.5">{"".join(cat_items)}</div>
          </div>
        """)

    return f"""
      <div class="relative min-h-screen overflow-hidden py-14 px-4 sm:px-8">
        
        <!-- Ambient Drifting Gradient Mesh Orbs -->
        <div class="absolute -top-24 -left-24 w-[500px] h-[500px] rounded-full bg-[var(--accent)] blur-[150px] opacity-20 pointer-events-none animate-pulse"></div>
        <div class="absolute top-1/2 -right-24 w-[450px] h-[450px] rounded-full bg-pink-600 blur-[160px] opacity-15 pointer-events-none animate-pulse"></div>
        <div class="absolute -bottom-24 left-1/3 w-[450px] h-[450px] rounded-full bg-violet-600 blur-[160px] opacity-15 pointer-events-none"></div>

        <div class="max-w-6xl mx-auto space-y-14 relative z-10">
          
          <!-- Hero Kinetic Card -->
          <div class="bg-slate-900/70 backdrop-blur-2xl border border-slate-800/90 rounded-3xl p-8 sm:p-12 shadow-2xl flex flex-col md:flex-row items-center gap-8 relative overflow-hidden">
            <div class="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-[var(--accent-glow)] to-transparent rounded-bl-full pointer-events-none opacity-40"></div>
            
            {avatar_elem}

            <div class="space-y-4 text-center md:text-left flex-1">
              <div class="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold shadow-inner">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                <span>{badge_text}</span>
              </div>
              
              <div class="space-y-1">
                <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">{full_name}</h1>
                <div class="text-lg sm:text-2xl font-bold min-h-[36px] flex items-center justify-center md:justify-start">
                  <span id="typewriterTarget" class="text-[var(--accent)]"></span>
                  <span class="w-0.5 h-6 bg-[var(--accent)] inline-block ml-1 animate-pulse"></span>
                </div>
              </div>

              {f'<p class="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-2xl">{summary}</p>' if resume.portfolio_show_bio else ''}

              <div class="flex flex-wrap items-center justify-center md:justify-start gap-3 pt-2">
                <a href="{cta_url}" class="px-6 py-3 bg-[var(--accent)] hover:brightness-110 text-slate-950 font-extrabold text-xs rounded-2xl shadow-xl shadow-[var(--accent-glow)] hover:-translate-y-0.5 transition transform flex items-center gap-2">
                  <i data-lucide="zap" class="w-4 h-4"></i>
                  <span>{cta_text}</span>
                </a>
                {f'''
                <button onclick="window.parent.postMessage('download_resume', '*')"
                  class="px-5 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-semibold text-xs rounded-2xl shadow hover:-translate-y-0.5 transition transform flex items-center gap-2">
                  <i data-lucide="download" class="w-4 h-4 text-[var(--accent)]"></i>
                  <span>Download ATS Resume</span>
                </button>
                ''' if resume.portfolio_show_resume_download else ''}
              </div>

              <div class="pt-2 flex justify-center md:justify-start">{socials_html}</div>
            </div>
          </div>

          <!-- Featured Projects Spotlight (3D Tilt Grid) -->
          {f'''
          <div class="space-y-6">
            <div class="flex items-center justify-between border-b border-slate-800 pb-4">
              <div class="flex items-center gap-2.5 text-xl font-bold text-white">
                <i data-lucide="layers" class="w-5 h-5 text-[var(--accent)] animate-bounce"></i>
                <span>Featured Systems & Deployments</span>
              </div>
              <span class="text-xs font-mono text-slate-400">Interactive 3D Hover</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">{"".join(project_cards)}</div>
          </div>
          ''' if resume.portfolio_show_projects else ''}

          <!-- Skills Arsenal (Animated Percentage Bars) -->
          {f'''
          <div class="space-y-6">
            <div class="flex items-center gap-2.5 text-xl font-bold text-white border-b border-slate-800 pb-4">
              <i data-lucide="cpu" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Core Technical Stack & Proficiency</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">{"".join(skill_bars_html)}</div>
          </div>
          ''' if resume.portfolio_show_skills else ''}

          <!-- Experience Milestones -->
          {f'''
          <div class="bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 rounded-3xl p-8 space-y-6 shadow-xl">
            <div class="flex items-center gap-2.5 text-xl font-bold text-white border-b border-slate-800 pb-4">
              <i data-lucide="briefcase" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Career Trajectory</span>
            </div>
            <div class="space-y-6">
              {"".join([f'<div class="relative pl-6 border-l-2 border-[var(--accent)] space-y-1.5"><div class="absolute -left-[7px] top-1.5 w-3 h-3 rounded-full bg-[var(--accent)] ring-4 ring-[var(--accent-glow)]"></div><div class="flex flex-wrap justify-between items-center"><h4 class="font-bold text-sm text-white">{e.job_title} · <span class="text-[var(--accent)]">{e.company}</span></h4><span class="text-xs font-mono text-slate-400 bg-slate-950 px-2.5 py-0.5 rounded-full border border-slate-800">{e.start_date} – {e.end_date}</span></div><p class="text-xs text-slate-300 leading-relaxed pt-1">{" ".join([b.lstrip("•- ") for b in e.bullet_points[:2]])}</p></div>' for e in resume.work_experience])}
            </div>
          </div>
          ''' if resume.portfolio_show_experience else ''}

        </div>
      </div>

      <!-- Typewriter & 3D Tilt Script -->
      <script>
        // 1. Kinetic Typewriter Engine
        const phrases = {phrases_json};
        let pIdx = 0;
        let cIdx = 0;
        let isDeleting = false;
        const target = document.getElementById('typewriterTarget');

        function typeLoop() {{
          if (!target) return;
          const currentPhrase = phrases[pIdx];
          if (isDeleting) {{
            target.textContent = currentPhrase.substring(0, cIdx - 1);
            cIdx--;
          }} else {{
            target.textContent = currentPhrase.substring(0, cIdx + 1);
            cIdx++;
          }}

          let delay = isDeleting ? 40 : 90;
          if (!isDeleting && cIdx === currentPhrase.length) {{
            delay = 2000;
            isDeleting = true;
          }} else if (isDeleting && cIdx === 0) {{
            isDeleting = false;
            pIdx = (pIdx + 1) % phrases.length;
            delay = 400;
          }}
          setTimeout(typeLoop, delay);
        }}
        typeLoop();

        // 2. Interactive 3D Perspective Tilt on Hover
        document.querySelectorAll('.tilt-card').forEach(card => {{
          card.addEventListener('mousemove', e => {{
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left - (rect.width / 2);
            const y = e.clientY - rect.top - (rect.height / 2);
            const rotX = -(y / (rect.height / 2)) * 6;
            const rotY = (x / (rect.width / 2)) * 6;
            card.style.transform = `perspective(1000px) rotateX(${{rotX}}deg) rotateY(${{rotY}}deg) translateY(-4px)`;
          }});
          card.addEventListener('mouseleave', () => {{
            card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0)';
          }});
        }});
      </script>
    """


# ─────────────────────────────────────────────────────────────────────────────
# 7. INTERACTIVE PARTICLE CONSTELLATION GALAXY TEMPLATE (HTML5 60fps Canvas)
# ─────────────────────────────────────────────────────────────────────────────
def render_galaxy_canvas(resume: TailoredResume, accent: str) -> str:
    info = resume.personal_info
    full_name = info.full_name or "Candidate Name"
    role_title = resume.target_job_title or "Software Developer"
    summary = resume.professional_summary or ""
    avatar_url = info.avatar_url or ""
    cta_text = resume.portfolio_cta_text or "Connect with Me"
    cta_url = resume.portfolio_cta_url or (
        f"mailto:{info.email}" if info.email else "#contact"
    )

    # Counts
    num_projects = len(resume.projects)
    num_milestones = len(resume.work_experience)
    num_skills = sum(len(c.skills) for c in resume.skill_categories)

    # Avatar
    if avatar_url:
        avatar_elem = f'<img src="{avatar_url}" alt="{full_name}" class="w-24 h-24 sm:w-28 sm:h-28 rounded-full object-cover ring-4 ring-[var(--accent)] shadow-2xl shadow-[var(--accent-glow)]">'
    else:
        initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "GC"
        avatar_elem = f"""
          <div class="w-24 h-24 rounded-full bg-slate-900 border-2 border-[var(--accent)] shadow-2xl shadow-[var(--accent-glow)] flex items-center justify-center text-white font-extrabold text-2xl">
            <span>{initials}</span>
          </div>
        """

    # Projects
    projects_cards = []
    for p in resume.projects:
        tech = " · ".join(p.technologies[:4])
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-300 leading-relaxed">• {b.lstrip("•- ")}</li>'
                for b in p.description_bullets[:2]
            ]
        )
        actions = []
        if p.demo_url:
            actions.append(
                f'<a href="{p.demo_url}" target="_blank" class="px-3 py-1 bg-[var(--accent)] text-slate-950 font-bold rounded-lg text-xs hover:brightness-110 transition flex items-center gap-1"><i data-lucide="play" class="w-3 h-3"></i> Live</a>'
            )
        if p.link:
            actions.append(
                f'<a href="{p.link}" target="_blank" class="px-3 py-1 bg-white/10 text-white rounded-lg text-xs hover:bg-white/20 transition flex items-center gap-1"><i data-lucide="github" class="w-3 h-3"></i> Code</a>'
            )

        projects_cards.append(f"""
          <div class="p-6 rounded-3xl bg-slate-900/50 backdrop-blur-xl border border-white/10 hover:border-[var(--accent)] transition duration-300 space-y-3 shadow-xl">
            <div class="flex items-center justify-between">
              <h4 class="font-bold text-base text-white">{p.name}</h4>
              <div class="flex items-center gap-2">{"".join(actions)}</div>
            </div>
            <p class="text-[11px] font-mono text-[var(--accent)]">{tech}</p>
            <ul class="space-y-1">{bullets}</ul>
          </div>
        """)

    return f"""
      <div class="relative min-h-screen text-slate-100 py-16 px-4 sm:px-8">
        
        <!-- Interactive HTML5 Constellation Canvas -->
        <canvas id="galaxyCanvas" class="fixed inset-0 pointer-events-auto z-0 opacity-70"></canvas>

        <div class="max-w-5xl mx-auto space-y-16 relative z-10 pointer-events-none">
          
          <!-- Hero Section -->
          <div class="p-8 sm:p-12 rounded-3xl bg-slate-900/60 backdrop-blur-2xl border border-white/10 shadow-2xl text-center space-y-6 pointer-events-auto">
            <div class="flex justify-center">{avatar_elem}</div>
            <div class="space-y-2">
              <div class="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                <span>{info.availability_badge or "Online & Ready"}</span>
              </div>
              <h1 class="text-3xl sm:text-6xl font-black text-white tracking-tight">{full_name}</h1>
              <p class="text-base sm:text-xl font-semibold text-[var(--accent)]">{role_title}</p>
            </div>
            {f'<p class="text-xs sm:text-sm text-slate-300 max-w-2xl mx-auto leading-relaxed">{summary}</p>' if resume.portfolio_show_bio else ''}

            <!-- Counting Metrics Animation Cards -->
            <div class="grid grid-cols-3 gap-3 max-w-lg mx-auto pt-2">
              <div class="p-3 bg-black/40 rounded-2xl border border-white/10">
                <span class="counter-num text-2xl sm:text-3xl font-black text-[var(--accent)]" data-target="{num_projects}">0</span>
                <span class="text-xl font-black text-[var(--accent)]">+</span>
                <p class="text-[10px] text-slate-400 font-semibold uppercase">Projects</p>
              </div>
              <div class="p-3 bg-black/40 rounded-2xl border border-white/10">
                <span class="counter-num text-2xl sm:text-3xl font-black text-white" data-target="{num_milestones}">0</span>
                <p class="text-[10px] text-slate-400 font-semibold uppercase">Milestones</p>
              </div>
              <div class="p-3 bg-black/40 rounded-2xl border border-white/10">
                <span class="counter-num text-2xl sm:text-3xl font-black text-pink-400" data-target="{num_skills}">0</span>
                <p class="text-[10px] text-slate-400 font-semibold uppercase">Stack Skills</p>
              </div>
            </div>

            <div class="flex flex-wrap justify-center gap-3 pt-2">
              <a href="{cta_url}" class="px-6 py-3 bg-[var(--accent)] hover:brightness-110 text-slate-950 font-extrabold text-xs rounded-2xl shadow-xl shadow-[var(--accent-glow)] transition flex items-center gap-2">
                <i data-lucide="sparkles" class="w-4 h-4"></i>
                <span>{cta_text}</span>
              </a>
              {f'''
              <button onclick="window.parent.postMessage('download_resume', '*')"
                class="px-5 py-3 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-semibold text-xs rounded-2xl transition flex items-center gap-2">
                <i data-lucide="download" class="w-4 h-4 text-[var(--accent)]"></i>
                <span>Download ATS CV</span>
              </button>
              ''' if resume.portfolio_show_resume_download else ''}
            </div>
          </div>

          <!-- Featured Projects Grid -->
          {f'''
          <div class="space-y-6 pointer-events-auto">
            <div class="flex items-center gap-2.5 text-xl font-bold text-white">
              <i data-lucide="layers" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Featured Creations & Architectures</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">{"".join(projects_cards)}</div>
          </div>
          ''' if resume.portfolio_show_projects else ''}

          <!-- Experience Timeline -->
          {f'''
          <div class="p-8 rounded-3xl bg-slate-900/60 backdrop-blur-2xl border border-white/10 space-y-6 shadow-2xl pointer-events-auto">
            <div class="flex items-center gap-2.5 text-xl font-bold text-white border-b border-white/10 pb-4">
              <i data-lucide="briefcase" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Experience Log</span>
            </div>
            <div class="space-y-6">
              {"".join([f'<div class="border-l-2 border-[var(--accent)] pl-4 space-y-1"><div class="flex justify-between items-center"><h4 class="font-bold text-white text-sm">{e.job_title} · <span class="text-[var(--accent)]">{e.company}</span></h4><span class="text-xs text-slate-400 font-mono">{e.start_date} – {e.end_date}</span></div><p class="text-xs text-slate-300 pt-1 leading-relaxed">{" ".join([b.lstrip("•- ") for b in e.bullet_points[:2]])}</p></div>' for e in resume.work_experience])}
            </div>
          </div>
          ''' if resume.portfolio_show_experience else ''}

        </div>

      </div>

      <!-- HTML5 Interactive Particle Constellation & Counters Script -->
      <script>
        // 1. Constellation Particle Engine (60fps)
        const canvas = document.getElementById('galaxyCanvas');
        if (canvas) {{
          const ctx = canvas.getContext('2d');
          let width = canvas.width = window.innerWidth;
          let height = canvas.height = window.innerHeight;

          window.addEventListener('resize', () => {{
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
          }});

          const particles = [];
          const count = Math.min(80, Math.floor(width / 18));
          const mouse = {{ x: null, y: null }};

          window.addEventListener('mousemove', e => {{
            mouse.x = e.clientX;
            mouse.y = e.clientY;
          }});
          window.addEventListener('mouseleave', () => {{
            mouse.x = null;
            mouse.y = null;
          }});

          for (let i = 0; i < count; i++) {{
            particles.push({{
              x: Math.random() * width,
              y: Math.random() * height,
              vx: (Math.random() - 0.5) * 0.8,
              vy: (Math.random() - 0.5) * 0.8,
              radius: Math.random() * 2 + 1
            }});
          }}

          function animateCanvas() {{
            ctx.clearRect(0, 0, width, height);

            for (let i = 0; i < particles.length; i++) {{
              const p = particles[i];
              p.x += p.vx;
              p.y += p.vy;
              if (p.x < 0 || p.x > width) p.vx *= -1;
              if (p.y < 0 || p.y > height) p.vy *= -1;

              ctx.beginPath();
              ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
              ctx.fillStyle = '{accent}';
              ctx.globalAlpha = 0.6;
              ctx.fill();

              // Connect nearby particles
              for (let j = i + 1; j < particles.length; j++) {{
                const p2 = particles[j];
                const dx = p.x - p2.x;
                const dy = p.y - p2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 110) {{
                  ctx.beginPath();
                  ctx.moveTo(p.x, p.y);
                  ctx.lineTo(p2.x, p2.y);
                  ctx.strokeStyle = '{accent}';
                  ctx.globalAlpha = 0.25 * (1 - dist / 110);
                  ctx.stroke();
                }}
              }}

              // Connect to mouse cursor
              if (mouse.x !== null) {{
                const dx = p.x - mouse.x;
                const dy = p.y - mouse.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 140) {{
                  ctx.beginPath();
                  ctx.moveTo(p.x, p.y);
                  ctx.lineTo(mouse.x, mouse.y);
                  ctx.strokeStyle = '#f43f5e';
                  ctx.globalAlpha = 0.4 * (1 - dist / 140);
                  ctx.stroke();
                }}
              }}
            }}

            requestAnimationFrame(animateCanvas);
          }}
          animateCanvas();
        }}

        // 2. Metric Counters Roll-up Animation
        document.querySelectorAll('.counter-num').forEach(c => {{
          const target = +c.getAttribute('data-target');
          if (!target) return;
          const duration = 1200;
          const step = Math.max(1, Math.floor(target / 30));
          let current = 0;
          const timer = setInterval(() => {{
            current += step;
            if (current >= target) {{
              c.textContent = target;
              clearInterval(timer);
            }} else {{
              c.textContent = current;
            }}
          }}, 35);
        }});
      </script>
    """


# ─────────────────────────────────────────────────────────────────────────────
# 8. AURORA WHITE TEMPLATE (Scandinavian / Minimalist Clean Light Edition)
# ─────────────────────────────────────────────────────────────────────────────
def render_aurora_white(resume: TailoredResume, accent: str) -> str:
    info = resume.personal_info
    full_name = info.full_name or "Candidate Name"
    role_title = resume.target_job_title or "Software Engineer"
    summary = resume.professional_summary or ""
    avatar_url = info.avatar_url or ""
    badge_text = info.availability_badge or "Available for High-Impact Roles"
    cta_text = resume.portfolio_cta_text or "Get in Touch"
    cta_url = resume.portfolio_cta_url or (f"mailto:{info.email}" if info.email else "#contact")

    # Avatar
    if avatar_url:
        avatar_elem = f'<img src="{avatar_url}" alt="{full_name}" class="w-28 h-28 sm:w-32 sm:h-32 rounded-3xl object-cover ring-4 ring-white shadow-xl shadow-slate-200/80">'
    else:
        initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "AW"
        avatar_elem = f'''
          <div class="w-28 h-28 sm:w-32 sm:h-32 rounded-3xl bg-gradient-to-tr from-slate-100 to-slate-200 p-1 shadow-xl shadow-slate-200/80 flex items-center justify-center">
            <div class="w-full h-full bg-white rounded-3xl flex items-center justify-center text-slate-800 text-3xl font-black">
              {initials}
            </div>
          </div>
        '''

    # Social icons
    socials = []
    for link in info.social_links:
        if link.enabled and link.url.strip():
            href = link.url if link.url.startswith("http") or link.url.startswith("mailto:") else f"https://{link.url}"
            svg = get_social_svg(link.name, link.icon, "w-4 h-4 text-slate-600 group-hover:text-slate-950 transition-colors")
            socials.append(f'''
              <a href="{href}" target="_blank" title="{link.name}"
                 class="group p-2.5 rounded-xl bg-white border border-slate-200/80 shadow-sm hover:border-slate-400 hover:shadow-md transition flex items-center justify-center">
                {svg}
              </a>
            ''')
    if info.email and not any("mail" in l.name.lower() for l in info.social_links if l.enabled):
        email_svg = get_social_svg("mail", "mail", "w-4 h-4 text-slate-600 group-hover:text-slate-950 transition-colors")
        socials.append(f'''
          <a href="mailto:{info.email}" title="Email"
             class="group p-2.5 rounded-xl bg-white border border-slate-200/80 shadow-sm hover:border-slate-400 hover:shadow-md transition flex items-center justify-center">
            {email_svg}
          </a>
        ''')
    socials_html = "".join(socials)

    # Metrics
    if resume.portfolio_metrics:
        metrics = resume.portfolio_metrics
    else:
        metrics = [
            {"label": "Key Projects", "value": f"{len(resume.projects)}+"},
            {"label": "Experience", "value": f"{len(resume.work_experience)}+ Yrs"},
            {"label": "System Reliability", "value": "99.98%"},
            {"label": "Core Competencies", "value": f"{sum(len(c.skills) for c in resume.skill_categories)}+"}
        ]

    metrics_html = "".join([f'''
      <div class="p-5 bg-white border border-slate-200/80 rounded-2xl shadow-sm hover:shadow-md hover:border-slate-300 transition text-center space-y-1">
        <div class="text-3xl font-black text-slate-900 font-mono tracking-tight">{m.get("value", "0")}</div>
        <p class="text-[11px] font-bold uppercase tracking-wider text-slate-500">{m.get("label", "Metric")}</p>
      </div>
    ''' for m in metrics[:4]])

    # Projects
    projects_html = []
    for idx, p in enumerate(resume.projects):
        tech_tags = "".join([f'<span class="px-2.5 py-1 text-xs font-mono bg-slate-100 border border-slate-200/60 text-slate-700 rounded-lg">{t}</span>' for t in p.technologies])
        bullets = "".join([f'<li class="text-xs text-slate-600 leading-relaxed flex items-start gap-2"><span class="text-[var(--accent)] font-bold mt-0.5">▪</span><span>{b.lstrip("•- ")}</span></li>' for b in p.description_bullets])
        actions = []
        if p.demo_url:
            actions.append(f'<a href="{p.demo_url}" target="_blank" class="px-4 py-2 bg-slate-900 text-white rounded-xl text-xs font-bold hover:bg-slate-800 transition flex items-center gap-1.5 shadow-sm"><span>Live Demo</span> <span class="text-xs">→</span></a>')
        if p.link:
            actions.append(f'<a href="{p.link}" target="_blank" class="px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-xl text-xs font-semibold hover:border-slate-300 hover:bg-slate-50 transition flex items-center gap-1.5"><span>Source Code</span></a>')

        projects_html.append(f'''
          <div class="bg-white border border-slate-200/80 rounded-3xl p-6 sm:p-8 shadow-sm hover:shadow-xl hover:border-[var(--accent)] transition-all duration-300 space-y-4 group">
            <div class="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div class="space-y-1">
                <span class="text-xs font-mono text-[var(--accent)] font-bold">PROJECT {idx+1:02d}</span>
                <h4 class="text-xl font-bold text-slate-900 group-hover:text-[var(--accent)] transition">{p.name}</h4>
              </div>
              <div class="flex flex-wrap gap-2">{"".join(actions)}</div>
            </div>
            <ul class="space-y-1.5 max-w-3xl">{bullets}</ul>
            <div class="flex flex-wrap gap-1.5 pt-2">{tech_tags}</div>
          </div>
        ''')

    # Skills with clean light progress bars
    skills_html = []
    for cat in resume.skill_categories:
        skill_bars = []
        for s in cat.skills:
            level = cat.skill_levels.get(s, 85) if cat.skill_levels else 85
            skill_bars.append(f'''
              <div class="space-y-1.5">
                <div class="flex justify-between text-xs">
                  <span class="font-semibold text-slate-800">{s}</span>
                  <span class="font-mono text-slate-500 font-bold">{level}%</span>
                </div>
                <div class="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div class="h-full rounded-full bg-[var(--accent)] transition-all duration-1000" style="width: {level}%"></div>
                </div>
              </div>
            ''')
        skills_html.append(f'''
          <div class="bg-white border border-slate-200/80 rounded-3xl p-6 shadow-sm hover:shadow-md transition space-y-4">
            <h5 class="text-xs font-bold uppercase tracking-wider text-slate-900 border-b border-slate-100 pb-2.5 flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-[var(--accent)]"></span>
              {cat.category_name}
            </h5>
            <div class="space-y-3">{"".join(skill_bars)}</div>
          </div>
        ''')

    # Experience Milestones
    exp_html = []
    for exp in resume.work_experience:
        bullets = "".join([f'<li class="text-xs text-slate-600 leading-relaxed">• {b.lstrip("•- ")}</li>' for b in exp.bullet_points[:3]])
        exp_html.append(f'''
          <div class="relative pl-8 pb-8 border-l-2 border-slate-200 last:border-0">
            <div class="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full bg-white border-2 border-[var(--accent)] shadow-sm"></div>
            <div class="space-y-1">
              <div class="flex flex-wrap justify-between items-baseline gap-2">
                <h4 class="font-bold text-slate-900 text-base">{exp.job_title}</h4>
                <span class="text-xs font-mono text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-full">{exp.start_date} – {exp.end_date}</span>
              </div>
              <p class="text-xs font-semibold text-[var(--accent)]">{exp.company} {f"· {exp.location}" if exp.location else ""}</p>
              <ul class="space-y-1 pt-2">{bullets}</ul>
            </div>
          </div>
        ''')

    return f'''
      <div class="min-h-screen bg-[#FAFAFC] text-slate-900">
        
        <!-- Subtle Top Ambient Glow -->
        <div class="absolute top-0 inset-x-0 h-96 bg-gradient-to-b from-slate-100 via-transparent to-transparent pointer-events-none -z-10"></div>

        <!-- Sticky Light Header -->
        <header class="sticky top-0 z-30 bg-white/80 backdrop-blur border-b border-slate-200/80">
          <div class="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
            <div class="flex items-center gap-2.5">
              <span class="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center font-bold text-xs font-mono">
                {full_name[:2].upper()}
              </span>
              <span class="font-bold text-slate-900 text-sm tracking-tight">{full_name}</span>
            </div>

            <nav class="hidden md:flex items-center gap-6 text-xs font-semibold text-slate-600">
              <a href="#projects" class="hover:text-slate-900 transition">Projects</a>
              <a href="#experience" class="hover:text-slate-900 transition">Experience</a>
              <a href="#skills" class="hover:text-slate-900 transition">Skills</a>
              <a href="#contact" class="hover:text-slate-900 transition">Contact</a>
            </nav>

            <div class="flex items-center gap-2.5">
              {f'''
              <button onclick="window.parent.postMessage('download_resume', '*')"
                class="px-3.5 py-2 bg-white border border-slate-200 hover:border-slate-400 text-slate-700 rounded-xl text-xs font-semibold shadow-sm transition flex items-center gap-1.5">
                <i data-lucide="download" class="w-3.5 h-3.5 text-slate-600"></i>
                <span class="hidden sm:inline">Resume PDF</span>
              </button>
              ''' if resume.portfolio_show_resume_download else ''}
              <a href="{cta_url}"
                class="px-4 py-2 bg-[var(--accent)] hover:brightness-105 text-white rounded-xl text-xs font-bold shadow-md shadow-[var(--accent-glow)] transition">
                {cta_text}
              </a>
            </div>
          </div>
        </header>

        <!-- Main Body -->
        <main class="max-w-6xl mx-auto px-4 sm:px-6 py-12 sm:py-16 space-y-16 sm:space-y-20">

          <!-- HERO SECTION -->
          <section class="bg-white border border-slate-200/80 rounded-3xl p-8 sm:p-12 shadow-sm relative overflow-hidden flex flex-col sm:flex-row items-center sm:items-start gap-8">
            {avatar_elem}
            <div class="space-y-4 text-center sm:text-left flex-1">
              <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-semibold">
                <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span>{badge_text}</span>
              </div>
              <div class="space-y-1">
                <h1 class="text-3xl sm:text-5xl font-black tracking-tight text-slate-900">{full_name}</h1>
                <p class="text-lg sm:text-2xl font-bold text-[var(--accent)]">{role_title}</p>
                <p class="text-xs text-slate-500 font-medium">{info.location or "Global / Remote"}</p>
              </div>
              {f'<p class="text-sm sm:text-base text-slate-600 leading-relaxed max-w-2xl pt-1">{summary}</p>' if resume.portfolio_show_bio else ''}
              
              <div class="flex flex-wrap items-center gap-3 pt-2 justify-center sm:justify-start">
                <a href="{cta_url}" class="px-6 py-3 bg-[var(--accent)] text-white font-bold rounded-xl text-xs hover:brightness-105 shadow-md shadow-[var(--accent-glow)] transition">
                  {cta_text} →
                </a>
                {f'''
                <button onclick="window.parent.postMessage('download_resume', '*')"
                  class="px-5 py-3 bg-white border border-slate-200 hover:border-slate-300 text-slate-800 rounded-xl text-xs font-semibold shadow-sm transition">
                  Download CV Monograph
                </button>
                ''' if resume.portfolio_show_resume_download else ''}
                <div class="flex items-center gap-1.5 pl-2">{socials_html}</div>
              </div>
            </div>
          </section>

          <!-- METRICS HIGHLIGHTS -->
          <section class="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {metrics_html}
          </section>

          <!-- PROJECTS SHOWCASE -->
          {f'''
          <section id="projects" class="space-y-6">
            <div class="flex justify-between items-baseline border-b border-slate-200 pb-4">
              <div class="space-y-1">
                <span class="text-xs font-mono uppercase tracking-wider text-[var(--accent)] font-bold">PORTFOLIO EXHIBITS</span>
                <h2 class="text-2xl font-black text-slate-900 tracking-tight">Featured Engineering Projects</h2>
              </div>
              <span class="text-xs font-mono text-slate-500">{len(resume.projects)} Systems</span>
            </div>
            <div class="space-y-6">{"".join(projects_html)}</div>
          </section>
          ''' if resume.portfolio_show_projects else ''}

          <!-- SKILLS ARSENAL -->
          {f'''
          <section id="skills" class="space-y-6">
            <div class="border-b border-slate-200 pb-4 space-y-1">
              <span class="text-xs font-mono uppercase tracking-wider text-[var(--accent)] font-bold">TECHNICAL MATRIX</span>
              <h2 class="text-2xl font-black text-slate-900 tracking-tight">Core Competencies & Stack</h2>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">{"".join(skills_html)}</div>
          </section>
          ''' if resume.portfolio_show_skills else ''}

          <!-- EXPERIENCE TIMELINE -->
          {f'''
          <section id="experience" class="space-y-6">
            <div class="border-b border-slate-200 pb-4 space-y-1">
              <span class="text-xs font-mono uppercase tracking-wider text-[var(--accent)] font-bold">CAREER TRAJECTORY</span>
              <h2 class="text-2xl font-black text-slate-900 tracking-tight">Milestones & Achievements</h2>
            </div>
            <div class="bg-white border border-slate-200/80 rounded-3xl p-8 sm:p-10 shadow-sm space-y-2">
              {"".join(exp_html)}
            </div>
          </section>
          ''' if resume.portfolio_show_experience else ''}

        </main>

        <!-- Minimalist Footer -->
        <footer id="contact" class="border-t border-slate-200 bg-white py-12 mt-20 text-xs text-slate-500">
          <div class="max-w-6xl mx-auto px-4 sm:px-6 flex flex-wrap justify-between items-center gap-4">
            <div class="space-y-1">
              <p class="font-bold text-slate-900">© 2026 {full_name}. All rights reserved.</p>
              <p class="text-[11px] text-slate-400">Crafted with ResuMatch AI · Clean Light Edition</p>
            </div>
            <div class="flex items-center gap-2">{socials_html}</div>
          </div>
        </footer>

      </div>
    '''


# ─────────────────────────────────────────────────────────────────────────────
# MASTER PORTFOLIO COMPOSER
# ─────────────────────────────────────────────────────────────────────────────
def generate_portfolio_html(resume: TailoredResume, theme: Optional[str] = None) -> str:
    """
    Generate responsive, standalone portfolio website matching the selected architectural template.
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

    full_name = safe_resume.personal_info.full_name or "Professional Portfolio"
    role_title = safe_resume.target_job_title or "Portfolio"
    summary = safe_resume.professional_summary or ""

    return f"""<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{full_name} — {role_title} | Portfolio</title>
  
  <meta name="description" content="{summary[:160]}">
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
<body class="{body_bg} min-h-screen antialiased selection:bg-[var(--accent)] selection:text-black">
  {layout_html}

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
