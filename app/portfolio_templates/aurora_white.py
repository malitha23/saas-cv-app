"""
Theme: Aurora White (Scandinavian Minimalist Light Studio)
Features:
- Crisp white/light background with refined soft gray card shadows
- High readability, elegant typography, and modern executive polish
- Perfect for corporate, product, and leadership portfolios
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
        loc_tag = f"· {exp.location}" if exp.location else ""
        exp_html.append(f'''
          <div class="relative pl-8 pb-8 border-l-2 border-slate-200 last:border-0">
            <div class="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full bg-white border-2 border-[var(--accent)] shadow-sm"></div>
            <div class="space-y-1">
              <div class="flex flex-wrap justify-between items-baseline gap-2">
                <h4 class="font-bold text-slate-900 text-base">{exp.job_title}</h4>
                <span class="text-xs font-mono text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-full">{exp.start_date} – {exp.end_date}</span>
              </div>
              <p class="text-xs font-semibold text-[var(--accent)]">{exp.company} {loc_tag}</p>
              <ul class="space-y-1 pt-2">{bullets}</ul>
            </div>
          </div>
        ''')

    nav_resume_btn = f'''
              <button onclick="window.parent.postMessage('download_resume', '*')"
                class="px-3.5 py-2 bg-white border border-slate-200 hover:border-slate-400 text-slate-700 rounded-xl text-xs font-semibold shadow-sm transition flex items-center gap-1.5">
                <i data-lucide="download" class="w-3.5 h-3.5 text-slate-600"></i>
                <span class="hidden sm:inline">Resume PDF</span>
              </button>
    ''' if resume.portfolio_show_resume_download else ''

    bio_html = f'<p class="text-sm sm:text-base text-slate-600 leading-relaxed max-w-2xl pt-1">{summary}</p>' if resume.portfolio_show_bio else ''

    hero_resume_btn = f'''
                <button onclick="window.parent.postMessage('download_resume', '*')"
                  class="px-5 py-3 bg-white border border-slate-200 hover:border-slate-300 text-slate-800 rounded-xl text-xs font-semibold shadow-sm transition">
                  Download CV Monograph
                </button>
    ''' if resume.portfolio_show_resume_download else ''

    joined_projects_html = "".join(projects_html)
    projects_section_html = f'''
          <section id="projects" class="space-y-6">
            <div class="flex justify-between items-baseline border-b border-slate-200 pb-4">
              <div class="space-y-1">
                <span class="text-xs font-mono uppercase tracking-wider text-[var(--accent)] font-bold">PORTFOLIO EXHIBITS</span>
                <h2 class="text-2xl font-black text-slate-900 tracking-tight">Featured Engineering Projects</h2>
              </div>
              <span class="text-xs font-mono text-slate-500">{len(resume.projects)} Systems</span>
            </div>
            <div class="space-y-6">{joined_projects_html}</div>
          </section>
    ''' if resume.portfolio_show_projects else ''

    joined_skills_html = "".join(skills_html)
    skills_section_html = f'''
          <section id="skills" class="space-y-6">
            <div class="border-b border-slate-200 pb-4 space-y-1">
              <span class="text-xs font-mono uppercase tracking-wider text-[var(--accent)] font-bold">TECHNICAL MATRIX</span>
              <h2 class="text-2xl font-black text-slate-900 tracking-tight">Core Competencies & Stack</h2>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">{joined_skills_html}</div>
          </section>
    ''' if resume.portfolio_show_skills else ''

    joined_exp_html = "".join(exp_html)
    exp_section_html = f'''
          <section id="experience" class="space-y-6">
            <div class="border-b border-slate-200 pb-4 space-y-1">
              <span class="text-xs font-mono uppercase tracking-wider text-[var(--accent)] font-bold">CAREER TRAJECTORY</span>
              <h2 class="text-2xl font-black text-slate-900 tracking-tight">Milestones & Achievements</h2>
            </div>
            <div class="bg-white border border-slate-200/80 rounded-3xl p-8 sm:p-10 shadow-sm space-y-2">
              {joined_exp_html}
            </div>
          </section>
    ''' if resume.portfolio_show_experience else ''

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
              {nav_resume_btn}
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
              {bio_html}
              
              <div class="flex flex-wrap items-center gap-3 pt-2 justify-center sm:justify-start">
                <a href="{cta_url}" class="px-6 py-3 bg-[var(--accent)] text-white font-bold rounded-xl text-xs hover:brightness-105 shadow-md shadow-[var(--accent-glow)] transition">
                  {cta_text} →
                </a>
                {hero_resume_btn}
                <div class="flex items-center gap-1.5 pl-2">{socials_html}</div>
              </div>
            </div>
          </section>

          <!-- METRICS HIGHLIGHTS -->
          <section class="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {metrics_html}
          </section>

          <!-- PROJECTS SHOWCASE -->
          {projects_section_html}

          <!-- SKILLS ARSENAL -->
          {skills_section_html}

          <!-- EXPERIENCE TIMELINE -->
          {exp_section_html}

        </main>

        <!-- Minimalist Footer -->
        <footer id="contact" class="border-t border-slate-200 bg-white py-12 mt-20 text-xs text-slate-500">
          <div class="max-w-6xl mx-auto px-4 sm:px-6 flex flex-wrap justify-between items-center gap-4">
            <div class="space-y-1">
              <p class="font-bold text-slate-900">© 2026 {full_name}. All rights reserved.</p>
              <p class="text-[11px] text-slate-400">Crafted with DreemFolio AI · Clean Light Edition</p>
            </div>
            <div class="flex items-center gap-2">{socials_html}</div>
          </div>
        </footer>

      </div>
    '''


