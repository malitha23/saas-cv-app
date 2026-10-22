"""
Theme: Galaxy Canvas (Interactive Constellation Particles)
Features:
- Live HTML5 Canvas background with interactive particle physics
- Animated stat counters and glowing neon project cards
- Deep cosmic navy/black theme
"""
import os
import io
import re
import html
import json
from typing import List, Optional, Dict, Any
from app.schemas import TailoredResume
from app.portfolio_templates.common import (
    render_whatsapp_cta_button,
    render_cert_badge_thumb,
    render_personal_kyc_strip,
    render_spoken_languages_block,
    render_references_block,
    sanitize_text, sanitize_url, get_social_svg, get_social_icon, hex_to_rgba
)

def render_galaxy_canvas(resume: TailoredResume, accent: str) -> str:
    info = resume.personal_info
    full_name = info.full_name or "Candidate Name"
    role_title = (resume.target_job_title or "").strip()
    role_html = f'<p class="text-base sm:text-xl font-semibold text-[var(--accent)]">{role_title}</p>' if role_title else ""
    summary = resume.professional_summary or ""
    avatar_url = info.avatar_url or ""
    cta_text = resume.portfolio_cta_text or "Connect with Me"
    wa_hero_btn = render_whatsapp_cta_button(resume, size="hero", label="WhatsApp Connect")
    wa_contact_btn = render_whatsapp_cta_button(resume, size="standard", label="Chat on WhatsApp")
    cta_url = resume.portfolio_cta_url or (
        f"mailto:{info.email}" if info.email else "#contact"
    )

    # Socials
    socials_list = []
    for link in info.social_links:
        if link.enabled and link.url.strip():
            href = (
                link.url
                if link.url.startswith("http") or link.url.startswith("mailto:")
                else f"https://{link.url}"
            )
            icon = get_social_icon(link.name, link.icon)
            socials_list.append(f'''
              <a href="{href}" target="_blank"
                class="p-2 rounded-xl bg-white/5 border border-white/10 text-slate-300 hover:text-white hover:border-[var(--accent)] transition flex items-center gap-1.5 text-xs">
                <i data-lucide="{icon}" class="w-3.5 h-3.5 text-[var(--accent)]"></i>
                <span>{link.name}</span>
              </a>
            ''')
    socials_html = "".join(socials_list)

    # Counts
    num_projects = len(resume.projects)
    num_milestones = len(resume.work_experience)
    num_skills = sum(len(c.skills) for c in resume.skill_categories)

    # Avatar
    if avatar_url:
        avatar_elem = f'<img src="{avatar_url}" alt="{full_name}" class="w-24 h-24 sm:w-28 sm:h-28 rounded-full object-cover ring-4 ring-[var(--accent)] shadow-2xl shadow-[var(--accent-glow)]">'
    else:
        initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "GC"
        avatar_elem = f"""
          <div class="w-24 h-24 rounded-full bg-slate-900 border-2 border-[var(--accent)] shadow-2xl shadow-[var(--accent-glow)] flex items-center justify-center text-white font-extrabold text-2xl">
            <span>{initials}</span>
          </div>
        """

    # Projects
    num_proj = len(resume.projects)
    projects_cards = []
    for idx, p in enumerate(resume.projects):
        tech = " · ".join(p.technologies[:4])
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-300 leading-relaxed">• {b.lstrip("•- ")}</li>'
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

        span_cls = "md:col-span-2" if (num_proj % 2 != 0 and idx == num_proj - 1) else ""
        projects_cards.append(f"""
          <div class="p-6 rounded-3xl bg-slate-900/50 backdrop-blur-xl border border-white/10 hover:border-[var(--accent)] transition duration-300 space-y-3 shadow-xl {span_cls}">
            <div class="flex items-center justify-between">
              <h4 class="font-bold text-base text-white">{p.name}</h4>
              <div class="flex items-center gap-2">{"".join(actions)}</div>
            </div>
            <p class="text-[11px] font-mono text-[var(--accent)]">{tech}</p>
            <ul class="space-y-1">{bullets}</ul>
          </div>
        """)

    bio_html = f'<p class="text-xs sm:text-sm text-slate-300 max-w-2xl mx-auto leading-relaxed">{summary}</p>' if resume.portfolio_show_bio else ''

    resume_btn_html = f'''
              <button onclick="triggerPortfolioCvDownload()"
                class="px-5 py-3 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-semibold text-xs rounded-2xl transition flex items-center gap-2">
                <i data-lucide="download" class="w-4 h-4 text-[var(--accent)]"></i>
                <span>Download ATS CV</span>
              </button>
    ''' if resume.portfolio_show_resume_download else ''

    joined_projects_cards = "".join(projects_cards)
    projects_grid_html = f'''
          <div class="space-y-6 pointer-events-auto">
            <div class="flex items-center gap-2.5 text-xl font-bold text-white">
              <i data-lucide="layers" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Featured Creations & Architectures</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">{joined_projects_cards}</div>
          </div>
    ''' if (resume.portfolio_show_projects and getattr(resume, "show_projects", True) and len(resume.projects) > 0) else ''

    exp_items_list = []
    for e in resume.work_experience:
        bp_text = " ".join([b.lstrip("•- ") for b in e.bullet_points[:2]])
        exp_items_list.append(f'<div class="border-l-2 border-[var(--accent)] pl-4 space-y-1"><div class="flex justify-between items-center"><h4 class="font-bold text-white text-sm">{e.job_title} · <span class="text-[var(--accent)]">{e.company}</span></h4><span class="text-xs text-slate-400 font-mono">{e.start_date} – {e.end_date}</span></div><p class="text-xs text-slate-300 pt-1 leading-relaxed">{bp_text}</p></div>')
    joined_exp_items = "".join(exp_items_list)

    exp_timeline_html = f'''
          <div class="p-8 rounded-3xl bg-slate-900/60 backdrop-blur-2xl border border-white/10 space-y-6 shadow-2xl pointer-events-auto">
            <div class="flex items-center gap-2.5 text-xl font-bold text-white border-b border-white/10 pb-4">
              <i data-lucide="briefcase" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Experience Log</span>
            </div>
            <div class="space-y-6">
              {joined_exp_items}
            </div>
          </div>
    ''' if (resume.portfolio_show_experience and getattr(resume, "show_experience", True) and len(resume.work_experience) > 0 and bool(joined_exp_items)) else ''

    # --- Education Section ---
    show_edu = (
        getattr(resume, "portfolio_show_education", True)
        and getattr(resume, "show_education", True)
        and len(resume.education) > 0
    )
    num_edu = len(resume.education)
    edu_cards = []
    for idx, edu in enumerate(resume.education):
        details_html = f'<p class="text-xs text-slate-300 pt-1 leading-relaxed">{edu.details}</p>' if getattr(edu, "details", None) else ''
        loc_html = f'<span class="text-slate-500">·</span> {edu.location}' if getattr(edu, "location", None) else ''
        year_html = f'<span class="text-xs font-mono text-[var(--accent)] font-semibold">{edu.graduation_year}</span>' if getattr(edu, "graduation_year", None) else ''
        span_cls = "md:col-span-2" if (num_edu % 2 != 0 and idx == num_edu - 1) else ""
        edu_cards.append(f"""
          <div class="p-5 rounded-2xl bg-slate-900/60 border border-white/10 space-y-2 hover:border-[var(--accent)]/50 transition {span_cls}">
            <div class="flex flex-wrap justify-between items-start gap-2">
              <div>
                <h4 class="font-bold text-white text-sm">{edu.degree}</h4>
                <p class="text-xs font-semibold text-[var(--accent)]">{edu.institution} {loc_html}</p>
              </div>
              {year_html}
            </div>
            {details_html}
          </div>
        """)
    edu_grid_class = "grid grid-cols-1 md:grid-cols-2 gap-4" if len(edu_cards) >= 2 else "grid grid-cols-1 gap-4"
    edu_section_html = f'''
          <div class="p-8 rounded-3xl bg-slate-900/60 backdrop-blur-2xl border border-white/10 space-y-6 shadow-2xl pointer-events-auto">
            <div class="flex items-center gap-2.5 text-xl font-bold text-white border-b border-white/10 pb-4">
              <i data-lucide="graduation-cap" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Academic Background & Qualifications</span>
            </div>
            <div class="{edu_grid_class}">
              {''.join(edu_cards)}
            </div>
          </div>
    ''' if show_edu else ''

    # --- Certifications Section ---
    raw_certs = getattr(resume, "certifications", []) or []
    show_certs = (
        getattr(resume, "portfolio_show_certifications", True)
        and len(raw_certs) > 0
    )
    num_certs = len(raw_certs)
    cert_cards = []
    for idx, cert in enumerate(raw_certs):
        issuer_html = f'<p class="text-xs text-slate-400">{cert.issuer}</p>' if getattr(cert, "issuer", None) else ''
        year_html = f'<span class="text-xs font-mono text-slate-400 bg-slate-950 px-2 py-0.5 rounded border border-white/10">{cert.year}</span>' if getattr(cert, "year", None) else ''
        url_html = f'<a href="{cert.url}" target="_blank" class="text-xs text-[var(--accent)] hover:underline font-semibold flex items-center gap-1 shrink-0"><i data-lucide="external-link" class="w-3.5 h-3.5"></i> Verify</a>' if getattr(cert, "url", None) else ''
        span_cls = "md:col-span-2 lg:col-span-3" if (num_certs >= 3 and num_certs % 3 == 1 and idx == num_certs - 1) else ("md:col-span-2" if (num_certs < 3 and num_certs % 2 != 0 and idx == num_certs - 1) else "")
        cert_cards.append(f"""
          <div class="p-4 rounded-2xl bg-slate-900/60 border border-white/10 flex items-center justify-between gap-3 hover:border-[var(--accent)]/50 transition {span_cls}">
            <div class="flex items-center gap-3.5 min-w-0">
              <div class="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center shrink-0">
                <i data-lucide="award" class="w-5 h-5"></i>
              </div>
              <div class="min-w-0">
                <h4 class="font-bold text-sm text-white truncate">{cert.name}</h4>
                <div class="flex items-center gap-2">{issuer_html} {year_html}</div>
              </div>
            </div>
            {url_html}
          </div>
        """)
    cert_grid_class = "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" if len(cert_cards) >= 3 else "grid grid-cols-1 md:grid-cols-2 gap-4"
    cert_section_html = f'''
          <div class="p-8 rounded-3xl bg-slate-900/60 backdrop-blur-2xl border border-white/10 space-y-6 shadow-2xl pointer-events-auto">
            <div class="flex items-center gap-2.5 text-xl font-bold text-white border-b border-white/10 pb-4">
              <i data-lucide="award" class="w-5 h-5 text-[var(--accent)]"></i>
              <span>Verified Credentials & Certifications</span>
            </div>
            <div class="{cert_grid_class}">
              {''.join(cert_cards)}
            </div>
          </div>
    ''' if show_certs else ''

    # --- Contact Section ---
    contact_galaxy_cards = []
    if info.email:
        contact_galaxy_cards.append(f'''
          <a href="mailto:{info.email}" class="p-4 rounded-2xl bg-slate-900/80 border border-white/10 hover:border-[var(--accent)] hover:shadow-[0_0_20px_var(--accent-glow)] transition-all flex items-center gap-3.5 group">
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
        contact_galaxy_cards.append(f'''
          <a href="tel:{info.phone}" class="p-4 rounded-2xl bg-slate-900/80 border border-white/10 hover:border-emerald-400 transition-all flex items-center gap-3.5 group">
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
        contact_galaxy_cards.append(f'''
          <div class="p-4 rounded-2xl bg-slate-900/80 border border-white/10 flex items-center gap-3.5">
            <div class="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center shrink-0">
              <i data-lucide="map-pin" class="w-5 h-5"></i>
            </div>
            <div class="min-w-0">
              <span class="text-[10px] text-slate-400 font-bold uppercase block">Coordinates</span>
              <span class="text-xs font-bold text-slate-300 truncate block">{info.location}</span>
            </div>
          </div>
        ''')

    contact_section_html = f'''
          <div id="contact" class="p-6 sm:p-8 rounded-3xl bg-slate-950/80 backdrop-blur-2xl border border-white/10 space-y-6 scroll-mt-12">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-white/10 pb-4">
              <div class="space-y-1">
                <div class="flex items-center gap-2 text-xl font-black text-white">
                  <i data-lucide="send" class="w-5 h-5 text-[var(--accent)]"></i>
                  <span>Direct Communication Channels</span>
                </div>
                <p class="text-xs text-slate-400">Initiate conversation for engineering appointments and architectural collaborations.</p>
              </div>
              <div class="flex flex-wrap items-center gap-2 shrink-0">
                <a href="{cta_url}" class="px-5 py-2.5 bg-[var(--accent)] text-slate-950 font-bold text-xs rounded-xl shadow-lg shadow-[var(--accent-glow)] hover:brightness-110 transition shrink-0 flex items-center gap-2">
                  <i data-lucide="sparkles" class="w-4 h-4"></i>
                  <span>{cta_text}</span>
                </a>
                {wa_contact_btn}
              </div>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {''.join(contact_galaxy_cards)}
            </div>
            <div class="pt-2 border-t border-white/10 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
              <span class="text-emerald-400 flex items-center gap-1.5">
                <span class="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                {info.availability_badge or "Available for conversations"}
              </span>
              <div class="flex items-center gap-2">{socials_html}</div>
            </div>
          </div>
    '''
    return f"""
      <div class="relative min-h-screen text-slate-100 py-16 px-4 sm:px-8">
        
        <!-- Interactive HTML5 Constellation Canvas -->
        <canvas id="galaxyCanvas" class="fixed inset-0 pointer-events-auto z-0 opacity-70"></canvas>

        <div class="max-w-5xl mx-auto space-y-16 relative z-10 pointer-events-none">
          
          <!-- Hero Section -->
          <div class="p-8 sm:p-12 rounded-3xl bg-slate-900/60 backdrop-blur-2xl border border-white/10 shadow-2xl text-center space-y-6 pointer-events-auto">
            <div class="flex justify-center">{avatar_elem}</div>
            <div class="space-y-2">
              <div class="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
                <span>{info.availability_badge or "Online & Ready"}</span>
              </div>
              <h1 class="text-3xl sm:text-6xl font-black text-white tracking-tight">{full_name}</h1>
              <p class="text-base sm:text-xl font-semibold text-[var(--accent)]">{role_title}</p>
            </div>
            {bio_html}

            <!-- Counting Metrics Animation Cards -->
            <div class="grid grid-cols-3 gap-3 max-w-lg mx-auto pt-2">
              <div class="p-3 bg-black/40 rounded-2xl border border-white/10">
                <span class="counter-num text-2xl sm:text-3xl font-black text-[var(--accent)]" data-target="{num_projects if (resume.portfolio_show_projects and getattr(resume, 'show_projects', True) and num_projects > 0) else (num_skills or 99)}">0</span>
                <span class="text-xl font-black text-[var(--accent)]">{'%' if not (resume.portfolio_show_projects and getattr(resume, 'show_projects', True) and num_projects > 0) and num_skills == 0 else '+'}</span>
                <p class="text-[10px] text-slate-400 font-semibold uppercase">{'Projects' if (resume.portfolio_show_projects and getattr(resume, 'show_projects', True) and num_projects > 0) else ('Core Stack' if num_skills > 0 else 'Precision')}</p>
              </div>
              <div class="p-3 bg-black/40 rounded-2xl border border-white/10">
                <span class="counter-num text-2xl sm:text-3xl font-black text-white" data-target="{num_milestones if num_milestones > 0 else 100}">0</span>
                <span class="text-xl font-black text-white">{'%' if num_milestones == 0 else '+'}</span>
                <p class="text-[10px] text-slate-400 font-semibold uppercase">{'Milestones' if num_milestones > 0 else 'Reliability'}</p>
              </div>
              <div class="p-3 bg-black/40 rounded-2xl border border-white/10">
                <span class="counter-num text-2xl sm:text-3xl font-black text-pink-400" data-target="{num_skills if num_skills > 0 else 10}">0</span>
                <span class="text-xl font-black text-pink-400">+</span>
                <p class="text-[10px] text-slate-400 font-semibold uppercase">Stack Skills</p>
              </div>
            </div>

            <div class="flex flex-wrap justify-center gap-3 pt-2">
              <a href="{cta_url}" class="px-6 py-3 bg-[var(--accent)] hover:brightness-110 text-slate-950 font-extrabold text-xs rounded-2xl shadow-xl shadow-[var(--accent-glow)] transition flex items-center gap-2">
                <i data-lucide="sparkles" class="w-4 h-4"></i>
                <span>{cta_text}</span>
              </a>
              {wa_hero_btn}
              {resume_btn_html}
            </div>
          </div>

          <!-- Featured Projects Grid -->
          {projects_grid_html}

          <!-- Experience Timeline -->
          {exp_timeline_html}

          <!-- Education Section -->
          {edu_section_html}

          <!-- Certifications Section -->
          {cert_section_html}

          <!-- Languages & References -->
          {render_spoken_languages_block(resume, card_bg="bg-slate-900/60", border="border-slate-800")}
          {render_references_block(resume, card_bg="bg-slate-900/60", border="border-slate-800")}
          {render_personal_kyc_strip(resume, card_bg="bg-slate-900/60", border="border-slate-800")}

          <!-- Contact Section -->
          {contact_section_html}

        </div>

      </div>

      <!-- HTML5 Interactive Particle Constellation & Counters Script -->
      <script>
        // 1. Constellation Particle Engine (60fps)
        const canvas = document.getElementById('galaxyCanvas');
        if (canvas) {{
          const ctx = canvas.getContext('2d');
          let width = canvas.width = window.innerWidth;
          let height = canvas.height = window.innerHeight;

          window.addEventListener('resize', () => {{
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
          }});

          const particles = [];
          const count = Math.min(80, Math.floor(width / 18));
          const mouse = {{ x: null, y: null }};

          window.addEventListener('mousemove', e => {{
            mouse.x = e.clientX;
            mouse.y = e.clientY;
          }});
          window.addEventListener('mouseleave', () => {{
            mouse.x = null;
            mouse.y = null;
          }});

          for (let i = 0; i < count; i++) {{
            particles.push({{
              x: Math.random() * width,
              y: Math.random() * height,
              vx: (Math.random() - 0.5) * 0.8,
              vy: (Math.random() - 0.5) * 0.8,
              radius: Math.random() * 2 + 1
            }});
          }}

          function animateCanvas() {{
            ctx.clearRect(0, 0, width, height);

            for (let i = 0; i < particles.length; i++) {{
              const p = particles[i];
              p.x += p.vx;
              p.y += p.vy;
              if (p.x < 0 || p.x > width) p.vx *= -1;
              if (p.y < 0 || p.y > height) p.vy *= -1;

              ctx.beginPath();
              ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
              ctx.fillStyle = '{accent}';
              ctx.globalAlpha = 0.6;
              ctx.fill();

              // Connect nearby particles
              for (let j = i + 1; j < particles.length; j++) {{
                const p2 = particles[j];
                const dx = p.x - p2.x;
                const dy = p.y - p2.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 110) {{
                  ctx.beginPath();
                  ctx.moveTo(p.x, p.y);
                  ctx.lineTo(p2.x, p2.y);
                  ctx.strokeStyle = '{accent}';
                  ctx.globalAlpha = 0.25 * (1 - dist / 110);
                  ctx.stroke();
                }}
              }}

              // Connect to mouse cursor
              if (mouse.x !== null) {{
                const dx = p.x - mouse.x;
                const dy = p.y - mouse.y;
                const dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < 140) {{
                  ctx.beginPath();
                  ctx.moveTo(p.x, p.y);
                  ctx.lineTo(mouse.x, mouse.y);
                  ctx.strokeStyle = '#f43f5e';
                  ctx.globalAlpha = 0.4 * (1 - dist / 140);
                  ctx.stroke();
                }}
              }}
            }}

            requestAnimationFrame(animateCanvas);
          }}
          animateCanvas();
        }}

        // 2. Metric Counters Roll-up Animation
        document.querySelectorAll('.counter-num').forEach(c => {{
          const target = +c.getAttribute('data-target');
          if (!target) return;
          const duration = 1200;
          const step = Math.max(1, Math.floor(target / 30));
          let current = 0;
          const timer = setInterval(() => {{
            current += step;
            if (current >= target) {{
              c.textContent = target;
              clearInterval(timer);
            }} else {{
              c.textContent = current;
            }}
          }}, 35);
        }});
      </script>
    """


# ─────────────────────────────────────────────────────────────────────────────
# 8. AURORA WHITE TEMPLATE (Scandinavian / Minimalist Clean Light Edition)
# ─────────────────────────────────────────────────────────────────────────────
