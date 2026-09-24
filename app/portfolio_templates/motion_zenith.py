"""
Theme: Motion Zenith (Kinetic Motion Studio)
Features:
- Animated typewriter headline and interactive 3D card tilt
- Dynamic animated skill level meters
- Fluid micro-interactions and contemporary design agency styling
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

    bio_html = f'<p class="text-xs sm:text-sm text-slate-300 leading-relaxed max-w-2xl">{summary}</p>' if resume.portfolio_show_bio else ''

    resume_btn_html = f'''
                <button onclick="window.parent.postMessage('download_resume', '*')"
                  class="px-5 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-semibold text-xs rounded-2xl shadow hover:-translate-y-0.5 transition transform flex items-center gap-2">
                  <i data-lucide="download" class="w-4 h-4 text-[var(--accent)]"></i>
                  <span>Download ATS Resume</span>
                </button>
    ''' if resume.portfolio_show_resume_download else ''

    joined_projects_cards = "".join(project_cards)
    projects_showcase_html = f'''
          <div class="space-y-6">
            <div class="flex items-center justify-between border-b border-slate-800 pb-4">
              <div class="flex items-center gap-2.5 text-xl font-bold text-white">
                <i data-lucide="layers" class="w-5 h-5 text-[var(--accent)] animate-bounce"></i>
                <span>Featured Systems & Deployments</span>
              </div>
              <span class="text-xs font-mono text-slate-400">Interactive 3D Hover</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">{joined_projects_cards}</div>
          </div>
    ''' if resume.portfolio_show_projects else ''

    joined_skill_bars = "".join(skill_bars_html)
    skills_showcase_html = f'''
          <div class="space-y-6">
            <div class="flex items-center gap-2.5 text-xl font-bold text-white border-b border-slate-800 pb-4">
              <i data-lucide="cpu" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Core Technical Stack & Proficiency</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">{joined_skill_bars}</div>
          </div>
    ''' if resume.portfolio_show_skills else ''

    exp_items_list = []
    for e in resume.work_experience:
        bp_text = " ".join([b.lstrip("•- ") for b in e.bullet_points[:2]])
        exp_items_list.append(f'<div class="relative pl-6 border-l-2 border-[var(--accent)] space-y-1.5"><div class="absolute -left-[7px] top-1.5 w-3 h-3 rounded-full bg-[var(--accent)] ring-4 ring-[var(--accent-glow)]"></div><div class="flex flex-wrap justify-between items-center"><h4 class="font-bold text-sm text-white">{e.job_title} · <span class="text-[var(--accent)]">{e.company}</span></h4><span class="text-xs font-mono text-slate-400 bg-slate-950 px-2.5 py-0.5 rounded-full border border-slate-800">{e.start_date} – {e.end_date}</span></div><p class="text-xs text-slate-300 leading-relaxed pt-1">{bp_text}</p></div>')
    joined_exp_items = "".join(exp_items_list)

    exp_showcase_html = f'''
          <div class="bg-slate-900/60 backdrop-blur-xl border border-slate-800/80 rounded-3xl p-8 space-y-6 shadow-xl">
            <div class="flex items-center gap-2.5 text-xl font-bold text-white border-b border-slate-800 pb-4">
              <i data-lucide="briefcase" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Career Trajectory</span>
            </div>
            <div class="space-y-6">
              {joined_exp_items}
            </div>
          </div>
    ''' if resume.portfolio_show_experience else ''

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

              {bio_html}

              <div class="flex flex-wrap items-center justify-center md:justify-start gap-3 pt-2">
                <a href="{cta_url}" class="px-6 py-3 bg-[var(--accent)] hover:brightness-110 text-slate-950 font-extrabold text-xs rounded-2xl shadow-xl shadow-[var(--accent-glow)] hover:-translate-y-0.5 transition transform flex items-center gap-2">
                  <i data-lucide="zap" class="w-4 h-4"></i>
                  <span>{cta_text}</span>
                </a>
                {resume_btn_html}
              </div>

              <div class="pt-2 flex justify-center md:justify-start">{socials_html}</div>
            </div>
          </div>

          <!-- Featured Projects Spotlight (3D Tilt Grid) -->
          {projects_showcase_html}

          <!-- Skills Arsenal (Animated Percentage Bars) -->
          {skills_showcase_html}

          <!-- Experience Milestones -->
          {exp_showcase_html}

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
