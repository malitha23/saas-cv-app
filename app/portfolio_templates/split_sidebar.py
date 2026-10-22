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
    role_title = (resume.target_job_title or "").strip()
    role_html = f'<p class="text-base font-semibold text-[var(--accent)]">{role_title}</p>' if role_title else ""
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
                <button onclick="triggerPortfolioCvDownload()"
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
                <h2 class="text-lg font-bold text-white">Key Projects & Initiatives</h2>
              </div>
              <div class="space-y-4">{joined_project_items}</div>
            </section>
    ''' if (resume.portfolio_show_projects and getattr(resume, "show_projects", True) and len(resume.projects) > 0) else ''

    skill_cards_list = []
    for c in resume.skill_categories:
        rendered_skills = "".join([f'<span class="px-2 py-0.5 text-xs bg-slate-950 border border-slate-800 text-slate-300 rounded">{s}</span>' for s in c.skills])
        skill_cards_list.append(f'<div class="p-4 bg-slate-900/60 border border-slate-800 rounded-xl space-y-2"><h4 class="text-xs font-bold text-[var(--accent)] uppercase">{c.category_name}</h4><div class="flex flex-wrap gap-1.5">{rendered_skills}</div></div>')
    joined_skill_cards = "".join(skill_cards_list)

    num_cats = len(resume.skill_categories)
    if num_cats <= 1:
        skills_grid_class = "grid grid-cols-1 gap-4"
    elif num_cats == 2:
        skills_grid_class = "grid grid-cols-1 sm:grid-cols-2 gap-4"
    elif num_cats == 3:
        skills_grid_class = "grid grid-cols-1 sm:grid-cols-3 gap-4"
    else:
        skills_grid_class = "grid grid-cols-1 sm:grid-cols-2 gap-4"

    skills_section_html = f'''
            <section id="skills" class="space-y-6">
              <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
                <i data-lucide="cpu" class="w-5 h-5 text-[var(--accent)]"></i>
                <h2 class="text-lg font-bold text-white">Core Competencies & Stack</h2>
              </div>
              <div class="{skills_grid_class}">
                {joined_skill_cards}
              </div>
            </section>
    ''' if resume.portfolio_show_skills else ''

    # --- Education ---
    show_edu = (
        getattr(resume, "portfolio_show_education", True)
        and getattr(resume, "show_education", True)
        and len(resume.education) > 0
    )
    edu_items = []
    for edu in resume.education:
        details_html = f'<p class="text-xs text-slate-400 pt-1 leading-relaxed">{edu.details}</p>' if getattr(edu, "details", None) else ''
        loc_suffix = f' · {edu.location}' if getattr(edu, "location", None) else ''
        year_html = f'<span class="text-xs font-mono text-[var(--accent)] font-semibold">{edu.graduation_year}</span>' if getattr(edu, "graduation_year", None) else ''
        edu_items.append(f"""
          <div class="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-5 space-y-2 hover:border-[var(--accent)]/50 transition">
            <div class="flex flex-wrap justify-between items-start gap-2">
              <div>
                <h4 class="text-sm font-bold text-white">{edu.degree}</h4>
                <p class="text-xs text-[var(--accent)] font-medium">{edu.institution}{loc_suffix}</p>
              </div>
              {year_html}
            </div>
            {details_html}
          </div>
        """)
    edu_section_html = f'''
            <section id="education" class="space-y-6">
              <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
                <i data-lucide="graduation-cap" class="w-5 h-5 text-[var(--accent)]"></i>
                <h2 class="text-lg font-bold text-white">Education & Academic Background</h2>
              </div>
              <div class="space-y-4">{"".join(edu_items)}</div>
            </section>
    ''' if show_edu else ''

    # --- Certifications ---
    raw_certs = getattr(resume, "certifications", []) or []
    show_certs = (
        getattr(resume, "portfolio_show_certifications", True)
        and len(raw_certs) > 0
    )
    cert_items = []
    for cert in raw_certs:
        issuer_html = f'<p class="text-xs text-slate-400">{cert.issuer}</p>' if getattr(cert, "issuer", None) else ''
        year_html = f'<span class="text-[11px] font-mono text-slate-500 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">{cert.year}</span>' if getattr(cert, "year", None) else ''
        url_html = f'<a href="{cert.url}" target="_blank" class="text-xs text-[var(--accent)] hover:underline font-semibold flex items-center gap-1 shrink-0"><i data-lucide="external-link" class="w-3 h-3"></i> Verify</a>' if getattr(cert, "url", None) else ''
        cert_items.append(f"""
          <div class="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 flex items-center justify-between gap-3 hover:border-[var(--accent)]/50 transition">
            <div class="flex items-center gap-3 min-w-0">
              <div class="w-9 h-9 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
                <i data-lucide="award" class="w-4 h-4"></i>
              </div>
              <div class="min-w-0">
                <h4 class="text-xs font-bold text-white truncate">{cert.name}</h4>
                <div class="flex items-center gap-2 pt-0.5">{issuer_html} {year_html}</div>
              </div>
            </div>
            {url_html}
          </div>
        """)
    cert_grid_class = "grid grid-cols-1 sm:grid-cols-2 gap-3" if len(cert_items) >= 2 else "grid grid-cols-1 gap-3"
    cert_section_html = f'''
            <section id="certifications" class="space-y-6">
              <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
                <i data-lucide="award" class="w-5 h-5 text-[var(--accent)]"></i>
                <h2 class="text-lg font-bold text-white">Verified Certifications & Licenses</h2>
              </div>
              <div class="{cert_grid_class}">{"".join(cert_items)}</div>
            </section>
    ''' if show_certs else ''

    # --- Contact Section ---
    contact_cards = []
    if info.email:
        contact_cards.append(f'''
          <a href="mailto:{info.email}" class="p-3.5 bg-slate-900/80 border border-slate-800 rounded-xl flex items-center gap-3 hover:border-[var(--accent)] transition group">
            <div class="w-9 h-9 rounded-lg bg-[var(--accent)]/10 text-[var(--accent)] flex items-center justify-center shrink-0">
              <i data-lucide="mail" class="w-4 h-4"></i>
            </div>
            <div class="min-w-0">
              <span class="text-[10px] text-slate-400 font-bold uppercase block">Email Address</span>
              <span class="text-xs font-bold text-slate-200 group-hover:text-[var(--accent)] transition truncate block">{info.email}</span>
            </div>
          </a>
        ''')
    if info.phone:
        contact_cards.append(f'''
          <a href="tel:{info.phone}" class="p-3.5 bg-slate-900/80 border border-slate-800 rounded-xl flex items-center gap-3 hover:border-emerald-500 transition group">
            <div class="w-9 h-9 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center shrink-0">
              <i data-lucide="phone" class="w-4 h-4"></i>
            </div>
            <div class="min-w-0">
              <span class="text-[10px] text-slate-400 font-bold uppercase block">Phone / WhatsApp</span>
              <span class="text-xs font-bold text-slate-200 group-hover:text-emerald-400 transition truncate block">{info.phone}</span>
            </div>
          </a>
        ''')
    if info.location:
        contact_cards.append(f'''
          <div class="p-3.5 bg-slate-900/80 border border-slate-800 rounded-xl flex items-center gap-3">
            <div class="w-9 h-9 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0">
              <i data-lucide="map-pin" class="w-4 h-4"></i>
            </div>
            <div class="min-w-0">
              <span class="text-[10px] text-slate-400 font-bold uppercase block">Location</span>
              <span class="text-xs font-bold text-slate-200 truncate block">{info.location}</span>
            </div>
          </div>
        ''')

    contact_section_html = f'''
            <section id="contact" class="space-y-4 pt-4 border-t border-slate-800/80 scroll-mt-12">
              <div class="flex items-center gap-2 border-b border-slate-800 pb-3">
                <i data-lucide="send" class="w-5 h-5 text-[var(--accent)]"></i>
                <h2 class="text-lg font-bold text-white">Direct Communication & Collaboration</h2>
              </div>
              <div class="bg-slate-900/50 border border-slate-800 rounded-2xl p-5 sm:p-6 space-y-4">
                <p class="text-xs text-slate-300">Open for new roles, consulting projects, and technical advisory discussions.</p>
                <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {''.join(contact_cards)}
                </div>
                <div class="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800/80">
                  <span class="text-xs text-emerald-400 font-medium flex items-center gap-1.5">
                    <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                    {info.availability_badge or "Available for new inquiries"}
                  </span>
                  <a href="{cta_url}" class="px-4 py-2 bg-[var(--accent)] text-slate-950 font-bold rounded-xl text-xs flex items-center gap-2 hover:brightness-110 transition">
                    <i data-lucide="send" class="w-3.5 h-3.5"></i>
                    <span>{cta_text}</span>
                  </a>
                </div>
              </div>
            </section>
    '''
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
              {f'<a href="#experience" class="hover:text-[var(--accent)] flex items-center gap-2 transition"><i data-lucide="chevron-right" class="w-3 h-3"></i> Career Milestones</a>' if (resume.portfolio_show_experience and getattr(resume, "show_experience", True) and len(resume.work_experience) > 0) else ''}
              {f'<a href="#projects" class="hover:text-[var(--accent)] flex items-center gap-2 transition"><i data-lucide="chevron-right" class="w-3 h-3"></i> Key Projects & Initiatives</a>' if (resume.portfolio_show_projects and getattr(resume, "show_projects", True) and len(resume.projects) > 0) else ''}
              {f'<a href="#skills" class="hover:text-[var(--accent)] flex items-center gap-2 transition"><i data-lucide="chevron-right" class="w-3 h-3"></i> Core Technical Arsenal</a>' if (resume.portfolio_show_skills and getattr(resume, "show_skills", True) and len(resume.skill_categories) > 0) else ''}
              {f'<a href="#education" class="hover:text-[var(--accent)] flex items-center gap-2 transition"><i data-lucide="chevron-right" class="w-3 h-3"></i> Education & Degrees</a>' if show_edu else ''}
              {f'<a href="#certifications" class="hover:text-[var(--accent)] flex items-center gap-2 transition"><i data-lucide="chevron-right" class="w-3 h-3"></i> Verified Certifications</a>' if show_certs else ''}
              <a href="#contact" class="hover:text-[var(--accent)] flex items-center gap-2 transition"><i data-lucide="chevron-right" class="w-3 h-3"></i> Get In Touch & Connect</a>
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

            <!-- Education -->
            {edu_section_html}

            <!-- Certifications -->
            {cert_section_html}

            <!-- Contact -->
            {contact_section_html}

          </div>

        </div>
      </div>
    '''


# ─────────────────────────────────────────────────────────────────────────────
# 3. CYBER TERMINAL CLI TEMPLATE (Hacker / Terminal Developer Aesthetic)
# ─────────────────────────────────────────────────────────────────────────────
