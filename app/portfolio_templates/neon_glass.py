"""
Theme: Neon Glass — Ultra-Premium Neo-Glassmorphism 3D Glow
Design: Cosmic aurora background, layered frosted glass, animated neon borders,
        cinematic scroll reveals, 3D tilt cards, shimmer micro-interactions.
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
    render_cert_badge_thumb,
    render_personal_kyc_strip,
    render_spoken_languages_block,
    render_references_block,
    render_whatsapp_cta_button,
)


def render_neon_glass(resume: TailoredResume, accent: str) -> str:
    info = resume.personal_info
    full_name = info.full_name or "Candidate"
    role_title = (resume.target_job_title or "").strip()
    role_html = f'<p class="text-base sm:text-xl font-semibold text-[var(--accent)] tracking-tight">{role_title}</p>' if role_title else ""
    summary = resume.professional_summary or ""
    avatar_url = info.avatar_url or ""
    badge_text = info.availability_badge or "Available for Impact"
    cta_text = resume.portfolio_cta_text or "Connect Now"
    wa_hero_btn = render_whatsapp_cta_button(resume, size="hero", label="WhatsApp Connect")
    wa_contact_btn = render_whatsapp_cta_button(resume, size="standard", label="Chat on WhatsApp")
    cta_url = resume.portfolio_cta_url or (
        f"mailto:{info.email}" if info.email else "#contact"
    )

    # --- Avatar with animated rotating gradient ring ---
    if avatar_url:
        avatar_elem = f"""
          <div class="relative shrink-0 animate-float">
            <div class="absolute -inset-2 rounded-full bg-[conic-gradient(from_0deg,var(--accent),#a855f7,#06b6d4,var(--accent))] opacity-90 blur-[2px] animate-spin-slow"></div>
            <div class="absolute -inset-6 rounded-full bg-[var(--accent)] opacity-30 blur-2xl animate-pulse-glow"></div>
            <img src="{avatar_url}" alt="{full_name}"
                 class="relative w-28 h-28 rounded-full object-cover ring-2 ring-slate-950/80 shadow-[0_0_40px_-4px_var(--accent-glow)]">
          </div>
        """
    else:
        initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "NG"
        avatar_elem = f"""
          <div class="relative shrink-0 animate-float">
            <div class="absolute -inset-2 rounded-full bg-[conic-gradient(from_0deg,var(--accent),#a855f7,#06b6d4,var(--accent))] opacity-90 blur-[2px] animate-spin-slow"></div>
            <div class="absolute -inset-6 rounded-full bg-[var(--accent)] opacity-30 blur-2xl animate-pulse-glow"></div>
            <div class="relative w-28 h-28 rounded-full bg-slate-950 p-[3px] shadow-2xl shadow-[var(--accent-glow)] flex items-center justify-center">
              <div class="w-full h-full bg-gradient-to-br from-slate-900 to-slate-950 rounded-full flex items-center justify-center ring-1 ring-white/10">
                <span class="bg-gradient-to-br from-white via-white to-[var(--accent)] bg-clip-text text-transparent text-3xl font-black tracking-tight">{initials}</span>
              </div>
            </div>
          </div>
        """

    # --- Social pills with neon trace + shimmer ---
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
                class="group relative p-3 rounded-2xl bg-white/[0.04] backdrop-blur-xl border border-white/10 hover:border-[var(--accent)]/70 hover:shadow-[0_0_28px_-4px_var(--accent-glow)] text-slate-200 transition-all duration-400 flex items-center gap-2 text-xs font-medium hover:-translate-y-1 overflow-hidden">
                <span class="absolute inset-0 bg-gradient-to-r from-transparent via-[var(--accent)]/15 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></span>
                <span class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[var(--accent)]/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></span>
                <i data-lucide="{icon}" class="relative w-4 h-4 text-[var(--accent)] group-hover:scale-110 transition-transform duration-300"></i>
                <span class="relative">{link.name}</span>
              </a>
            """)
    socials_bar = (
        f'<div class="flex flex-wrap justify-center gap-3 pt-2">{"".join(social_links)}</div>'
        if social_links
        else ""
    )

    # --- Projects with 3D tilt hint + corner glow + trace border ---
    projects = []
    for idx, p in enumerate(resume.projects):
        tech = "".join(
            [
                f'<span class="px-2 py-0.5 text-[10px] bg-white/[0.04] border border-white/10 rounded-md text-slate-300 font-medium hover:border-[var(--accent)]/60 hover:text-[var(--accent)] hover:-translate-y-0.5 transition-all duration-300 cursor-default">{t}</span>'
                for t in p.technologies
            ]
        )
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-300/90 flex items-start gap-2"><span class="text-[var(--accent)] mt-0.5 select-none">▸</span><span>{b.lstrip("•- ")}</span></li>'
                for b in p.description_bullets[:2]
            ]
        )
        actions = []
        if p.demo_url:
            actions.append(
                f'<a href="{p.demo_url}" target="_blank" class="group/btn relative px-3 py-1.5 bg-[var(--accent)] text-slate-950 font-bold rounded-lg text-xs transition-all duration-300 flex items-center gap-1 hover:-translate-y-0.5 hover:shadow-[0_8px_24px_-6px_var(--accent-glow)] overflow-hidden"><span class="absolute inset-0 bg-gradient-to-r from-white/0 via-white/50 to-white/0 translate-x-[-100%] group-hover/btn:translate-x-[100%] transition-transform duration-700"></span><i data-lucide="play" class="relative w-3 h-3"></i><span class="relative">Live</span></a>'
            )
        if p.link:
            actions.append(
                f'<a href="{p.link}" target="_blank" class="px-3 py-1.5 bg-white/[0.06] text-white border border-white/10 rounded-lg text-xs transition-all duration-300 flex items-center gap-1 hover:bg-white/[0.12] hover:border-[var(--accent)]/50 hover:-translate-y-0.5"><i data-lucide="github" class="w-3 h-3"></i> Code</a>'
            )

        projects.append(f"""
          <div class="reveal group relative bg-white/[0.04] backdrop-blur-2xl border border-white/10 hover:border-[var(--accent)]/60 hover:shadow-[0_20px_60px_-20px_var(--accent-glow)] rounded-3xl p-6 space-y-4 transition-all duration-500 overflow-hidden hover:-translate-y-2" style="transition-delay: {idx*90}ms">
            <!-- Inner highlight -->
            <div class="absolute inset-0 rounded-3xl bg-gradient-to-br from-white/[0.08] via-transparent to-transparent pointer-events-none"></div>
            <!-- Corner glow -->
            <div class="absolute -top-24 -right-24 w-56 h-56 rounded-full bg-[var(--accent)]/20 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"></div>
            <!-- Bottom-left subtle glow -->
            <div class="absolute -bottom-16 -left-16 w-40 h-40 rounded-full bg-purple-500/10 blur-3xl opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"></div>
            <!-- Top trace line -->
            <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[var(--accent)]/70 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

            <div class="relative flex items-center justify-between gap-3">
              <h4 class="font-bold text-base text-white group-hover:text-[var(--accent)] transition-colors duration-300 tracking-tight">{p.name}</h4>
              <div class="flex items-center gap-2 shrink-0">{"".join(actions)}</div>
            </div>
            <div class="relative flex flex-wrap gap-1.5">{tech}</div>
            <ul class="relative space-y-1.5">{bullets}</ul>
          </div>
        """)

    bio_html = (
        f'<p class="text-sm sm:text-base text-slate-300/90 max-w-2xl mx-auto leading-relaxed">{summary}</p>'
        if resume.portfolio_show_bio
        else ""
    )

    resume_btn_html = (
        f"""
              <button onclick="triggerPortfolioCvDownload()"
                class="group relative px-5 py-3 bg-white/[0.06] hover:bg-white/[0.12] backdrop-blur-xl border border-white/15 hover:border-[var(--accent)]/60 text-white font-semibold text-xs rounded-xl transition-all duration-300 flex items-center gap-2 hover:-translate-y-0.5 hover:shadow-[0_12px_32px_-8px_var(--accent-glow)] overflow-hidden">
                <span class="absolute inset-0 bg-gradient-to-r from-transparent via-[var(--accent)]/10 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></span>
                <i data-lucide="file-down" class="relative w-4 h-4 text-[var(--accent)] group-hover:translate-y-0.5 transition-transform duration-300"></i>
                <span class="relative">Download ATS CV</span>
              </button>
    """
        if resume.portfolio_show_resume_download
        else ""
    )

    joined_projects = "".join(projects)
    projects_showcase_html = (
        f"""
          <div class="reveal space-y-6">
            <div class="flex items-center gap-2.5 text-xl font-bold text-white">
              <span class="relative flex items-center justify-center w-8 h-8 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/30">
                <i data-lucide="layers" class="w-4 h-4 text-[var(--accent)]"></i>
              </span>
              <span class="bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Featured Creations & Systems</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">{joined_projects}</div>
          </div>
    """
        if (resume.portfolio_show_projects and getattr(resume, "show_projects", True) and len(resume.projects) > 0)
        else ""
    )

    # --- Experience timeline with pulsing neon dots ---
    exp_items_list = []
    for idx, e in enumerate(resume.work_experience):
        bp_text = " ".join([b.lstrip("•- ") for b in e.bullet_points[:2]])
        exp_items_list.append(f"""
          <div class="reveal group relative border-l-2 border-white/10 hover:border-[var(--accent)]/60 pl-5 space-y-2 transition-all duration-500 py-1" style="transition-delay: {idx*90}ms">
            <span class="absolute -left-[7px] top-2 w-3 h-3 rounded-full bg-slate-950 border-2 border-[var(--accent)] shadow-[0_0_0_0_var(--accent-glow)] group-hover:shadow-[0_0_0_6px_var(--accent-glow)] transition-all duration-500"></span>
            <div class="flex flex-wrap justify-between items-center gap-2">
              <h4 class="font-bold text-white text-sm group-hover:text-[var(--accent)] transition-colors duration-300 tracking-tight">{e.job_title} · <span class="text-[var(--accent)]">{e.company}</span></h4>
              <span class="text-[11px] text-slate-400 font-mono bg-white/[0.04] border border-white/10 px-2.5 py-0.5 rounded-full group-hover:border-[var(--accent)]/40 transition-colors duration-300">{e.start_date} – {e.end_date}</span>
            </div>
            <p class="text-xs text-slate-300/90 pt-1 leading-relaxed">{bp_text}</p>
          </div>
        """)
    joined_exp_items = "".join(exp_items_list)

    exp_showcase_html = (
        f"""
          <div class="reveal bg-white/[0.04] backdrop-blur-2xl border border-white/10 rounded-3xl p-8 space-y-6 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6)] relative overflow-hidden hover:border-white/20 transition-all duration-500">
            <div class="absolute -top-32 -right-32 w-72 h-72 rounded-full bg-[var(--accent)]/10 blur-3xl pointer-events-none"></div>
            <div class="absolute inset-0 rounded-3xl bg-gradient-to-br from-white/[0.06] via-transparent to-transparent pointer-events-none"></div>
            <div class="relative flex items-center gap-2.5 text-xl font-bold text-white border-b border-white/10 pb-4">
              <span class="relative flex items-center justify-center w-8 h-8 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/30">
                <i data-lucide="briefcase" class="w-4 h-4 text-[var(--accent)]"></i>
              </span>
              <span class="bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Professional Milestone Timeline</span>
            </div>
            <div class="relative space-y-6">
              {joined_exp_items}
            </div>
          </div>
    """
        if resume.portfolio_show_experience
        else ""
    )

    # --- Skills chips with neon hover ---
    skill_cards_list = []
    for c in resume.skill_categories:
        rendered_skills = "".join(
            [
                f'<span class="px-2.5 py-1 text-xs bg-white/[0.05] border border-white/10 rounded-lg text-slate-200 hover:bg-[var(--accent)]/10 hover:border-[var(--accent)]/60 hover:text-[var(--accent)] hover:-translate-y-0.5 hover:shadow-[0_4px_14px_-4px_var(--accent-glow)] transition-all duration-300 cursor-default">{s}</span>'
                for s in c.skills
            ]
        )
        skill_cards_list.append(f"""
          <div class="space-y-2.5">
            <h5 class="text-[11px] font-bold text-[var(--accent)] uppercase tracking-[0.12em] flex items-center gap-2">
              <span class="w-1 h-1 rounded-full bg-[var(--accent)] shadow-[0_0_8px_var(--accent-glow)]"></span>
              {c.category_name}
            </h5>
            <div class="flex flex-wrap gap-1.5">{rendered_skills}</div>
          </div>
        """)
    joined_skill_cards = "".join(skill_cards_list)

    num_cats = len(resume.skill_categories)
    if num_cats <= 1:
        skills_grid_class = "relative grid grid-cols-1 gap-6"
    elif num_cats == 2:
        skills_grid_class = "relative grid grid-cols-1 sm:grid-cols-2 gap-6"
    elif num_cats == 3:
        skills_grid_class = "relative grid grid-cols-1 sm:grid-cols-3 gap-6"
    else:
        skills_grid_class = "relative grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6"

    skills_showcase_html = (
        f"""
          <div class="reveal bg-white/[0.04] backdrop-blur-2xl border border-white/10 rounded-3xl p-8 space-y-5 relative overflow-hidden hover:border-white/20 transition-all duration-500">
            <div class="absolute -bottom-32 -left-32 w-72 h-72 rounded-full bg-purple-500/10 blur-3xl pointer-events-none"></div>
            <div class="absolute inset-0 rounded-3xl bg-gradient-to-br from-white/[0.06] via-transparent to-transparent pointer-events-none"></div>
            <div class="relative flex items-center gap-2.5 text-xl font-bold text-white border-b border-white/10 pb-4">
              <span class="relative flex items-center justify-center w-8 h-8 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/30">
                <i data-lucide="cpu" class="w-4 h-4 text-[var(--accent)]"></i>
              </span>
              <span class="bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Technical Competencies</span>
            </div>
            <div class="{skills_grid_class}">
              {joined_skill_cards}
            </div>
          </div>
    """
        if resume.portfolio_show_skills
        else ""
    )

    # --- Education Showcase (Frosted Glass) ---
    show_edu = (
        getattr(resume, "portfolio_show_education", True)
        and getattr(resume, "show_education", True)
        and len(resume.education) > 0
    )
    edu_cards = []
    for edu in resume.education:
        details_html = f'<p class="text-xs text-slate-300/80 pt-1 leading-relaxed">{edu.details}</p>' if getattr(edu, "details", None) else ''
        loc_html = f'<span class="text-slate-500">·</span> {edu.location}' if getattr(edu, "location", None) else ''
        year_html = f'<span class="text-[11px] font-mono text-[var(--accent)] bg-white/[0.04] border border-white/10 px-2.5 py-0.5 rounded-full shrink-0">{edu.graduation_year}</span>' if getattr(edu, "graduation_year", None) else ''
        edu_cards.append(f"""
          <div class="reveal group p-5 bg-white/[0.03] border border-white/10 rounded-2xl hover:border-[var(--accent)]/50 hover:bg-white/[0.06] transition-all duration-300 space-y-2">
            <div class="flex flex-wrap justify-between items-start gap-2">
              <div>
                <h4 class="font-bold text-white text-sm group-hover:text-[var(--accent)] transition-colors">{edu.degree}</h4>
                <p class="text-xs font-semibold text-[var(--accent)]">{edu.institution} {loc_html}</p>
              </div>
              {year_html}
            </div>
            {details_html}
          </div>
        """)
    edu_grid_class = "grid grid-cols-1 sm:grid-cols-2 gap-4" if len(edu_cards) >= 2 else "grid grid-cols-1 gap-4"
    edu_showcase_html = f"""
          <div class="reveal bg-white/[0.04] backdrop-blur-2xl border border-white/10 rounded-3xl p-8 space-y-6 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6)] relative overflow-hidden hover:border-white/20 transition-all duration-500">
            <div class="relative flex items-center gap-2.5 text-xl font-bold text-white border-b border-white/10 pb-4">
              <span class="relative flex items-center justify-center w-8 h-8 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/30">
                <i data-lucide="graduation-cap" class="w-4 h-4 text-[var(--accent)]"></i>
              </span>
              <span class="bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Academic Background & Qualifications</span>
            </div>
            <div class="{edu_grid_class}">
              {''.join(edu_cards)}
            </div>
          </div>
    """ if show_edu else ""

    # --- Certifications Showcase (Neon Glow Badges) ---
    raw_certs = getattr(resume, "certifications", []) or []
    show_certs = (
        getattr(resume, "portfolio_show_certifications", True)
        and len(raw_certs) > 0
    )
    cert_cards = []
    for cert in raw_certs:
        issuer_html = f'<p class="text-xs text-slate-400">{cert.issuer}</p>' if getattr(cert, "issuer", None) else ''
        year_html = f'<span class="text-[10px] font-mono text-slate-400 bg-white/[0.04] px-2 py-0.5 rounded border border-white/10">{cert.year}</span>' if getattr(cert, "year", None) else ''
        url_html = render_cert_badge_thumb(cert)
        cert_cards.append(f"""
          <div class="reveal group p-4 bg-white/[0.03] border border-white/10 rounded-2xl hover:border-[var(--accent)]/60 hover:shadow-[0_8px_24px_-6px_var(--accent-glow)] transition-all duration-300 flex items-center justify-between gap-3">
            <div class="flex items-center gap-3.5 min-w-0">
              <div class="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-400 flex items-center justify-center shrink-0">
                <i data-lucide="award" class="w-5 h-5"></i>
              </div>
              <div class="min-w-0">
                <h4 class="font-bold text-white text-sm truncate group-hover:text-[var(--accent)] transition-colors">{cert.name}</h4>
                <div class="flex items-center gap-2">{issuer_html} {year_html}</div>
              </div>
            </div>
            {url_html}
          </div>
        """)
    cert_grid_class = "grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4" if len(cert_cards) >= 3 else "grid grid-cols-1 sm:grid-cols-2 gap-4"
    cert_showcase_html = f"""
          <div class="reveal bg-white/[0.04] backdrop-blur-2xl border border-white/10 rounded-3xl p-8 space-y-6 shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6)] relative overflow-hidden hover:border-white/20 transition-all duration-500">
            <div class="relative flex items-center gap-2.5 text-xl font-bold text-white border-b border-white/10 pb-4">
              <span class="relative flex items-center justify-center w-8 h-8 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/30">
                <i data-lucide="award" class="w-4 h-4 text-[var(--accent)]"></i>
              </span>
              <span class="bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">Verified Credentials & Certifications</span>
            </div>
            <div class="{cert_grid_class}">
              {''.join(cert_cards)}
            </div>
          </div>
    """ if show_certs else ""

    # --- Contact Showcase ---
    contact_neon_cards = []
    if info.email:
        contact_neon_cards.append(f'''
          <a href="mailto:{info.email}" class="p-4 rounded-2xl bg-white/[0.04] border border-white/10 hover:border-[var(--accent)] hover:bg-white/[0.08] transition-all flex items-center gap-3.5 group">
            <div class="w-10 h-10 rounded-xl bg-[var(--accent)]/10 text-[var(--accent)] flex items-center justify-center shrink-0">
              <i data-lucide="mail" class="w-5 h-5"></i>
            </div>
            <div class="min-w-0">
              <span class="text-[10px] text-slate-400 font-bold uppercase block">Electronic Mail</span>
              <span class="text-xs font-bold text-white group-hover:text-[var(--accent)] transition truncate block">{info.email}</span>
            </div>
          </a>
        ''')
    if info.phone:
        contact_neon_cards.append(f'''
          <a href="tel:{info.phone}" class="p-4 rounded-2xl bg-white/[0.04] border border-white/10 hover:border-emerald-400 hover:bg-white/[0.08] transition-all flex items-center gap-3.5 group">
            <div class="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center shrink-0">
              <i data-lucide="phone" class="w-5 h-5"></i>
            </div>
            <div class="min-w-0">
              <span class="text-[10px] text-slate-400 font-bold uppercase block">Direct Line</span>
              <span class="text-xs font-bold text-white group-hover:text-emerald-400 transition truncate block">{info.phone}</span>
            </div>
          </a>
        ''')
    if info.location:
        contact_neon_cards.append(f'''
          <div class="p-4 rounded-2xl bg-white/[0.04] border border-white/10 flex items-center gap-3.5">
            <div class="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0">
              <i data-lucide="map-pin" class="w-5 h-5"></i>
            </div>
            <div class="min-w-0">
              <span class="text-[10px] text-slate-400 font-bold uppercase block">Location / Timezone</span>
              <span class="text-xs font-bold text-slate-300 truncate block">{info.location}</span>
            </div>
          </div>
        ''')

    contact_showcase_html = f'''
          <div id="contact" class="reveal bg-white/[0.04] backdrop-blur-2xl border border-white/10 rounded-3xl p-8 space-y-6 relative overflow-hidden hover:border-white/20 transition-all duration-500 scroll-mt-12">
            <div class="absolute -top-32 -right-32 w-72 h-72 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none"></div>
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-4">
              <div class="space-y-1">
                <div class="flex items-center gap-2.5 text-xl font-bold text-white">
                  <span class="w-8 h-8 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/30 flex items-center justify-center">
                    <i data-lucide="send" class="w-4 h-4 text-[var(--accent)]"></i>
                  </span>
                  <span>Direct Communication & Connect</span>
                </div>
                <p class="text-xs text-slate-400">Available for technical roles, freelance development, and engineering consulting.</p>
              </div>
              <div class="flex flex-wrap items-center gap-2 shrink-0">
                <a href="{cta_url}" class="px-5 py-2.5 bg-[var(--accent)] text-slate-950 font-bold text-xs rounded-xl shadow-[0_12px_36px_-8px_var(--accent-glow)] hover:brightness-110 transition shrink-0 flex items-center gap-2">
                  <i data-lucide="send" class="w-3.5 h-3.5"></i>
                  <span>{cta_text}</span>
                </a>
                {wa_contact_btn}
              </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {''.join(contact_neon_cards)}
            </div>
            <div class="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400 pt-2">
              <span class="flex items-center gap-1.5 text-emerald-400">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                {info.availability_badge or "Available for appointments"}
              </span>
              <div class="flex items-center gap-2">{socials_bar}</div>
            </div>
          </div>
    '''
    return f"""
      <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

        html {{ scroll-behavior: smooth; }}
        body {{ font-family: 'Inter', system-ui, -apple-system, sans-serif; }}
        h1, h2, h3 {{ font-family: 'Space Grotesk', 'Inter', sans-serif; letter-spacing: -0.02em; }}
        .font-mono {{ font-family: 'JetBrains Mono', monospace; }}

        /* --- Keyframes --- */
        @keyframes floatY {{
          0%, 100% {{ transform: translateY(0); }}
          50% {{ transform: translateY(-8px); }}
        }}
        @keyframes spinSlow {{
          0% {{ transform: rotate(0deg); }}
          100% {{ transform: rotate(360deg); }}
        }}
        @keyframes pulseGlow {{
          0%, 100% {{ opacity: 0.35; transform: scale(1); }}
          50% {{ opacity: 0.75; transform: scale(1.12); }}
        }}
        @keyframes orbDrift1 {{
          0%, 100% {{ transform: translate(0, 0) scale(1); }}
          50% {{ transform: translate(60px, -40px) scale(1.15); }}
        }}
        @keyframes orbDrift2 {{
          0%, 100% {{ transform: translate(0, 0) scale(1); }}
          50% {{ transform: translate(-70px, 50px) scale(1.1); }}
        }}
        @keyframes orbDrift3 {{
          0%, 100% {{ transform: translate(0, 0) scale(1); }}
          50% {{ transform: translate(40px, 60px) scale(1.08); }}
        }}
        @keyframes auroraShift {{
          0%, 100% {{ background-position: 0% 50%; }}
          50% {{ background-position: 100% 50%; }}
        }}
        @keyframes dotPulse {{
          0% {{ box-shadow: 0 0 0 0 rgba(16,185,129,0.6); }}
          70% {{ box-shadow: 0 0 0 8px rgba(16,185,129,0); }}
          100% {{ box-shadow: 0 0 0 0 rgba(16,185,129,0); }}
        }}
        @keyframes gridFade {{
          0%, 100% {{ opacity: 0.35; }}
          50% {{ opacity: 0.55; }}
        }}

        .animate-float {{ animation: floatY 6s ease-in-out infinite; }}
        .animate-spin-slow {{ animation: spinSlow 8s linear infinite; }}
        .animate-pulse-glow {{ animation: pulseGlow 4s ease-in-out infinite; }}
        .badge-pulse {{ animation: dotPulse 2.2s ease-out infinite; }}

        /* --- Scroll reveal --- */
        .reveal {{
          opacity: 0;
          transform: translateY(32px);
          transition: opacity 0.9s cubic-bezier(0.16,1,0.3,1),
                      transform 0.9s cubic-bezier(0.16,1,0.3,1);
          will-change: opacity, transform;
          backface-visibility: hidden;
        }}
        .reveal.is-visible {{
          opacity: 1;
          transform: translateY(0);
        }}

        /* --- Cosmic background orbs --- */
        .cosmic-orb {{
          position: fixed;
          border-radius: 9999px;
          filter: blur(120px);
          pointer-events: none;
          z-index: 0;
        }}
        .cosmic-1 {{
          top: -10%; left: 15%;
          width: 520px; height: 520px;
          background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
          opacity: 0.28;
          animation: orbDrift1 18s ease-in-out infinite;
        }}
        .cosmic-2 {{
          top: 35%; right: -10%;
          width: 620px; height: 620px;
          background: radial-gradient(circle, #a855f7 0%, transparent 70%);
          opacity: 0.22;
          animation: orbDrift2 22s ease-in-out infinite;
        }}
        .cosmic-3 {{
          bottom: -10%; left: 25%;
          width: 560px; height: 560px;
          background: radial-gradient(circle, #06b6d4 0%, transparent 70%);
          opacity: 0.18;
          animation: orbDrift3 20s ease-in-out infinite;
        }}
        .cosmic-4 {{
          top: 60%; left: -10%;
          width: 480px; height: 480px;
          background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
          opacity: 0.16;
          animation: orbDrift1 24s ease-in-out infinite reverse;
        }}

        /* --- Aurora backdrop sweep --- */
        .aurora-sweep {{
          position: fixed;
          inset: 0;
          background:
            radial-gradient(ellipse 80% 50% at 50% -20%, var(--accent) 0%, transparent 60%),
            radial-gradient(ellipse 60% 40% at 80% 100%, #a855f7 0%, transparent 60%);
          opacity: 0.10;
          pointer-events: none;
          z-index: 0;
          animation: gridFade 10s ease-in-out infinite;
        }}

        /* --- Subtle grid overlay --- */
        .grid-overlay {{
          position: fixed;
          inset: 0;
          background-image:
            linear-gradient(rgba(148,163,184,0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(148,163,184,0.05) 1px, transparent 1px);
          background-size: 48px 48px;
          mask-image: radial-gradient(ellipse at center, black 20%, transparent 75%);
          -webkit-mask-image: radial-gradient(ellipse at center, black 20%, transparent 75%);
          pointer-events: none;
          z-index: 0;
          animation: gridFade 12s ease-in-out infinite;
        }}

        /* --- Scroll progress bar --- */
        #ng-scroll-progress {{
          position: fixed;
          top: 0; left: 0;
          height: 2px;
          width: 0%;
          background: linear-gradient(90deg, var(--accent), #a855f7, #06b6d4, var(--accent));
          background-size: 300% 100%;
          z-index: 100;
          transition: width 0.1s ease-out;
          box-shadow: 0 0 14px var(--accent-glow);
          animation: auroraShift 5s linear infinite;
          transform: none !important;
        }}

        /* --- Glass card base --- */
        .glass-card {{
          background: rgba(255,255,255,0.04);
          backdrop-filter: blur(24px);
          -webkit-backdrop-filter: blur(24px);
          border: 1px solid rgba(255,255,255,0.10);
        }}
      </style>

      <!-- Scroll progress -->
      <div id="ng-scroll-progress"></div>

      <!-- Cosmic background -->
      <div class="cosmic-orb cosmic-1"></div>
      <div class="cosmic-orb cosmic-2"></div>
      <div class="cosmic-orb cosmic-3"></div>
      <div class="cosmic-orb cosmic-4"></div>
      <div class="aurora-sweep"></div>
      <div class="grid-overlay"></div>

      <div class="relative overflow-hidden min-h-screen py-16 px-4 sm:px-8 z-10">

        <div class="max-w-5xl mx-auto space-y-16 relative z-10">

          <!-- Hero Center Showcase -->
          <div class="reveal glass-card rounded-[2rem] p-8 sm:p-12 text-center space-y-6 shadow-[0_30px_80px_-30px_rgba(0,0,0,0.7)] relative overflow-hidden">
            <!-- inner highlight -->
            <div class="absolute inset-0 rounded-[2rem] bg-gradient-to-br from-white/[0.08] via-transparent to-transparent pointer-events-none"></div>
            <!-- top trace -->
            <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[var(--accent)]/70 to-transparent"></div>
            <!-- corner glow -->
            <div class="absolute -top-32 -right-32 w-80 h-80 rounded-full bg-[var(--accent)]/15 blur-3xl pointer-events-none animate-pulse-glow"></div>
            <div class="absolute -bottom-32 -left-32 w-80 h-80 rounded-full bg-purple-500/10 blur-3xl pointer-events-none"></div>

            <div class="relative flex justify-center">{avatar_elem}</div>
            <div class="relative space-y-3">
              <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 backdrop-blur border border-emerald-500/30 text-emerald-400 text-xs font-semibold shadow-[0_0_20px_-4px_rgba(16,185,129,0.5)]">
                <span class="badge-pulse relative flex w-2 h-2 rounded-full bg-emerald-400"></span>
                <span>{badge_text}</span>
              </div>
              <h1 class="text-3xl sm:text-6xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-100 to-[var(--accent)] tracking-tight leading-[1.05]">{full_name}</h1>
              <p class="text-base sm:text-xl font-semibold text-[var(--accent)] tracking-tight">{role_title}</p>
            </div>
            {bio_html}

            <div class="relative flex flex-wrap justify-center gap-3 pt-2">
              <a href="{cta_url}" class="group/btn relative px-6 py-3 bg-[var(--accent)] text-slate-950 font-bold text-xs rounded-xl shadow-[0_12px_36px_-8px_var(--accent-glow)] hover:shadow-[0_20px_48px_-10px_var(--accent-glow)] hover:-translate-y-1 transition-all duration-300 flex items-center gap-2 overflow-hidden">
                <span class="absolute inset-0 bg-gradient-to-r from-white/0 via-white/60 to-white/0 translate-x-[-100%] group-hover/btn:translate-x-[100%] transition-transform duration-700"></span>
                <i data-lucide="sparkles" class="relative w-4 h-4 group-hover/btn:rotate-12 transition-transform duration-300"></i>
                <span class="relative">{cta_text}</span>
              </a>
              {wa_hero_btn}
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

          <!-- Education Showcase -->
          {edu_showcase_html}

          <!-- Certifications Showcase -->
          {cert_showcase_html}

          <!-- Languages Showcase -->
          {render_spoken_languages_block(resume, card_bg="bg-white/[0.04]", border="border-white/10")}

          <!-- References Showcase -->
          {render_references_block(resume, card_bg="bg-white/[0.04]", border="border-white/10")}

          <!-- Personal KYC Strip -->
          {render_personal_kyc_strip(resume, card_bg="bg-white/[0.04]", border="border-white/10")}

          <!-- Contact Showcase -->
          {contact_showcase_html}

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
          }}, {{ threshold: 0.12, rootMargin: '0px 0px -60px 0px' }});
          els.forEach(el => io.observe(el));
        }})();

        // --- Scroll progress bar ---
        (function() {{
          const bar = document.getElementById('ng-scroll-progress');
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
      </script>
    """
