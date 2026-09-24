"""
Theme: Bento Grid (Apple / Linear Style)
Features:
- High-aesthetic multi-card modular bento grid layout
- Tech stack chips, featured metrics, interactive project cards
- Dark slate background with dynamic glow accents
"""
import os
import io
import re
import html
import json
from typing import List, Optional, Dict, Any
from app.schemas import TailoredResume
from app.portfolio_templates.common import (
    sanitize_text, sanitize_url, get_social_svg, get_social_icon, hex_to_rgba
)

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

    bio_html = f'<p class="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-xl">{summary}</p>' if resume.portfolio_show_bio else ''

    joined_skills_badges = "".join(skills_badges)
    skills_card_html = f'''
          <div class="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-3xl p-6 space-y-4 shadow-xl">
            <div class="flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
              <i data-lucide="cpu" class="w-4 h-4 text-[var(--accent)]"></i>
              <span>Technical Arsenal</span>
            </div>
            <div class="space-y-4">{joined_skills_badges}</div>
          </div>
    ''' if resume.portfolio_show_skills else ''

    proj_col = "lg:col-span-2" if resume.portfolio_show_skills else "lg:col-span-3"
    joined_project_cards = "".join(project_cards)
    projects_card_html = f'''
          <div class="{proj_col} bg-slate-900/70 backdrop-blur border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-4 shadow-xl">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
              <div class="flex items-center gap-2 text-sm font-bold text-white">
                <i data-lucide="layers" class="w-4 h-4 text-[var(--accent)]"></i>
                <span>Featured Systems & Projects</span>
              </div>
              <span class="text-[11px] text-slate-400 font-mono">{len(resume.projects)} Production Builds</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">{joined_project_cards}</div>
          </div>
    ''' if resume.portfolio_show_projects else ''

    exp_col = "lg:col-span-2" if resume.portfolio_show_education else "lg:col-span-3"
    joined_exp_cards = "".join(exp_cards)
    exp_card_html = f'''
          <div class="{exp_col} bg-slate-900/70 backdrop-blur border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-4 shadow-xl">
            <div class="flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
              <i data-lucide="briefcase" class="w-4 h-4 text-[var(--accent)]"></i>
              <span>Career Trajectory</span>
            </div>
            <div class="pt-2 space-y-4">{joined_exp_cards}</div>
          </div>
    ''' if resume.portfolio_show_experience else ''

    joined_edu_badges = "".join(edu_badges)
    edu_card_html = f'''
          <div class="bg-slate-900/70 backdrop-blur border border-slate-800 rounded-3xl p-6 space-y-4 shadow-xl">
            <div class="flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
              <i data-lucide="graduation-cap" class="w-4 h-4 text-[var(--accent)]"></i>
              <span>Qualifications</span>
            </div>
            <div class="space-y-3">{joined_edu_badges}</div>
          </div>
    ''' if resume.portfolio_show_education else ''

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
              {bio_html}
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
          {skills_card_html}

          <!-- Bento Card 4: Featured Projects Spotlight (2 Cols) -->
          {projects_card_html}

        </div>

        <!-- BENTO ROW 3: Experience & Education -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          <!-- Bento Card 5: Experience Timeline (2 Cols) -->
          {exp_card_html}

          <!-- Bento Card 6: Education & Credentials (1 Col) -->
          {edu_card_html}

        </div>

      </div>
    """


# ─────────────────────────────────────────────────────────────────────────────
# 2. SPLIT SIDEBAR TEMPLATE (Executive Split-Screen / Senior Director)
# ─────────────────────────────────────────────────────────────────────────────
