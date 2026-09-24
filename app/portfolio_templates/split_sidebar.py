"""
Theme: Split Sidebar (Executive Split-Pane)
Features:
- Sticky left drawer profile panel with avatar, contact & socials
- Scrolling right content feed for experience, projects, education
- Minimalist executive aesthetic
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
        loc_suffix = f"· {exp.location}" if exp.location else ""
        exp_items.append(f"""
          <div class="border-b border-slate-800/80 pb-6 last:border-0 last:pb-0 space-y-2">
            <div class="flex flex-wrap justify-between items-baseline gap-1">
              <div>
                <h4 class="font-bold text-sm text-white">{exp.job_title}</h4>
                <p class="text-xs font-semibold text-[var(--accent)]">{exp.company} {loc_suffix}</p>
              </div>
              <span class="text-xs font-mono text-slate-400">{exp.start_date} — {exp.end_date}</span>
            </div>
            <ul class="space-y-1.5 pt-1">{bullets}</ul>
          </div>
        """)

    bio_html = f'<p class="text-sm text-slate-300 leading-relaxed">{summary}</p>' if resume.portfolio_show_bio else ''
    
    resume_btn_html = f'''
                <button onclick="window.parent.postMessage('download_resume', '*')"
                  class="px-4 py-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 rounded-xl font-semibold text-xs flex items-center gap-2 transition">
                  <i data-lucide="download" class="w-3.5 h-3.5 text-[var(--accent)]"></i>
                  <span>Resume PDF</span>
                </button>
    ''' if resume.portfolio_show_resume_download else ''

    joined_exp_items = "".join(exp_items)
    exp_section_html = f'''
            <section id="experience" class="space-y-6">
              <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
                <i data-lucide="briefcase" class="w-5 h-5 text-[var(--accent)]"></i>
                <h2 class="text-lg font-bold text-white">Career Milestones & Achievements</h2>
              </div>
              <div class="space-y-6">{joined_exp_items}</div>
            </section>
    ''' if resume.portfolio_show_experience else ''

    joined_project_items = "".join(project_items)
    proj_section_html = f'''
            <section id="projects" class="space-y-6">
              <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
                <i data-lucide="layers" class="w-5 h-5 text-[var(--accent)]"></i>
                <h2 class="text-lg font-bold text-white">Key Systems & Architectures</h2>
              </div>
              <div class="space-y-4">{joined_project_items}</div>
            </section>
    ''' if resume.portfolio_show_projects else ''

    skill_cards_list = []
    for c in resume.skill_categories:
        rendered_skills = "".join([f'<span class="px-2 py-0.5 text-xs bg-slate-950 border border-slate-800 text-slate-300 rounded">{s}</span>' for s in c.skills])
        skill_cards_list.append(f'<div class="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2"><h4 class="text-xs font-bold text-[var(--accent)] uppercase">{c.category_name}</h4><div class="flex flex-wrap gap-1.5">{rendered_skills}</div></div>')
    joined_skill_cards = "".join(skill_cards_list)

    skills_section_html = f'''
            <section id="skills" class="space-y-6">
              <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
                <i data-lucide="cpu" class="w-5 h-5 text-[var(--accent)]"></i>
                <h2 class="text-lg font-bold text-white">Core Competencies & Stack</h2>
              </div>
              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {joined_skill_cards}
              </div>
            </section>
    ''' if resume.portfolio_show_skills else ''

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
            {bio_html}
            
            <div class="space-y-3 pt-2">
              <div class="flex items-center gap-3">
                <a href="{cta_url}" class="px-5 py-2.5 bg-[var(--accent)] text-slate-950 font-bold rounded-xl text-xs shadow-lg shadow-[var(--accent-glow)] flex items-center gap-2 hover:brightness-110 transition">
                  <i data-lucide="send" class="w-3.5 h-3.5"></i>
                  <span>{cta_text}</span>
                </a>
                {resume_btn_html}
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
            {exp_section_html}

            <!-- Projects -->
            {proj_section_html}

            <!-- Skills -->
            {skills_section_html}

          </div>

        </div>
      </div>
    '''


# ─────────────────────────────────────────────────────────────────────────────
# 3. CYBER TERMINAL CLI TEMPLATE (Hacker / Terminal Developer Aesthetic)
# ─────────────────────────────────────────────────────────────────────────────
