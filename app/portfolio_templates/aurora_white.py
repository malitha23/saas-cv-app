"""
Theme: Aurora White — Premium Scandinavian Minimalist Light Studio
Design: Executive-grade, glass-morphism, layered soft shadows,
        refined typography, cinematic micro-interactions + scroll animations.
"""

import os
import io
import re
import html
import json
from typing import List, Optional, Dict, Any
from app.schemas import TailoredResume
from app.portfolio_templates.common import (
    sanitize_text,
    sanitize_url,
    get_social_svg,
    get_social_icon,
    hex_to_rgba,
)


def render_aurora_white(resume: TailoredResume, accent: str) -> str:
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

    # --- Avatar with float animation ---
    if avatar_url:
        avatar_elem = f"""
          <div class="relative shrink-0 animate-float">
            <div class="absolute -inset-1.5 bg-gradient-to-tr from-[var(--accent)]/25 via-[var(--accent)]/5 to-transparent rounded-[2rem] blur-md animate-pulse-slow"></div>
            <img src="{avatar_url}" alt="{full_name}"
                 class="relative w-28 h-28 sm:w-36 sm:h-36 rounded-[2rem] object-cover ring-1 ring-white/70 shadow-[0_12px_36px_-12px_rgba(15,23,42,0.28)]">
          </div>
        """
    else:
        initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "AW"
        avatar_elem = f"""
          <div class="relative shrink-0 animate-float">
            <div class="absolute -inset-1.5 bg-gradient-to-tr from-[var(--accent)]/25 via-[var(--accent)]/5 to-transparent rounded-[2rem] blur-md animate-pulse-slow"></div>
            <div class="relative w-28 h-28 sm:w-36 sm:h-36 rounded-[2rem] bg-gradient-to-br from-white to-slate-50 p-[1.5px] shadow-[0_12px_36px_-12px_rgba(15,23,42,0.28)]">
              <div class="w-full h-full bg-gradient-to-br from-slate-50 to-white rounded-[2rem] flex items-center justify-center ring-1 ring-slate-100">
                <span class="text-slate-900 text-4xl font-black tracking-tight" style="font-family:'Playfair Display',serif">{initials}</span>
              </div>
            </div>
          </div>
        """

    # --- Social icons ---
    socials = []
    for link in info.social_links:
        if link.enabled and link.url.strip():
            href = (
                link.url
                if link.url.startswith("http") or link.url.startswith("mailto:")
                else f"https://{link.url}"
            )
            svg = get_social_svg(
                link.name,
                link.icon,
                "w-4 h-4 text-slate-500 group-hover:text-slate-900 transition-colors duration-300",
            )
            socials.append(f"""
              <a href="{href}" target="_blank" title="{link.name}"
                 class="group relative p-2.5 rounded-xl bg-white/80 backdrop-blur border border-slate-200/70 shadow-[0_1px_3px_-1px_rgba(15,23,42,0.08)] hover:border-[var(--accent)]/40 hover:shadow-[0_6px_16px_-6px_var(--accent-glow)] hover:-translate-y-1 hover:scale-105 transition-all duration-300 flex items-center justify-center">
                {svg}
              </a>
            """)
    if info.email and not any(
        "mail" in l.name.lower() for l in info.social_links if l.enabled
    ):
        email_svg = get_social_svg(
            "mail",
            "mail",
            "w-4 h-4 text-slate-500 group-hover:text-slate-900 transition-colors duration-300",
        )
        socials.append(f"""
          <a href="mailto:{info.email}" title="Email"
             class="group relative p-2.5 rounded-xl bg-white/80 backdrop-blur border border-slate-200/70 shadow-[0_1px_3px_-1px_rgba(15,23,42,0.08)] hover:border-[var(--accent)]/40 hover:shadow-[0_6px_16px_-6px_var(--accent-glow)] hover:-translate-y-1 hover:scale-105 transition-all duration-300 flex items-center justify-center">
            {email_svg}
          </a>
        """)
    socials_html = "".join(socials)

    # --- Metrics ---
    if resume.portfolio_metrics:
        metrics = resume.portfolio_metrics
    else:
        metrics = [
            {"label": "Key Projects", "value": f"{len(resume.projects)}+"},
            {"label": "Experience", "value": f"{len(resume.work_experience)}+ Yrs"},
            {"label": "System Reliability", "value": "99.98%"},
            {
                "label": "Core Competencies",
                "value": f"{sum(len(c.skills) for c in resume.skill_categories)}+",
            },
        ]

    metrics_html = "".join([f"""
      <div class="reveal group relative p-6 bg-white border border-slate-200/60 rounded-2xl shadow-[0_2px_10px_-4px_rgba(15,23,42,0.08)] hover:shadow-[0_18px_44px_-14px_rgba(15,23,42,0.22)] hover:-translate-y-1.5 hover:border-[var(--accent)]/30 transition-all duration-500 text-center space-y-1.5 overflow-hidden" style="transition-delay: {i*80}ms">
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[var(--accent)]/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
        <div class="absolute -top-12 left-1/2 -translate-x-1/2 w-32 h-32 rounded-full bg-[var(--accent)]/[0.06] blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
        <div class="relative text-3xl sm:text-4xl font-black text-slate-900 font-mono tracking-tight leading-none group-hover:text-[var(--accent)] transition-colors duration-500">{m.get("value", "0")}</div>
        <p class="relative text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">{m.get("label", "Metric")}</p>
      </div>
    """ for i, m in enumerate(metrics[:4])])

    # --- Projects ---
    projects_html = []
    for idx, p in enumerate(resume.projects):
        tech_tags = "".join(
            [
                f'<span class="px-2.5 py-1 text-[11px] font-mono bg-slate-50 border border-slate-200/70 text-slate-600 rounded-lg hover:border-[var(--accent)]/40 hover:bg-white hover:text-slate-800 hover:-translate-y-0.5 transition-all duration-200">{t}</span>'
                for t in p.technologies
            ]
        )
        bullets = "".join(
            [
                f'<li class="text-[13px] text-slate-600 leading-relaxed flex items-start gap-2.5"><span class="text-[var(--accent)] font-bold mt-0.5 select-none">▪</span><span>{b.lstrip("•- ")}</span></li>'
                for b in p.description_bullets
            ]
        )
        actions = []
        if p.demo_url:
            actions.append(
                f'<a href="{p.demo_url}" target="_blank" class="group/btn btn-primary relative overflow-hidden px-4 py-2 text-white rounded-xl text-[11px] font-bold transition-all duration-300 flex items-center gap-1.5 hover:-translate-y-0.5"><span class="relative z-10 flex items-center gap-1.5">Live Demo <span class="group-hover/btn:translate-x-0.5 transition-transform duration-300">→</span></span></a>'
            )
        if p.link:
            actions.append(
                f'<a href="{p.link}" target="_blank" class="px-4 py-2 bg-white border border-slate-200 text-slate-700 rounded-xl text-[11px] font-semibold hover:border-[var(--accent)]/40 hover:bg-slate-50 hover:text-slate-900 hover:-translate-y-0.5 transition-all duration-300 flex items-center gap-1.5 shadow-[0_1px_3px_-1px_rgba(15,23,42,0.06)]"><span>Source Code</span></a>'
            )

        projects_html.append(f"""
          <div class="reveal group relative bg-white border border-slate-200/60 rounded-3xl p-6 sm:p-8 shadow-[0_2px_12px_-6px_rgba(15,23,42,0.08)] hover:shadow-[0_28px_64px_-22px_rgba(15,23,42,0.22)] hover:border-[var(--accent)]/30 hover:-translate-y-1.5 transition-all duration-500 space-y-5 overflow-hidden" style="transition-delay: {idx*60}ms">
            <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[var(--accent)]/50 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <div class="absolute -top-24 -right-24 w-48 h-48 rounded-full bg-[var(--accent)]/[0.07] blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>

            <div class="relative flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-5">
              <div class="space-y-1.5">
                <span class="text-[10px] font-mono text-[var(--accent)] font-bold tracking-[0.15em] uppercase">Project {idx+1:02d}</span>
                <h4 class="text-xl font-bold text-slate-900 group-hover:text-[var(--accent)] transition-colors duration-300 tracking-tight">{p.name}</h4>
              </div>
              <div class="flex flex-wrap gap-2">{"".join(actions)}</div>
            </div>
            <ul class="relative space-y-2 max-w-3xl">{bullets}</ul>
            <div class="relative flex flex-wrap gap-1.5 pt-1">{tech_tags}</div>
          </div>
        """)

    # --- Skills ---
    skills_html = []
    for cat in resume.skill_categories:
        skill_bars = []
        for s in cat.skills:
            level = cat.skill_levels.get(s, 85) if cat.skill_levels else 85
            skill_bars.append(f"""
              <div class="space-y-2">
                <div class="flex justify-between items-baseline text-xs">
                  <span class="font-semibold text-slate-800 tracking-tight">{s}</span>
                  <span class="font-mono text-slate-400 font-bold text-[11px]">{level}%</span>
                </div>
                <div class="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden">
                  <div class="skill-bar h-full rounded-full bg-gradient-to-r from-[var(--accent)] to-[var(--accent)]/70 shadow-[0_0_8px_var(--accent-glow)]" data-level="{level}" style="width: 0%"></div>
                </div>
              </div>
            """)
        skills_html.append(f"""
          <div class="reveal group bg-white border border-slate-200/60 rounded-3xl p-6 shadow-[0_2px_12px_-6px_rgba(15,23,42,0.06)] hover:shadow-[0_20px_48px_-16px_rgba(15,23,42,0.16)] hover:-translate-y-1 transition-all duration-500 space-y-5">
            <h5 class="text-[11px] font-bold uppercase tracking-[0.14em] text-slate-900 border-b border-slate-100 pb-3 flex items-center gap-2.5">
              <span class="w-1.5 h-1.5 rounded-full bg-[var(--accent)] shadow-[0_0_8px_var(--accent-glow)] group-hover:scale-125 transition-transform duration-300"></span>
              {cat.category_name}
            </h5>
            <div class="space-y-4">{"".join(skill_bars)}</div>
          </div>
        """)

    # --- Experience ---
    exp_html = []
    for exp in resume.work_experience:
        bullets = "".join(
            [
                f'<li class="text-[13px] text-slate-600 leading-relaxed flex items-start gap-2.5"><span class="text-slate-300 mt-1.5 select-none">—</span><span>{b.lstrip("•- ")}</span></li>'
                for b in exp.bullet_points[:3]
            ]
        )
        loc_tag = (
            f'<span class="text-slate-400">·</span> {exp.location}'
            if exp.location
            else ""
        )
        exp_html.append(f"""
          <div class="reveal relative pl-9 pb-9 border-l border-slate-200/80 last:border-0 last:pb-0 group">
            <div class="absolute -left-[7px] top-1.5 w-3.5 h-3.5 rounded-full bg-white border-2 border-[var(--accent)] shadow-[0_0_0_4px_rgba(255,255,255,1),0_0_12px_var(--accent-glow)] group-hover:scale-125 transition-transform duration-300"></div>
            <div class="space-y-1.5">
              <div class="flex flex-wrap justify-between items-baseline gap-2">
                <h4 class="font-bold text-slate-900 text-base tracking-tight group-hover:text-[var(--accent)] transition-colors duration-300">{exp.job_title}</h4>
                <span class="text-[11px] font-mono text-slate-500 bg-slate-50 border border-slate-200/70 px-2.5 py-1 rounded-full">{exp.start_date} – {exp.end_date}</span>
              </div>
              <p class="text-xs font-semibold text-[var(--accent)] tracking-tight">{exp.company} <span class="text-slate-400 font-normal">{loc_tag}</span></p>
              <ul class="space-y-2 pt-3">{bullets}</ul>
            </div>
          </div>
        """)

    nav_resume_btn = (
        f"""
              <button onclick="window.parent.postMessage('download_resume', '*')"
                class="px-3.5 py-2 bg-white border border-slate-200 hover:border-[var(--accent)]/40 hover:bg-slate-50 text-slate-700 hover:text-slate-900 rounded-xl text-xs font-semibold shadow-[0_1px_3px_-1px_rgba(15,23,42,0.08)] hover:shadow-[0_6px_16px_-6px_rgba(15,23,42,0.15)] hover:-translate-y-0.5 transition-all duration-300 flex items-center gap-1.5">
                <i data-lucide="download" class="w-3.5 h-3.5 text-slate-500"></i>
                <span class="hidden sm:inline">Resume PDF</span>
              </button>
    """
        if resume.portfolio_show_resume_download
        else ""
    )

    bio_html = (
        f'<p class="text-sm sm:text-[15px] text-slate-500 leading-relaxed max-w-2xl pt-1 font-light">{summary}</p>'
        if resume.portfolio_show_bio
        else ""
    )

    hero_resume_btn = (
        f"""
                <button onclick="window.parent.postMessage('download_resume', '*')"
                  class="px-5 py-3 bg-white border border-slate-200 hover:border-[var(--accent)]/40 hover:bg-slate-50 text-slate-800 hover:text-slate-900 rounded-xl text-xs font-semibold shadow-[0_1px_3px_-1px_rgba(15,23,42,0.08)] hover:shadow-[0_10px_24px_-8px_rgba(15,23,42,0.18)] hover:-translate-y-0.5 transition-all duration-300">
                  Download CV Monograph
                </button>
    """
        if resume.portfolio_show_resume_download
        else ""
    )

    joined_projects_html = "".join(projects_html)
    projects_section_html = (
        f"""
          <section id="projects" class="space-y-8">
            <div class="reveal flex justify-between items-baseline border-b border-slate-200/70 pb-5">
              <div class="space-y-2">
                <span class="text-[10px] font-mono uppercase tracking-[0.2em] text-[var(--accent)] font-bold">Portfolio Exhibits</span>
                <h2 class="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight" style="font-family:'Playfair Display',serif">Featured Engineering Projects</h2>
              </div>
              <span class="text-[11px] font-mono text-slate-400 hidden sm:block">{len(resume.projects)} Systems</span>
            </div>
            <div class="space-y-6">{joined_projects_html}</div>
          </section>
    """
        if resume.portfolio_show_projects
        else ""
    )

    joined_skills_html = "".join(skills_html)
    skills_section_html = (
        f"""
          <section id="skills" class="space-y-8">
            <div class="reveal border-b border-slate-200/70 pb-5 space-y-2">
              <span class="text-[10px] font-mono uppercase tracking-[0.2em] text-[var(--accent)] font-bold">Technical Matrix</span>
              <h2 class="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight" style="font-family:'Playfair Display',serif">Core Competencies & Stack</h2>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">{joined_skills_html}</div>
          </section>
    """
        if resume.portfolio_show_skills
        else ""
    )

    joined_exp_html = "".join(exp_html)
    exp_section_html = (
        f"""
          <section id="experience" class="space-y-8">
            <div class="reveal border-b border-slate-200/70 pb-5 space-y-2">
              <span class="text-[10px] font-mono uppercase tracking-[0.2em] text-[var(--accent)] font-bold">Career Trajectory</span>
              <h2 class="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight" style="font-family:'Playfair Display',serif">Milestones & Achievements</h2>
            </div>
            <div class="reveal bg-white border border-slate-200/60 rounded-3xl p-8 sm:p-10 shadow-[0_2px_12px_-6px_rgba(15,23,42,0.06)] space-y-2">
              {joined_exp_html}
            </div>
          </section>
    """
        if resume.portfolio_show_experience
        else ""
    )

    return f"""
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Playfair+Display:wght@700;800;900&display=swap');

        html {{ scroll-behavior: smooth; }}
        body {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; }}

        /* --- Keyframe animations --- */
        @keyframes floatY {{
          0%, 100% {{ transform: translateY(0); }}
          50% {{ transform: translateY(-6px); }}
        }}
        @keyframes pulseSlow {{
          0%, 100% {{ opacity: 0.6; transform: scale(1); }}
          50% {{ opacity: 1; transform: scale(1.03); }}
        }}
        @keyframes shimmer {{
          0% {{ transform: translateX(-100%); }}
          100% {{ transform: translateX(100%); }}
        }}
        @keyframes fadeUp {{
          0% {{ opacity: 0; transform: translateY(24px); }}
          100% {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes gradientShift {{
          0%, 100% {{ background-position: 0% 50%; }}
          50% {{ background-position: 100% 50%; }}
        }}
        @keyframes pulseRing {{
          0% {{ box-shadow: 0 0 0 0 rgba(16,185,129,0.5); }}
          70% {{ box-shadow: 0 0 0 8px rgba(16,185,129,0); }}
          100% {{ box-shadow: 0 0 0 0 rgba(16,185,129,0); }}
        }}

        .animate-float {{ animation: floatY 5s ease-in-out infinite; }}
        .animate-pulse-slow {{ animation: pulseSlow 4s ease-in-out infinite; }}
        .animate-pulse-ring {{ animation: pulseRing 2.2s ease-out infinite; }}

        /* --- Scroll reveal --- */
        .reveal {{
          opacity: 0;
          transform: translateY(28px);
          transition: opacity 0.8s cubic-bezier(0.16,1,0.3,1),
                      transform 0.8s cubic-bezier(0.16,1,0.3,1);
          will-change: opacity, transform;
        }}
        .reveal.is-visible {{
          opacity: 1;
          transform: translateY(0);
        }}

        /* --- Primary button (crisp, clear, no shadow bleed) --- */
        .btn-primary {{
          background: linear-gradient(180deg, var(--accent) 0%, color-mix(in srgb, var(--accent) 88%, black) 100%);
          box-shadow: 0 1px 0 0 rgba(255,255,255,0.25) inset,
                      0 4px 14px -4px var(--accent-glow),
                      0 1px 2px 0 rgba(15,23,42,0.15);
        }}
        .btn-primary:hover {{
          filter: brightness(1.08);
          box-shadow: 0 1px 0 0 rgba(255,255,255,0.3) inset,
                      0 10px 28px -8px var(--accent-glow),
                      0 2px 6px 0 rgba(15,23,42,0.2);
        }}
        .btn-primary::after {{
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(110deg, transparent 25%, rgba(255,255,255,0.35) 50%, transparent 75%);
          transform: translateX(-100%);
          transition: transform 0.7s ease;
          pointer-events: none;
        }}
        .btn-primary:hover::after {{
          transform: translateX(100%);
        }}

        /* --- Shimmering gradient section headings --- */
        .gradient-text {{
          background: linear-gradient(90deg, #0f172a 0%, var(--accent) 50%, #0f172a 100%);
          background-size: 200% 100%;
          -webkit-background-clip: text;
          background-clip: text;
          -webkit-text-fill-color: transparent;
          animation: gradientShift 6s ease-in-out infinite;
        }}

        /* --- Skill bar fill animation --- */
        .skill-bar {{
          transition: width 1.4s cubic-bezier(0.16,1,0.3,1);
        }}

        /* --- Badge ping ring --- */
        .badge-dot {{
          animation: pulseRing 2.2s ease-out infinite;
        }}

        /* --- Card hover smoothness --- */
        .reveal {{ backface-visibility: hidden; }}
      </style>

      <div class="min-h-screen bg-[#FBFBFD] text-slate-900 antialiased">

        <!-- Ambient gradient mesh background -->
        <div class="fixed inset-0 pointer-events-none -z-10 overflow-hidden">
          <div class="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-gradient-to-br from-[var(--accent)]/[0.04] to-transparent blur-3xl"></div>
          <div class="absolute top-1/3 -right-40 w-[500px] h-[500px] rounded-full bg-gradient-to-bl from-slate-300/20 to-transparent blur-3xl"></div>
          <div class="absolute bottom-0 left-1/3 w-[500px] h-[500px] rounded-full bg-gradient-to-tr from-[var(--accent)]/[0.03] to-transparent blur-3xl"></div>
          <div class="absolute inset-x-0 top-0 h-96 bg-gradient-to-b from-white via-white/50 to-transparent"></div>
        </div>

        <!-- Sticky glass header -->
        <header class="sticky top-0 z-30 bg-white/80 backdrop-blur-xl border-b border-slate-200/60 shadow-[0_1px_0_0_rgba(255,255,255,0.8)_inset,0_2px_12px_-6px_rgba(15,23,42,0.08)]">
          <div class="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span class="w-9 h-9 rounded-xl bg-gradient-to-br from-slate-900 to-slate-700 text-white flex items-center justify-center font-bold text-[11px] font-mono shadow-[0_4px_12px_-4px_rgba(15,23,42,0.4)] hover:scale-105 transition-transform duration-300">
                {full_name[:2].upper()}
              </span>
              <span class="font-bold text-slate-900 text-sm tracking-tight">{full_name}</span>
            </div>

            <nav class="hidden md:flex items-center gap-7 text-xs font-semibold text-slate-500">
              <a href="#projects" class="relative hover:text-slate-900 transition-colors duration-300 group">
                Projects<span class="absolute -bottom-1 left-0 w-0 h-px bg-[var(--accent)] group-hover:w-full transition-all duration-300"></span>
              </a>
              <a href="#experience" class="relative hover:text-slate-900 transition-colors duration-300 group">
                Experience<span class="absolute -bottom-1 left-0 w-0 h-px bg-[var(--accent)] group-hover:w-full transition-all duration-300"></span>
              </a>
              <a href="#skills" class="relative hover:text-slate-900 transition-colors duration-300 group">
                Skills<span class="absolute -bottom-1 left-0 w-0 h-px bg-[var(--accent)] group-hover:w-full transition-all duration-300"></span>
              </a>
              <a href="#contact" class="relative hover:text-slate-900 transition-colors duration-300 group">
                Contact<span class="absolute -bottom-1 left-0 w-0 h-px bg-[var(--accent)] group-hover:w-full transition-all duration-300"></span>
              </a>
            </nav>

            <div class="flex items-center gap-2.5">
              {nav_resume_btn}
              <a href="{cta_url}"
                class="btn-primary relative overflow-hidden px-4 py-2 text-white rounded-xl text-xs font-bold transition-all duration-300 hover:-translate-y-0.5">
                <span class="relative z-10">{cta_text}</span>
              </a>
            </div>
          </div>
        </header>

        <!-- Main content -->
        <main class="relative max-w-6xl mx-auto px-4 sm:px-6 pt-12 sm:pt-16 pb-6 sm:pb-10 space-y-16 sm:space-y-20">

          <!-- HERO -->
          <section class="reveal relative bg-white/85 backdrop-blur-sm border border-slate-200/60 rounded-[2rem] p-8 sm:p-12 shadow-[0_8px_40px_-12px_rgba(15,23,42,0.1)] overflow-hidden flex flex-col sm:flex-row items-center sm:items-start gap-8 sm:gap-10">
            <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[var(--accent)]/40 to-transparent"></div>
            <div class="absolute -top-32 -right-32 w-64 h-64 rounded-full bg-[var(--accent)]/[0.06] blur-3xl"></div>
            {avatar_elem}
            <div class="relative space-y-5 text-center sm:text-left flex-1">
              <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50/90 backdrop-blur border border-emerald-200/70 text-emerald-700 text-[11px] font-semibold shadow-[0_2px_8px_-2px_rgba(16,185,129,0.15)]">
                <span class="badge-dot relative flex w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>{badge_text}</span>
              </div>
              <div class="space-y-2">
                <h1 class="text-4xl sm:text-6xl font-black tracking-tight text-slate-900 leading-[1.05]" style="font-family:'Playfair Display',serif">{full_name}</h1>
                <p class="text-lg sm:text-2xl font-bold text-[var(--accent)] tracking-tight">{role_title}</p>
                <p class="text-xs text-slate-400 font-medium tracking-wide">{info.location or "Global / Remote"}</p>
              </div>
              {bio_html}

              <div class="flex flex-wrap items-center gap-3 pt-3 justify-center sm:justify-start">
                <a href="{cta_url}" class="btn-primary group relative overflow-hidden px-6 py-3 text-white font-bold rounded-xl text-xs transition-all duration-300 hover:-translate-y-1 inline-flex items-center gap-2">
                  <span class="relative z-10 flex items-center gap-2">
                    {cta_text} <span class="group-hover:translate-x-1 transition-transform duration-300">→</span>
                  </span>
                </a>
                {hero_resume_btn}
                <div class="flex items-center gap-1.5 sm:pl-3">{socials_html}</div>
              </div>
            </div>
          </section>

          <!-- METRICS -->
          <section class="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {metrics_html}
          </section>

          <!-- PROJECTS -->
          {projects_section_html}

          <!-- SKILLS -->
          {skills_section_html}

          <!-- EXPERIENCE -->
          {exp_section_html}

        </main>

               <!-- Footer — tight, refined, no excessive gaps -->
        <footer id="contact" class="relative mt-0 border-t border-slate-200/60 bg-gradient-to-b from-white/80 to-slate-50/60 backdrop-blur-sm">
          <!-- Top accent line -->
          <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[var(--accent)]/25 to-transparent"></div>

          <div class="max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
            <div class="flex flex-wrap justify-between items-center gap-5">
              <div class="space-y-1">
                <p class="font-bold text-slate-900 text-sm tracking-tight">© 2026 {full_name}. All rights reserved.</p>
                <p class="text-[11px] text-slate-400 font-light tracking-wide">Crafted with DreemFolio AI · Aurora White Edition</p>
              </div>
              <div class="flex items-center gap-2">{socials_html}</div>
            </div>
          </div>

          <!-- Reserved space for DreemFolio floating badge (prevent overlap) -->
          <div class="h-16 sm:h-20" aria-hidden="true"></div>
        </footer>

      </div>

      <script>
        // Scroll reveal
        (function() {{
          const els = document.querySelectorAll('.reveal');
          if (!('IntersectionObserver' in window)) {{
            els.forEach(el => el.classList.add('is-visible'));
            return;
          }}
          const io = new IntersectionObserver((entries) => {{
            entries.forEach(e => {{
              if (e.isIntersecting) {{
                e.target.classList.add('is-visible');
                io.unobserve(e.target);
              }}
            }});
          }}, {{ threshold: 0.12, rootMargin: '0px 0px -40px 0px' }});
          els.forEach(el => io.observe(el));
        }})();

        // Skill bar fill on scroll
        (function() {{
          const bars = document.querySelectorAll('.skill-bar');
          if (!('IntersectionObserver' in window)) {{
            bars.forEach(b => b.style.width = b.dataset.level + '%');
            return;
          }}
          const io = new IntersectionObserver((entries) => {{
            entries.forEach(e => {{
              if (e.isIntersecting) {{
                const lvl = e.target.dataset.level || '0';
                setTimeout(() => {{ e.target.style.width = lvl + '%'; }}, 150);
                io.unobserve(e.target);
              }}
            }});
          }}, {{ threshold: 0.4 }});
          bars.forEach(b => io.observe(b));
        }})();
      </script>
    """
