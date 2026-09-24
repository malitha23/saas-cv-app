"""
Theme: Neon Glass (Neo-Glassmorphism 3D Glow)
Features:
- Frosted glass cards with backdrop blur and cosmic radial gradients
- Neon border glows with customizable accent palette
- Modern futuristic aesthetic
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

    bio_html = f'<p class="text-sm sm:text-base text-slate-300 max-w-2xl mx-auto leading-relaxed">{summary}</p>' if resume.portfolio_show_bio else ''

    resume_btn_html = f'''
              <button onclick="window.parent.postMessage('download_resume', '*')"
                class="px-5 py-3 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-semibold text-xs rounded-xl transition flex items-center gap-2">
                <i data-lucide="file-down" class="w-4 h-4 text-[var(--accent)]"></i>
                <span>Download ATS CV</span>
              </button>
    ''' if resume.portfolio_show_resume_download else ''

    joined_projects = "".join(projects)
    projects_showcase_html = f'''
          <div class="space-y-6">
            <div class="flex items-center gap-2 text-xl font-bold text-white">
              <i data-lucide="layers" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Featured Creations & Systems</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">{joined_projects}</div>
          </div>
    ''' if resume.portfolio_show_projects else ''

    exp_items_list = []
    for e in resume.work_experience:
        bp_text = " ".join([b.lstrip("•- ") for b in e.bullet_points[:2]])
        exp_items_list.append(f'<div class="border-l-2 border-[var(--accent)] pl-4 space-y-1"><div class="flex justify-between items-center"><h4 class="font-bold text-white text-sm">{e.job_title} · <span class="text-[var(--accent)]">{e.company}</span></h4><span class="text-xs text-slate-400 font-mono">{e.start_date} – {e.end_date}</span></div><p class="text-xs text-slate-300 pt-1 leading-relaxed">{bp_text}</p></div>')
    joined_exp_items = "".join(exp_items_list)

    exp_showcase_html = f'''
          <div class="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 space-y-6 shadow-xl">
            <div class="flex items-center gap-2 text-xl font-bold text-white border-b border-white/10 pb-4">
              <i data-lucide="briefcase" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Professional Milestone Timeline</span>
            </div>
            <div class="space-y-6">
              {joined_exp_items}
            </div>
          </div>
    ''' if resume.portfolio_show_experience else ''

    skill_cards_list = []
    for c in resume.skill_categories:
        rendered_skills = "".join([f'<span class="px-2.5 py-1 text-xs bg-white/10 rounded-lg text-slate-200">{s}</span>' for s in c.skills])
        skill_cards_list.append(f'<div class="space-y-2"><h5 class="text-xs font-bold text-[var(--accent)] uppercase">{c.category_name}</h5><div class="flex flex-wrap gap-1.5">{rendered_skills}</div></div>')
    joined_skill_cards = "".join(skill_cards_list)

    skills_showcase_html = f'''
          <div class="bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 space-y-4">
            <div class="flex items-center gap-2 text-xl font-bold text-white border-b border-white/10 pb-4">
              <i data-lucide="cpu" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Technical Competencies</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-6">
              {joined_skill_cards}
            </div>
          </div>
    ''' if resume.portfolio_show_skills else ''

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
            {bio_html}
            
            <div class="flex flex-wrap justify-center gap-3 pt-2">
              <a href="{cta_url}" class="px-6 py-3 bg-[var(--accent)] text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-[var(--accent-glow)] hover:brightness-110 transition flex items-center gap-2">
                <i data-lucide="sparkles" class="w-4 h-4"></i>
                <span>{cta_text}</span>
              </a>
              {resume_btn_html}
            </div>

            {socials_bar}
          </div>

          <!-- Projects Showcase -->
          {projects_showcase_html}

          <!-- Experience Showcase -->
          {exp_showcase_html}

          <!-- Skills Showcase -->
          {skills_showcase_html}

        </div>
      </div>
    '''


# ─────────────────────────────────────────────────────────────────────────────
# 6. KINETIC MOTION STUDIO TEMPLATE (Awwwards-Style Micro-Animations & 3D Tilt)
# ─────────────────────────────────────────────────────────────────────────────
