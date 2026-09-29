"""
Theme: Bento Grid — Premium Apple/Linear Style
Design: Modular bento layout, glass-morphism, ambient gradient mesh,
        cinematic scroll animations, count-up metrics, magnetic hovers.
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

    # --- Avatar with animated gradient ring ---
    if avatar_url:
        avatar_elem = f"""
          <div class="relative shrink-0 animate-float">
            <div class="absolute -inset-1.5 rounded-2xl bg-gradient-to-tr from-[var(--accent)] via-violet-500 to-[var(--accent)] opacity-60 blur-md animate-gradient-spin"></div>
            <img src="{avatar_url}" alt="{full_name}"
                 class="relative w-24 h-24 sm:w-28 sm:h-28 rounded-2xl object-cover ring-2 ring-[var(--accent)]/60 shadow-[0_8px_32px_-8px_var(--accent-glow)]">
          </div>
        """
    else:
        initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "CV"
        avatar_elem = f"""
          <div class="relative shrink-0 animate-float">
            <div class="absolute -inset-1.5 rounded-2xl bg-gradient-to-tr from-[var(--accent)] via-violet-500 to-[var(--accent)] opacity-60 blur-md animate-gradient-spin"></div>
            <div class="relative w-24 h-24 sm:w-28 sm:h-28 rounded-2xl bg-gradient-to-tr from-[var(--accent)] to-violet-600 p-0.5 shadow-[0_8px_32px_-8px_var(--accent-glow)] flex items-center justify-center text-white font-extrabold text-2xl">
              <div class="w-full h-full bg-slate-950 rounded-2xl flex items-center justify-center">
                <span class="bg-gradient-to-br from-white to-slate-400 bg-clip-text text-transparent">{initials}</span>
              </div>
            </div>
          </div>
        """

    # --- Social pills with lift + glow ---
    social_links = []
    for link in info.social_links:
        if link.enabled and link.url.strip():
            href = (
                link.url
                if link.url.startswith("http") or link.url.startswith("mailto:")
                else f"https://{link.url}"
            )
            svg_icon = get_social_svg(
                link.name,
                link.icon,
                "w-4 h-4 text-[var(--accent)] group-hover:scale-110 transition-transform duration-300",
            )
            social_links.append(f"""
              <a href="{href}" target="_blank" rel="noopener noreferrer" title="{link.name}"
                class="group relative p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-[var(--accent)] hover:shadow-[0_8px_24px_-6px_var(--accent-glow)] hover:-translate-y-1 transition-all duration-300 flex items-center gap-2 text-xs font-medium overflow-hidden">
                <div class="absolute inset-0 bg-gradient-to-r from-[var(--accent)]/0 via-[var(--accent)]/10 to-[var(--accent)]/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
                {svg_icon}
                <span class="relative">{link.name}</span>
              </a>
            """)
    if not social_links and info.email:
        email_svg = get_social_svg(
            "mail",
            "mail",
            "w-4 h-4 text-[var(--accent)] group-hover:scale-110 transition-transform duration-300",
        )
        social_links.append(f"""
          <a href="mailto:{info.email}" class="group relative p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-[var(--accent)] hover:shadow-[0_8px_24px_-6px_var(--accent-glow)] hover:-translate-y-1 transition-all duration-300 flex items-center gap-2 text-xs font-medium overflow-hidden">
            <div class="absolute inset-0 bg-gradient-to-r from-[var(--accent)]/0 via-[var(--accent)]/10 to-[var(--accent)]/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
            {email_svg}
            <span class="relative">{info.email}</span>
          </a>
        """)

    socials_html = "".join(social_links)

    # --- Resume download button ---
    dl_button = ""
    if resume.portfolio_show_resume_download:
        dl_button = f"""
          <button onclick="window.parent.postMessage('download_resume', '*')"
            class="group relative px-4 py-2.5 bg-slate-800/80 backdrop-blur border border-slate-700 text-slate-200 rounded-xl font-semibold text-xs flex items-center gap-2 transition-all duration-300 hover:border-[var(--accent)]/60 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_-8px_rgba(0,0,0,0.5)] overflow-hidden">
            <i data-lucide="file-down" class="w-4 h-4 text-[var(--accent)] group-hover:translate-y-0.5 transition-transform duration-300"></i>
            <span>Download ATS Resume</span>
          </button>
        """

    # --- Project cards with hover lift + corner glow ---
    project_cards = []
    for idx, p in enumerate(resume.projects):
        tech = "".join(
            [
                f'<span class="px-2 py-0.5 text-[10px] font-mono bg-slate-900/80 border border-slate-800 text-slate-300 rounded-md hover:border-[var(--accent)]/60 hover:text-[var(--accent)] hover:-translate-y-0.5 transition-all duration-300 cursor-default">{t}</span>'
                for t in p.technologies
            ]
        )
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-400 flex items-start gap-2"><span class="text-[var(--accent)] mt-0.5 select-none">▸</span><span>{b.lstrip("•- ")}</span></li>'
                for b in p.description_bullets[:2]
            ]
        )
        actions = []
        if p.demo_url:
            actions.append(
                f'<a href="{p.demo_url}" target="_blank" class="group/btn relative px-3 py-1.5 bg-[var(--accent)] text-slate-950 font-bold rounded-lg text-xs flex items-center gap-1.5 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_6px_20px_-4px_var(--accent-glow)] overflow-hidden"><span class="absolute inset-0 bg-gradient-to-r from-white/0 via-white/40 to-white/0 translate-x-[-100%] group-hover/btn:translate-x-[100%] transition-transform duration-700"></span><i data-lucide="play" class="relative w-3.5 h-3.5"></i><span class="relative">Live Demo</span></a>'
            )
        if p.link:
            actions.append(
                f'<a href="{p.link}" target="_blank" class="px-3 py-1.5 bg-slate-800 text-slate-200 font-medium rounded-lg text-xs border border-slate-700 flex items-center gap-1.5 hover:border-[var(--accent)] hover:text-white hover:-translate-y-0.5 transition-all duration-300"><i data-lucide="github" class="w-3.5 h-3.5"></i> Repo</a>'
            )

        project_cards.append(f"""
          <div class="reveal group relative bg-slate-950/60 backdrop-blur border border-slate-800/80 rounded-2xl p-5 flex flex-col justify-between space-y-3 hover:border-[var(--accent)]/60 hover:-translate-y-1 hover:shadow-[0_20px_50px_-20px_var(--accent-glow)] transition-all duration-500 overflow-hidden" style="transition-delay: {idx*80}ms">
            <!-- corner glow -->
            <div class="absolute -top-16 -right-16 w-32 h-32 rounded-full bg-[var(--accent)]/10 blur-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
            <!-- top accent line -->
            <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[var(--accent)]/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

            <div class="relative space-y-2">
              <div class="flex items-start justify-between gap-2">
                <h4 class="font-bold text-sm text-white group-hover:text-[var(--accent)] transition-colors duration-300 tracking-tight">{p.name}</h4>
                <div class="flex flex-wrap gap-1 justify-end">{tech}</div>
              </div>
              <ul class="space-y-1.5">{bullets}</ul>
            </div>
            <div class="relative flex items-center gap-2 pt-3 border-t border-slate-900/80">{"".join(actions)}</div>
          </div>
        """)

    # --- Experience timeline with pulsing dots ---
    exp_cards = []
    for exp in resume.work_experience:
        b_items = "".join(
            [
                f'<li class="text-xs text-slate-400 flex items-start gap-2"><span class="text-slate-600 mt-0.5 select-none">—</span><span>{b.lstrip("•- ")}</span></li>'
                for b in exp.bullet_points[:3]
            ]
        )
        exp_cards.append(f"""
          <div class="reveal relative pl-6 pb-6 border-l-2 border-slate-800/60 last:border-transparent last:pb-0 group">
            <div class="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full bg-slate-900 border-2 border-[var(--accent)] shadow-[0_0_0_0_var(--accent-glow)] group-hover:shadow-[0_0_0_6px_var(--accent-glow)] group-hover:scale-110 transition-all duration-500"></div>
            <div class="space-y-1.5">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <span class="font-bold text-xs text-slate-200 group-hover:text-white transition-colors duration-300">{exp.job_title} · <span class="text-[var(--accent)]">{exp.company}</span></span>
                <span class="text-[10px] font-mono text-slate-400 bg-slate-900 px-2 py-0.5 rounded-full border border-slate-800 group-hover:border-[var(--accent)]/50 transition-colors duration-300">{exp.start_date} – {exp.end_date}</span>
              </div>
              <ul class="space-y-1.5 pt-1.5">{b_items}</ul>
            </div>
          </div>
        """)

    # --- Skill chips with hover lift + border glow ---
    skills_badges = []
    for cat in resume.skill_categories:
        tags = "".join(
            [
                f'<span class="px-2.5 py-1 text-xs font-medium bg-slate-900/90 border border-slate-800/80 text-slate-300 rounded-lg hover:border-[var(--accent)]/70 hover:text-white hover:-translate-y-0.5 hover:shadow-[0_4px_12px_-2px_var(--accent-glow)] transition-all duration-300 cursor-default">{s}</span>'
                for s in cat.skills
            ]
        )
        skills_badges.append(f"""
          <div class="space-y-2.5">
            <h5 class="text-[11px] font-bold uppercase tracking-[0.12em] text-[var(--accent)] flex items-center gap-2">
              <span class="w-1 h-1 rounded-full bg-[var(--accent)] shadow-[0_0_6px_var(--accent-glow)]"></span>
              {cat.category_name}
            </h5>
            <div class="flex flex-wrap gap-1.5">{tags}</div>
          </div>
        """)

    # --- Education ---
    edu_badges = []
    for edu in resume.education:
        edu_badges.append(f"""
          <div class="reveal group p-3.5 bg-slate-900/60 backdrop-blur border border-slate-800/80 rounded-xl space-y-1.5 hover:border-[var(--accent)]/50 hover:-translate-y-0.5 hover:shadow-[0_8px_20px_-8px_var(--accent-glow)] transition-all duration-400">
            <div class="flex justify-between items-center gap-2 text-xs font-bold text-slate-200">
              <span class="group-hover:text-white transition-colors duration-300 tracking-tight">{edu.degree}</span>
              <span class="text-[var(--accent)] text-[11px] font-mono shrink-0">{edu.graduation_year}</span>
            </div>
            <p class="text-[11px] text-slate-400">{edu.institution}</p>
          </div>
        """)

    # --- Bento metrics with count-up ---
    if resume.portfolio_metrics:
        bento_metric_items = "".join([f"""
          <div class="reveal group relative p-3 bg-slate-950 rounded-2xl border border-slate-800 text-center hover:border-[var(--accent)]/50 transition-all duration-400 overflow-hidden" style="transition-delay: {i*70}ms">
            <div class="absolute inset-0 bg-gradient-to-br from-[var(--accent)]/0 to-[var(--accent)]/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <span class="relative block text-xl sm:text-2xl font-extrabold text-[var(--accent)] counter" data-target="{m.get("value", "0")}">{m.get("value", "0")}</span>
            <p class="relative text-[9px] text-slate-400 uppercase font-semibold truncate tracking-wider">{m.get("label", "Metric")}</p>
          </div>
        """ for i, m in enumerate(resume.portfolio_metrics[:4])])
    else:
        bento_metric_items = f"""
          <div class="reveal group relative p-3 bg-slate-950 rounded-2xl border border-slate-800 text-center hover:border-[var(--accent)]/50 transition-all duration-400 overflow-hidden">
            <div class="absolute inset-0 bg-gradient-to-br from-[var(--accent)]/0 to-[var(--accent)]/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <span class="relative block text-2xl font-extrabold text-[var(--accent)] counter" data-target="{len(resume.projects)}">0</span>
            <p class="relative text-[10px] text-slate-400 uppercase font-semibold tracking-wider">Key Projects</p>
          </div>
          <div class="reveal group relative p-3 bg-slate-950 rounded-2xl border border-slate-800 text-center hover:border-[var(--accent)]/50 transition-all duration-400 overflow-hidden">
            <div class="absolute inset-0 bg-gradient-to-br from-[var(--accent)]/0 to-[var(--accent)]/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
            <span class="relative block text-2xl font-extrabold text-white counter" data-target="{len(resume.work_experience)}">0</span>
            <p class="relative text-[10px] text-slate-400 uppercase font-semibold tracking-wider">Milestones</p>
          </div>
        """

    bio_html = (
        f'<p class="text-xs sm:text-sm text-slate-300/90 leading-relaxed max-w-xl">{summary}</p>'
        if resume.portfolio_show_bio
        else ""
    )

    joined_skills_badges = "".join(skills_badges)
    skills_card_html = (
        f"""
          <div class="reveal relative bg-slate-900/70 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 space-y-4 shadow-[0_8px_32px_-12px_rgba(0,0,0,0.6)] hover:border-slate-700 transition-all duration-500 overflow-hidden group">
            <div class="absolute -top-24 -right-24 w-48 h-48 rounded-full bg-[var(--accent)]/5 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
            <div class="relative flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
              <i data-lucide="cpu" class="w-4 h-4 text-[var(--accent)]"></i>
              <span>Technical Arsenal</span>
            </div>
            <div class="relative space-y-4">{joined_skills_badges}</div>
          </div>
    """
        if resume.portfolio_show_skills
        else ""
    )

    proj_col = "lg:col-span-2" if resume.portfolio_show_skills else "lg:col-span-3"
    joined_project_cards = "".join(project_cards)
    projects_card_html = (
        f"""
          <div class="reveal {proj_col} bg-slate-900/70 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-4 shadow-[0_8px_32px_-12px_rgba(0,0,0,0.6)] hover:border-slate-700 transition-all duration-500">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
              <div class="flex items-center gap-2 text-sm font-bold text-white">
                <i data-lucide="layers" class="w-4 h-4 text-[var(--accent)]"></i>
                <span>Featured Systems & Projects</span>
              </div>
              <span class="text-[11px] text-slate-400 font-mono">{len(resume.projects)} Production Builds</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">{joined_project_cards}</div>
          </div>
    """
        if resume.portfolio_show_projects
        else ""
    )

    exp_col = "lg:col-span-2" if resume.portfolio_show_education else "lg:col-span-3"
    joined_exp_cards = "".join(exp_cards)
    exp_card_html = (
        f"""
          <div class="reveal {exp_col} bg-slate-900/70 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 sm:p-8 space-y-4 shadow-[0_8px_32px_-12px_rgba(0,0,0,0.6)] hover:border-slate-700 transition-all duration-500">
            <div class="flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
              <i data-lucide="briefcase" class="w-4 h-4 text-[var(--accent)]"></i>
              <span>Career Trajectory</span>
            </div>
            <div class="pt-2 space-y-4">{joined_exp_cards}</div>
          </div>
    """
        if resume.portfolio_show_experience
        else ""
    )

    joined_edu_badges = "".join(edu_badges)
    edu_card_html = (
        f"""
          <div class="reveal bg-slate-900/70 backdrop-blur-xl border border-slate-800 rounded-3xl p-6 space-y-4 shadow-[0_8px_32px_-12px_rgba(0,0,0,0.6)] hover:border-slate-700 transition-all duration-500">
            <div class="flex items-center gap-2 text-sm font-bold text-white border-b border-slate-800 pb-3">
              <i data-lucide="graduation-cap" class="w-4 h-4 text-[var(--accent)]"></i>
              <span>Qualifications</span>
            </div>
            <div class="space-y-3">{joined_edu_badges}</div>
          </div>
    """
        if resume.portfolio_show_education
        else ""
    )

    return f"""
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600&display=swap');

        html {{ scroll-behavior: smooth; }}
        body {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; }}

        /* --- Keyframes --- */
        @keyframes floatY {{
          0%, 100% {{ transform: translateY(0); }}
          50% {{ transform: translateY(-6px); }}
        }}
        @keyframes gradientSpin {{
          0% {{ transform: rotate(0deg) scale(1); }}
          50% {{ transform: rotate(180deg) scale(1.05); }}
          100% {{ transform: rotate(360deg) scale(1); }}
        }}
        @keyframes fadeUp {{
          0% {{ opacity: 0; transform: translateY(28px); }}
          100% {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes pulseGlow {{
          0%, 100% {{ opacity: 0.4; transform: scale(1); }}
          50% {{ opacity: 0.8; transform: scale(1.08); }}
        }}
        @keyframes borderGlow {{
          0%, 100% {{ box-shadow: 0 0 0 0 var(--accent-glow); }}
          50% {{ box-shadow: 0 0 20px 2px var(--accent-glow); }}
        }}
        @keyframes shimmerSlide {{
          0% {{ transform: translateX(-100%); }}
          100% {{ transform: translateX(100%); }}
        }}
        @keyframes dotPulse {{
          0% {{ box-shadow: 0 0 0 0 rgba(16,185,129,0.6); }}
          70% {{ box-shadow: 0 0 0 8px rgba(16,185,129,0); }}
          100% {{ box-shadow: 0 0 0 0 rgba(16,185,129,0); }}
        }}

        .animate-float {{ animation: floatY 6s ease-in-out infinite; }}
        .animate-gradient-spin {{ animation: gradientSpin 12s linear infinite; }}
        .badge-pulse {{ animation: dotPulse 2.2s ease-out infinite; }}

        /* --- Scroll reveal --- */
        .reveal {{
          opacity: 0;
          transform: translateY(28px);
          transition: opacity 0.85s cubic-bezier(0.16,1,0.3,1),
                      transform 0.85s cubic-bezier(0.16,1,0.3,1);
          will-change: opacity, transform;
          backface-visibility: hidden;
        }}
        .reveal.is-visible {{
          opacity: 1;
          transform: translateY(0);
        }}

        /* --- Ambient background orbs --- */
        .bg-orb {{
          position: fixed;
          border-radius: 9999px;
          filter: blur(80px);
          pointer-events: none;
          z-index: 0;
        }}
        .bg-orb-1 {{
          top: -20%; left: -10%;
          width: 500px; height: 500px;
          background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
          opacity: 0.12;
          animation: pulseGlow 8s ease-in-out infinite;
        }}
        .bg-orb-2 {{
          top: 30%; right: -15%;
          width: 600px; height: 600px;
          background: radial-gradient(circle, #8b5cf6 0%, transparent 70%);
          opacity: 0.08;
          animation: pulseGlow 10s ease-in-out infinite 2s;
        }}
        .bg-orb-3 {{
          bottom: -10%; left: 30%;
          width: 500px; height: 500px;
          background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
          opacity: 0.06;
          animation: pulseGlow 12s ease-in-out infinite 4s;
        }}

        /* --- Scroll progress bar --- */
        #scroll-progress {{
          position: fixed;
  top: 0; left: 0;
  height: 2px;
  width: 0%;
  background: linear-gradient(90deg, var(--accent), #8b5cf6, var(--accent));
  background-size: 200% 100%;
  z-index: 100;
  transition: width 0.1s ease-out;
  box-shadow: 0 0 12px var(--accent-glow);
  /* ✅ FIX: use background-position animation instead of rotate */
  animation: gradientFlow 6s linear infinite;
  transform: none !important;
  transform-origin: left center;
        }}

        /* --- Grid backdrop grid lines --- */
        .bento-backdrop::before {{
          content: '';
          position: fixed;
          inset: 0;
          background-image:
            linear-gradient(rgba(148,163,184,0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(148,163,184,0.04) 1px, transparent 1px);
          background-size: 40px 40px;
          mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
          -webkit-mask-image: radial-gradient(ellipse at center, black 30%, transparent 80%);
          pointer-events: none;
          z-index: 0;
        }}
      </style>

      <!-- Scroll progress -->
      <div id="scroll-progress"></div>

      <!-- Ambient orbs -->
      <div class="bg-orb bg-orb-1"></div>
      <div class="bg-orb bg-orb-2"></div>
      <div class="bg-orb bg-orb-3"></div>

      <div class="relative bento-backdrop max-w-6xl mx-auto px-4 sm:px-6 py-10 space-y-6 z-10">

        <!-- BENTO ROW 1: Hero & Highlights -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

          <!-- Bento Card 1: Hero Identity (2 Cols) -->
          <div class="reveal lg:col-span-2 relative bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 rounded-3xl p-6 sm:p-8 flex flex-col sm:flex-row gap-6 items-center sm:items-start shadow-[0_8px_40px_-12px_rgba(0,0,0,0.6)] hover:border-[var(--accent)]/40 hover:shadow-[0_20px_60px_-20px_var(--accent-glow)] transition-all duration-500 overflow-hidden group">

            <!-- Animated corner glow -->
            <div class="absolute -right-16 -bottom-16 w-56 h-56 rounded-full bg-[var(--accent)]/15 blur-3xl pointer-events-none animate-pulse-glow"></div>

            <!-- Top accent line -->
            <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[var(--accent)]/60 to-transparent"></div>

            {avatar_elem}
            <div class="relative space-y-3.5 text-center sm:text-left flex-1">
              <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
                <span class="badge-pulse relative flex w-2 h-2 rounded-full bg-emerald-400"></span>
                <span>{badge_text}</span>
              </div>
              <div>
                <h1 class="text-2xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
                  <span class="bg-gradient-to-br from-white via-white to-slate-400 bg-clip-text text-transparent">{full_name}</span>
                </h1>
                <p class="text-sm sm:text-base font-semibold text-[var(--accent)] mt-1 tracking-tight">{role_title}</p>
              </div>
              {bio_html}
              <div class="flex flex-wrap gap-2.5 pt-2 justify-center sm:justify-start">
                <a href="{cta_url}" class="group/btn relative px-5 py-2.5 bg-[var(--accent)] text-slate-950 font-bold text-xs rounded-xl shadow-[0_8px_24px_-6px_var(--accent-glow)] flex items-center gap-1.5 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_12px_32px_-8px_var(--accent-glow)] overflow-hidden">
                  <span class="absolute inset-0 bg-gradient-to-r from-white/0 via-white/50 to-white/0 translate-x-[-100%] group-hover/btn:translate-x-[100%] transition-transform duration-700"></span>
                  <i data-lucide="sparkles" class="relative w-4 h-4 group-hover/btn:rotate-12 transition-transform duration-300"></i>
                  <span class="relative">{cta_text}</span>
                </a>
                {dl_button}
              </div>
            </div>
          </div>

          <!-- Bento Card 2: Quick Metrics & Socials (1 Col) -->
          <div class="reveal bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 rounded-3xl p-6 flex flex-col justify-between space-y-4 shadow-[0_8px_40px_-12px_rgba(0,0,0,0.6)] hover:border-[var(--accent)]/40 transition-all duration-500 relative overflow-hidden group">
            <div class="absolute -top-16 -left-16 w-40 h-40 rounded-full bg-[var(--accent)]/8 blur-3xl pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>

            <div class="relative space-y-3">
              <div class="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400">
                <i data-lucide="zap" class="w-4 h-4 text-[var(--accent)] group-hover:scale-110 group-hover:rotate-12 transition-transform duration-300"></i>
                <span>Executive Metric</span>
              </div>
              <div class="grid grid-cols-2 gap-2.5">
                {bento_metric_items}
              </div>
            </div>
            <div class="relative space-y-2.5">
              <span class="text-[10px] font-bold uppercase text-slate-500 tracking-[0.12em]">Connect Directly</span>
              <div class="flex flex-wrap gap-2">{socials_html}</div>
            </div>
          </div>

        </div>

        <!-- BENTO ROW 2: Tech Stack & Projects -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {skills_card_html}
          {projects_card_html}
        </div>

        <!-- BENTO ROW 3: Experience & Education -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {exp_card_html}
          {edu_card_html}
        </div>

      </div>

      <script>
        // --- Scroll reveal ---
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

        // --- Scroll progress bar ---
        (function() {{
          const bar = document.getElementById('scroll-progress');
          if (!bar) return;
          const update = () => {{
            const scrollTop = window.scrollY || document.documentElement.scrollTop;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;
            const pct = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
            bar.style.width = pct + '%';
          }};
          window.addEventListener('scroll', update, {{ passive: true }});
          update();
        }})();

        // --- Count-up animation for metrics ---
        (function() {{
          const counters = document.querySelectorAll('.counter');
          if (!counters.length) return;

          const animate = (el) => {{
            const raw = el.dataset.target || '0';
            const match = raw.match(/-?[\\d.]+/);
            if (!match) {{ el.textContent = raw; return; }}
            const targetNum = parseFloat(match[0]);
            const prefix = raw.slice(0, match.index);
            const suffix = raw.slice(match.index + match[0].length);
            const isInt = Number.isInteger(targetNum);
            const duration = 1400;
            const start = performance.now();

            const step = (now) => {{
              const t = Math.min(1, (now - start) / duration);
              const eased = 1 - Math.pow(1 - t, 3);
              const cur = targetNum * eased;
              el.textContent = prefix + (isInt ? Math.round(cur) : cur.toFixed(1)) + suffix;
              if (t < 1) requestAnimationFrame(step);
              else el.textContent = raw;
            }};
            requestAnimationFrame(step);
          }};

          if (!('IntersectionObserver' in window)) {{
            counters.forEach(animate);
            return;
          }}
          const io = new IntersectionObserver((entries) => {{
            entries.forEach(e => {{
              if (e.isIntersecting) {{
                animate(e.target);
                io.unobserve(e.target);
              }}
            }});
          }}, {{ threshold: 0.5 }});
          counters.forEach(el => io.observe(el));
        }})();
      </script>
    """
