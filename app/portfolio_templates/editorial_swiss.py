"""
Theme: Editorial Swiss (Swiss Typographic Design)
Features:
- Bold editorial typography, oversized headers, and magazine grid
- High-contrast monochromatic styling with subtle accent rules
- Clean structured columns for projects and achievements
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
        loc_sub = f"// {exp.location}" if exp.location else ""
        experiences_html.append(f"""
          <div class="grid grid-cols-1 md:grid-cols-12 gap-6 py-6 border-b border-slate-800 stagger-item transition duration-300 hover:border-[var(--accent)]">
            <div class="md:col-span-4 space-y-1">
              <span class="text-xs font-mono text-[var(--accent)] uppercase font-semibold">{exp.start_date} — {exp.end_date}</span>
              <h4 class="font-bold text-base text-white">{exp.job_title}</h4>
              <p class="text-xs text-slate-400 italic">{exp.company} {loc_sub}</p>
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

    bio_html = f'<p class="text-base sm:text-xl text-slate-300 max-w-3xl font-light leading-relaxed pt-2 drop-cap">{summary}</p>' if resume.portfolio_show_bio else ''

    resume_btn_html = f'''
            <button onclick="window.parent.postMessage('download_resume', '*')"
              class="px-7 py-3.5 border border-slate-700 text-white font-semibold text-xs uppercase tracking-widest hover:border-white hover:bg-white/5 transition duration-300">
              Download CV Monograph (PDF)
            </button>
    ''' if resume.portfolio_show_resume_download else ''

    joined_projects_html = "".join(projects_html)
    projects_section_html = f'''
        <section class="space-y-6 animate-fade-in-up">
          <div class="flex justify-between items-baseline border-b border-white pb-3">
            <h3 class="text-sm font-mono tracking-widest uppercase text-slate-400">01 / SELECTED WORKS & SYSTEMS</h3>
            <span class="text-xs font-mono text-slate-500">{len(resume.projects)} EXHIBITS</span>
          </div>
          <div class="space-y-2">{joined_projects_html}</div>
        </section>
    ''' if resume.portfolio_show_projects else ''

    joined_exp_html = "".join(experiences_html)
    exp_section_html = f'''
        <section class="space-y-6 animate-fade-in-up">
          <div class="flex justify-between items-baseline border-b border-white pb-3">
            <h3 class="text-sm font-mono tracking-widest uppercase text-slate-400">02 / CAREER RECORD & ACHIEVEMENTS</h3>
            <span class="text-xs font-mono text-slate-500">{len(resume.work_experience)} MILESTONES</span>
          </div>
          <div class="space-y-2">{joined_exp_html}</div>
        </section>
    ''' if resume.portfolio_show_experience else ''

    skills_section_html = f'''
        <section class="space-y-6 animate-fade-in-up">
          <div class="flex justify-between items-baseline border-b border-white pb-3">
            <h3 class="text-sm font-mono tracking-widest uppercase text-slate-400">03 / CORE COMPETENCIES</h3>
            <span class="text-xs font-mono text-slate-500">SYSTEM ARCHITECTURE</span>
          </div>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-8 pt-2">
            {skills_html}
          </div>
        </section>
    ''' if resume.portfolio_show_skills else ''

    return f"""
      <div class="max-w-6xl mx-auto px-6 py-16 space-y-16">

        <!-- Masthead -->
        <header class="border-b-2 border-white pb-12 space-y-8 animate-fade-in-up">
          <div class="flex justify-between items-center text-xs uppercase tracking-widest font-mono text-slate-400 border-b border-slate-800 pb-3">
            <span>VOL. 2026 // EDITION NO. 09</span>
            <span>PRINT & DIGITAL MONOGRAPH</span>
            <span>{info.location or "GENEVA // GLOBAL"}</span>
          </div>

          <div class="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 pt-4">
            <div class="space-y-3">
              <span class="text-xs font-mono text-[var(--accent)] tracking-widest uppercase">Curriculum Vitae</span>
              <h1 class="text-4xl sm:text-7xl font-black uppercase tracking-tight text-white">{full_name}</h1>
              <p class="text-xl sm:text-2xl text-slate-400 font-light tracking-wide italic">{role_title}</p>
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

          {bio_html}

          <div class="flex flex-wrap items-center gap-4 pt-2">
            <a href="{cta_url}" class="px-7 py-3.5 bg-white text-black font-bold text-xs uppercase tracking-widest hover:bg-[var(--accent)] hover:text-white transition duration-300 shadow-lg hover:shadow-xl hover:shadow-[var(--accent-glow)]">
              {cta_text} →
            </a>
            {resume_btn_html}
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
        {projects_section_html}

        <!-- Experience -->
        {exp_section_html}

        <!-- Skills -->
        {skills_section_html}

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
