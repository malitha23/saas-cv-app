"""
Theme: Terminal Dev (Cyber Hacker CLI)
Features:
- Interactive bash / terminal prompt emulator
- Monospace typography and syntax-highlighted badges
- Code snippet styling for experience and project repos
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

def render_terminal_dev(resume: TailoredResume, accent: str) -> str:
    info = resume.personal_info
    full_name = info.full_name or "Candidate"
    role_title = resume.target_job_title or "Software Developer"
    summary = resume.professional_summary or ""
    user_slug = re.sub(r"[^a-zA-Z0-9]", "", full_name.lower().split()[0]) or "dev"

    # Avatar handling
    avatar_url = info.avatar_url or ""
    if avatar_url:
        avatar_elem = f'<img src="{avatar_url}" alt="{full_name}" class="w-24 h-24 rounded-2xl object-cover ring-2 ring-[var(--accent)] shadow-xl">'
    else:
        initials = "".join([p[0] for p in full_name.split()[:2]]).upper() or "DV"
        avatar_elem = f"""
            <div class="w-24 h-24 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-purple-600 p-0.5 shadow-xl">
                <div class="w-full h-full bg-slate-900 rounded-2xl flex items-center justify-center text-2xl font-black text-white">
                    {initials}
                </div>
            </div>
        """

    # Social links with modern styling
    socials = []
    for link in info.social_links:
        if link.enabled and link.url.strip():
            href = (
                link.url
                if link.url.startswith("http") or link.url.startswith("mailto:")
                else f"https://{link.url}"
            )
            svg_icon = get_social_svg(link.name, link.icon, "w-4 h-4 text-slate-400 group-hover:text-[var(--accent)] transition-colors")
            socials.append(f"""
                <a href="{href}" target="_blank" title="{link.name}"
                   class="group p-2.5 rounded-xl bg-slate-800/50 border border-slate-700/50 hover:border-[var(--accent)] hover:bg-slate-800 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-[var(--accent-glow)] flex items-center justify-center">
                    {svg_icon}
                </a>
            """)
    socials_html = "".join(socials)

    # Projects with modern cards
    projects_html = []
    for idx, p in enumerate(resume.projects):
        tech_tags = "".join(
            [
                f'<span class="px-2.5 py-1 text-[10px] font-mono bg-slate-800/60 border border-slate-700/50 text-slate-300 rounded-lg">{t}</span>'
                for t in p.technologies
            ]
        )
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-400 leading-relaxed flex items-start gap-2"><span class="text-[var(--accent)] mt-0.5">▹</span>{b.lstrip("•- ")}</li>'
                for b in p.description_bullets[:3]
            ]
        )

        actions = []
        if p.demo_url:
            actions.append(
                f'<a href="{p.demo_url}" target="_blank" class="px-4 py-2 bg-[var(--accent)] text-slate-950 font-bold rounded-lg text-xs hover:brightness-110 transition-all duration-300 hover:scale-105 flex items-center gap-1.5 shadow-lg shadow-[var(--accent-glow)]"><i data-lucide="external-link" class="w-3.5 h-3.5"></i> Live Demo</a>'
            )
        if p.link:
            actions.append(
                f'<a href="{p.link}" target="_blank" class="px-4 py-2 bg-slate-800/60 border border-slate-700/50 text-slate-200 font-medium rounded-lg text-xs hover:border-[var(--accent)] hover:bg-slate-800 transition-all duration-300 flex items-center gap-1.5"><i data-lucide="github" class="w-3.5 h-3.5"></i> Source</a>'
            )

        projects_html.append(f"""
            <div class="group bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 hover:border-[var(--accent)] rounded-2xl p-6 transition-all duration-500 hover:-translate-y-1 hover:shadow-2xl hover:shadow-[var(--accent-glow)] stagger-item">
                <div class="flex flex-wrap items-start justify-between gap-3 mb-3">
                    <div class="flex items-center gap-3">
                        <span class="text-xs font-mono text-[var(--accent)] font-bold">#{idx+1:02d}</span>
                        <h4 class="text-base font-bold text-white group-hover:text-[var(--accent)] transition-colors">{p.name}</h4>
                    </div>
                    <div class="flex flex-wrap gap-1.5">{tech_tags}</div>
                </div>
                <ul class="space-y-1.5 mb-4">{bullets}</ul>
                <div class="flex flex-wrap gap-2 pt-3 border-t border-slate-800/50">{''.join(actions)}</div>
            </div>
        """)

    # Experience with timeline
    experience_html = []
    for exp in resume.work_experience:
        bullets = "".join(
            [
                f'<li class="text-xs text-slate-400 leading-relaxed flex items-start gap-2"><span class="text-[var(--accent)] mt-0.5">▹</span>{b.lstrip("•- ")}</li>'
                for b in exp.bullet_points[:3]
            ]
        )
        experience_html.append(f"""
            <div class="relative pl-8 pb-8 border-l-2 border-slate-800 last:border-0 stagger-item">
                <div class="absolute -left-[9px] top-1.5 w-4 h-4 rounded-full bg-slate-900 border-2 border-[var(--accent)] shadow-lg shadow-[var(--accent-glow)]"></div>
                <div class="flex flex-wrap items-center justify-between gap-2 mb-1">
                    <div>
                        <h4 class="font-bold text-sm text-white">{exp.job_title}</h4>
                        <span class="text-xs font-semibold text-[var(--accent)]">{exp.company}</span>
                    </div>
                    <span class="text-[10px] font-mono text-slate-500 bg-slate-900/60 px-2.5 py-1 rounded-full border border-slate-800">{exp.start_date} — {exp.end_date}</span>
                </div>
                <ul class="space-y-1 mt-2">{bullets}</ul>
            </div>
        """)

    # Skills with animated progress bars
    skills_html = []
    for cat in resume.skill_categories:
        skill_items = []
        for s in cat.skills[:4]:
            level = cat.skill_levels.get(s, 85)
            skill_items.append(f"""
                <div class="space-y-1">
                    <div class="flex justify-between text-xs">
                        <span class="text-slate-300 font-medium">{s}</span>
                        <span class="text-[var(--accent)] font-mono">{level}%</span>
                    </div>
                    <div class="w-full h-1.5 bg-slate-800/60 rounded-full overflow-hidden">
                        <div class="h-full rounded-full bg-gradient-to-r from-[var(--accent)] to-purple-500 transition-all duration-1000 ease-out skill-bar" style="width: 0%"></div>
                    </div>
                </div>
            """)
        skills_html.append(f"""
            <div class="p-5 bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-xl hover:border-[var(--accent)] transition-all duration-300 stagger-item">
                <h5 class="text-xs font-bold uppercase tracking-wider text-[var(--accent)] mb-3 flex items-center gap-2">
                    <i data-lucide="code-2" class="w-3.5 h-3.5"></i>
                    {cat.category_name}
                </h5>
                <div class="space-y-2.5">{''.join(skill_items)}</div>
            </div>
        """)

    # Education
    education_html = []
    for edu in resume.education:
        education_html.append(f"""
            <div class="flex items-center gap-4 p-4 bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-xl hover:border-[var(--accent)] transition-all duration-300 stagger-item">
                <div class="w-12 h-12 rounded-xl bg-[var(--accent)]/10 border border-[var(--accent)]/20 flex items-center justify-center text-[var(--accent)] text-lg">
                    <i data-lucide="graduation-cap" class="w-5 h-5"></i>
                </div>
                <div class="flex-1">
                    <h5 class="font-bold text-sm text-white">{edu.degree}</h5>
                    <p class="text-xs text-slate-400">{edu.institution}</p>
                </div>
                <span class="text-xs font-mono text-[var(--accent)] font-bold">{edu.graduation_year}</span>
            </div>
        """)

    # Quick metrics (support custom portfolio_metrics or fallback to defaults)
    if resume.portfolio_metrics:
        colors = ["text-[var(--accent)]", "text-white", "text-emerald-400", "text-purple-400", "text-cyan-400"]
        metrics = []
        for i, m in enumerate(resume.portfolio_metrics):
            metrics.append({
                "label": m.get("label", "Metric"),
                "value": m.get("value", "0"),
                "color": colors[i % len(colors)]
            })
    else:
        metrics = [
            {"label": "Projects", "value": f"{len(resume.projects)}+", "color": "text-[var(--accent)]"},
            {"label": "Experience", "value": f"{len(resume.work_experience)}+ Yrs", "color": "text-white"},
            {"label": "Skills", "value": f"{sum(len(c.skills) for c in resume.skill_categories)}+", "color": "text-purple-400"},
            {"label": "System Uptime", "value": "99.98%", "color": "text-emerald-400"}
        ]
    metrics_html = "".join([f"""
        <div class="text-center p-4 bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-xl hover:border-[var(--accent)] transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-[var(--accent-glow)] stagger-item">
            <div class="text-2xl font-black {m['color']}">{m['value']}</div>
            <p class="text-[10px] text-slate-400 uppercase font-semibold tracking-wider">{m['label']}</p>
        </div>
    """ for m in metrics])

    # Interactive quick commands (modern version)
    quick_commands = [
        {"cmd": "bio", "label": "$ cat bio.md"},
        {"cmd": "projects", "label": "$ ls -la projects/"},
        {"cmd": "skills", "label": "$ ./tech-stack"},
        {"cmd": "experience", "label": "$ journalctl --career"},
        {"cmd": "contact", "label": "$ echo $CONTACT"},
    ]
    commands_html = "".join([f"""
        <button onclick="runCommand('{c['cmd']}')" 
                class="px-3.5 py-2 bg-slate-800/60 border border-slate-700/50 hover:border-[var(--accent)] text-slate-300 hover:text-white rounded-lg text-[11px] font-mono transition-all duration-300 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-[var(--accent-glow)]">
            {c['label']}
        </button>
    """ for c in quick_commands])

    # Pre-computed JSON strings to avoid dict hashing syntax errors in f-strings
    projects_json_data = json.dumps([p.name for p in resume.projects])
    skills_json_data = json.dumps([s for cat in resume.skill_categories for s in cat.skills])
    exp_json_data = json.dumps([{"title": e.job_title, "company": e.company} for e in resume.work_experience[:3]])

    bio_html = f'<p class="text-sm text-slate-300 leading-relaxed max-w-2xl">{summary}</p>' if resume.portfolio_show_bio else ''
    cta_target_url = resume.portfolio_cta_url or f"mailto:{info.email}"
    cta_target_text = resume.portfolio_cta_text or "Let's Connect"

    resume_btn_html = f'''
                        <button onclick="window.parent.postMessage('download_resume', '*')"
                                class="px-6 py-3 bg-slate-800/60 border border-slate-700/50 text-slate-200 font-semibold rounded-xl text-sm hover:border-[var(--accent)] hover:bg-slate-800 transition-all duration-300 hover:-translate-y-0.5 flex items-center gap-2">
                            <i data-lucide="download" class="w-4 h-4 text-[var(--accent)]"></i>
                            Download CV
                        </button>
    ''' if resume.portfolio_show_resume_download else ''

    joined_projects_html = "".join(projects_html)
    projects_section_html = f'''
        <section class="mb-12 animate-fade-in-up">
            <div class="flex items-center justify-between border-b border-slate-800/50 pb-4 mb-6">
                <h2 class="text-xl font-bold text-white flex items-center gap-3">
                    <i data-lucide="layers" class="w-5 h-5 text-[var(--accent)]"></i>
                    Featured Projects
                </h2>
                <span class="text-xs text-slate-500 font-mono">{len(resume.projects)} systems</span>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                {joined_projects_html}
            </div>
        </section>
    ''' if resume.portfolio_show_projects else ''

    joined_exp_html = "".join(experience_html)
    exp_section_html = f'''
            <div class="lg:col-span-2 bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-6 animate-fade-in-up">
                <h2 class="text-xl font-bold text-white flex items-center gap-3 border-b border-slate-800/50 pb-4 mb-6">
                    <i data-lucide="briefcase" class="w-5 h-5 text-[var(--accent)]"></i>
                    Career Timeline
                </h2>
                <div class="space-y-2">{joined_exp_html}</div>
            </div>
    ''' if resume.portfolio_show_experience else ''

    joined_skills_html = "".join(skills_html)
    skills_section_html = f'''
            <div class="bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-6 animate-fade-in-up">
                <h2 class="text-xl font-bold text-white flex items-center gap-3 border-b border-slate-800/50 pb-4 mb-6">
                    <i data-lucide="cpu" class="w-5 h-5 text-[var(--accent)]"></i>
                    Tech Stack
                </h2>
                <div class="space-y-4">{joined_skills_html}</div>
            </div>
    ''' if resume.portfolio_show_skills else ''

    joined_edu_html = "".join(education_html)
    edu_section_html = f'''
        <section class="animate-fade-in-up">
            <div class="bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-6">
                <h2 class="text-xl font-bold text-white flex items-center gap-3 border-b border-slate-800/50 pb-4 mb-6">
                    <i data-lucide="graduation-cap" class="w-5 h-5 text-[var(--accent)]"></i>
                    Education
                </h2>
                <div class="space-y-3">{joined_edu_html}</div>
            </div>
        </section>
    ''' if resume.portfolio_show_education else ''

    return f"""
    <div class="max-w-6xl mx-auto px-4 sm:px-6 py-12">
        
        <!-- HERO SECTION -->
        <div class="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-900/90 via-slate-900/50 to-slate-950/90 backdrop-blur-xl border border-slate-800/50 p-8 sm:p-12 mb-12 animate-fade-in-up">
            
            <!-- Ambient glow -->
            <div class="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-[var(--accent)] blur-[120px] opacity-20 pointer-events-none"></div>
            <div class="absolute -bottom-24 -left-24 w-72 h-72 rounded-full bg-purple-600 blur-[120px] opacity-20 pointer-events-none"></div>
            
            <div class="relative flex flex-col md:flex-row items-center gap-8">
                <!-- Avatar -->
                {avatar_elem}
                
                <!-- Info -->
                <div class="flex-1 text-center md:text-left">
                    <div class="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold mb-4">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        <span>{info.availability_badge or "Available for Opportunities"}</span>
                    </div>
                    <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight mb-2">{full_name}</h1>
                    <p class="text-lg sm:text-xl font-semibold text-[var(--accent)] mb-3">{role_title}</p>
                    {bio_html}
                    
                    <!-- Socials -->
                    <div class="flex flex-wrap gap-2 mt-4 justify-center md:justify-start">
                        {socials_html}
                    </div>
                    
                    <!-- CTA -->
                    <div class="flex flex-wrap gap-3 mt-5 justify-center md:justify-start">
                        <a href="{cta_target_url}" 
                           class="px-6 py-3 bg-[var(--accent)] text-slate-950 font-bold rounded-xl text-sm hover:brightness-110 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-2xl hover:shadow-[var(--accent-glow)] flex items-center gap-2">
                            <i data-lucide="sparkles" class="w-4 h-4"></i>
                            {cta_target_text}
                        </a>
                        {resume_btn_html}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- METRICS -->
        <div class="grid grid-cols-3 gap-4 mb-12">
            {metrics_html}
        </div>
        
        <!-- QUICK COMMANDS (subtle interactive bar) -->
        <div class="bg-slate-900/40 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-4 mb-12 flex flex-wrap items-center gap-3 animate-fade-in-up">
            <span class="text-xs font-bold uppercase tracking-wider text-slate-500 mr-2">⚡ Quick</span>
            {commands_html}
            <button onclick="clearTerminal()" 
                    class="px-3.5 py-2 bg-red-500/10 border border-red-500/20 hover:border-red-500 text-red-400 rounded-lg text-[11px] font-mono transition-all duration-300 hover:-translate-y-0.5">
                $ clear
            </button>
        </div>
        
        <!-- TERMINAL OUTPUT (hidden by default, appears when commands run) -->
        <div id="termOutput" class="hidden mb-12 bg-slate-900/60 backdrop-blur-sm border border-slate-800/50 rounded-2xl p-6 space-y-4 font-mono animate-fade-in-up"></div>
        
        <!-- PROJECTS -->
        {projects_section_html}
        
        <!-- EXPERIENCE + SKILLS + EDUCATION GRID -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-12">
            
            <!-- Experience -->
            {exp_section_html}
            
            <!-- Skills -->
            {skills_section_html}
            
        </div>
        
        <!-- EDUCATION -->
        {edu_section_html}
        
    </div>
    
    <!-- JavaScript for Interactions -->
    <script>
        // Terminal command runner (simplified, just shows output)
        function runCommand(cmd) {{
            const output = document.getElementById('termOutput');
            output.classList.remove('hidden');
            const div = document.createElement('div');
            div.className = 'space-y-2 border-l-2 border-[var(--accent)] pl-4 text-xs';
            
            if (cmd === 'bio') {{
                div.innerHTML = `<span class="text-[var(--accent)] font-bold">$ cat bio.md</span><p class="text-slate-300 leading-relaxed">{summary or "No bio available."}</p>`;
            }} else if (cmd === 'projects') {{
                const projects = {projects_json_data};
                div.innerHTML = `<span class="text-[var(--accent)] font-bold">$ ls -la projects/</span><div class="space-y-1 text-slate-300">` + 
                    projects.map((p, i) => `<div class="flex items-center gap-2"><span class="text-[var(--accent)]">▹</span> <span class="font-bold">${{p}}</span> <span class="text-slate-500 text-[10px]">(project_0${{i+1}})</span></div>`).join('') +
                    `</div>`;
            }} else if (cmd === 'skills') {{
                const skills = {skills_json_data};
                div.innerHTML = `<span class="text-[var(--accent)] font-bold">$ ./tech-stack</span><div class="flex flex-wrap gap-1.5">` + 
                    skills.map(s => `<span class="px-2 py-0.5 bg-slate-800/60 border border-slate-700/50 rounded text-slate-300 text-[10px]">${{s}}</span>`).join('') +
                    `</div>`;
            }} else if (cmd === 'experience') {{
                const exp = {exp_json_data};
                div.innerHTML = `<span class="text-[var(--accent)] font-bold">$ journalctl --career</span><div class="space-y-1 text-slate-300">` +
                    exp.map(e => `<div>+ <span class="text-white font-bold">${{e.title}}</span> @ <span class="text-[var(--accent)]">${{e.company}}</span></div>`).join('') +
                    `</div>`;
            }} else if (cmd === 'contact') {{
                div.innerHTML = `<span class="text-[var(--accent)] font-bold">$ echo $CONTACT</span><div class="flex gap-2 pt-1">{socials_html}</div>`;
            }} else {{
                div.innerHTML = `<span class="text-red-400">Command not found: ${{cmd}}. Try: bio, projects, skills, experience, contact</span>`;
            }}
            output.appendChild(div);
            output.scrollTop = output.scrollHeight;
        }}
        
        function clearTerminal() {{
            const output = document.getElementById('termOutput');
            output.innerHTML = '';
            output.classList.add('hidden');
        }}
        
        // Trigger skill bar animations on scroll
        document.addEventListener('DOMContentLoaded', function() {{
            const observer = new IntersectionObserver((entries) => {{
                entries.forEach(entry => {{
                    if (entry.isIntersecting) {{
                        const bars = entry.target.querySelectorAll('.skill-bar');
                        bars.forEach(bar => {{
                            const width = bar.style.width;
                            bar.style.width = '0%';
                            setTimeout(() => {{
                                bar.style.width = width;
                            }}, 100);
                        }});
                    }}
                }});
            }}, {{ threshold: 0.3 }});
            
            document.querySelectorAll('.skill-bar').forEach(bar => {{
                const parent = bar.closest('.space-y-2\\.5') || bar.closest('.space-y-4');
                if (parent) observer.observe(parent);
            }});
        }});
    </script>
    
    <style>
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .animate-fade-in-up {{
            animation: fadeInUp 0.7s ease-out both;
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
        
        /* Smooth transitions */
        * {{
            transition-property: all;
        }}
    </style>
    """


# ─────────────────────────────────────────────────────────────────────────────
# 4. EDITORIAL SWISS TEMPLATE (Awwwards Typographic Luxury Magazine)
# ─────────────────────────────────────────────────────────────────────────────
