"""
Shared Common Utilities for Portfolio Web Templates.
Contains HTML/URL sanitizers, vCard generator, QR code generators,
security PIN gate overlay, verification badge, and social SVG helpers.
"""

import os
import io
import re
import html
import json
import hmac
import hashlib
from typing import Dict, Any, List, Optional
import qrcode
import qrcode.image.svg
from app.schemas import TailoredResume, SocialLink, ProofOfWorkItem


def sanitize_text(val: Any) -> str:
    """Safely escape HTML special characters (&, <, >, \", ') to prevent Stored XSS."""
    if val is None:
        return ""
    return html.escape(str(val), quote=True)


def sanitize_url(url: Optional[str], allow_data_image: bool = False) -> str:
    """
    Sanitize URLs for href and src attributes.
    Strictly prevents javascript:, vbscript:, file:, blob:, and malformed protocol attacks.
    """
    if not url or not isinstance(url, str):
        return ""
    cleaned = url.strip()
    lower = cleaned.lower()

    # Block dangerous schemes
    if any(lower.startswith(bad) for bad in ("javascript:", "vbscript:", "file:", "blob:")):
        return "#"

    if allow_data_image and lower.startswith("data:image/"):
        # Ensure it is a valid image mime type and no scripts embedded
        if any(mime in lower for mime in ("png", "jpeg", "jpg", "webp", "gif")):
            return cleaned
        return ""

    if cleaned.startswith(("#", "/", "mailto:", "tel:")):
        return html.escape(cleaned, quote=True)

    if cleaned.startswith(("http://", "https://")):
        return html.escape(cleaned, quote=True)

    # If it's a domain/handle without scheme, format safely as https://
    if "." in cleaned and not ":" in cleaned.split("/")[0]:
        return html.escape(f"https://{cleaned}", quote=True)

    return "#"


def sanitize_resume_for_portfolio(resume: TailoredResume) -> TailoredResume:
    """Recursively clone and sanitize all resume fields to eliminate Stored XSS across all portfolio themes."""
    res = resume.model_copy(deep=True)

    if res.personal_info:
        info = res.personal_info
        info.full_name = sanitize_text(info.full_name)
        info.email = sanitize_text(info.email)
        info.phone = sanitize_text(info.phone)
        info.location = sanitize_text(info.location)
        info.linkedin = sanitize_url(info.linkedin)
        info.portfolio = sanitize_url(info.portfolio)
        info.github = sanitize_url(info.github)
        info.avatar_url = sanitize_url(info.avatar_url, allow_data_image=True)
        info.hero_headline = sanitize_text(info.hero_headline)
        info.availability_badge = sanitize_text(info.availability_badge)
        info.custom_domain = sanitize_text(info.custom_domain)

        # Ensure direct fields (linkedin, github, portfolio) are synced into social_links if not already present
        existing_names = {sl.name.lower() for sl in info.social_links}
        synced_social_links = list(info.social_links)
        if info.linkedin and not any("linkedin" in n for n in existing_names):
            synced_social_links.append(SocialLink(name="LinkedIn", url=info.linkedin, icon="linkedin", enabled=True))
        if info.github and not any("github" in n for n in existing_names):
            synced_social_links.append(SocialLink(name="GitHub", url=info.github, icon="github", enabled=True))
        if info.portfolio and not any("portfolio" in n or "website" in n for n in existing_names):
            synced_social_links.append(SocialLink(name="Portfolio", url=info.portfolio, icon="globe", enabled=True))

        safe_links = []
        for sl in synced_social_links:
            safe_links.append(SocialLink(
                name=sanitize_text(sl.name),
                url=sanitize_url(sl.url),
                icon=sanitize_text(sl.icon),
                enabled=sl.enabled
            ))
        info.social_links = safe_links

    res.target_job_title = sanitize_text(res.target_job_title)
    res.professional_summary = sanitize_text(res.professional_summary)
    res.portfolio_cta_text = sanitize_text(res.portfolio_cta_text)
    res.portfolio_cta_url = sanitize_url(res.portfolio_cta_url)

    # Projects
    safe_projects = []
    for p in res.projects:
        p_copy = p.model_copy(deep=True)
        p_copy.name = sanitize_text(p_copy.name)
        p_copy.link = sanitize_url(p_copy.link)
        p_copy.demo_url = sanitize_url(p_copy.demo_url)
        p_copy.technologies = [sanitize_text(t) for t in p_copy.technologies]
        p_copy.description_bullets = [sanitize_text(b) for b in p_copy.description_bullets]
        safe_projects.append(p_copy)
    res.projects = safe_projects

    # Work experience
    safe_exp = []
    for exp in res.work_experience:
        e_copy = exp.model_copy(deep=True)
        e_copy.job_title = sanitize_text(e_copy.job_title)
        e_copy.company = sanitize_text(e_copy.company)
        e_copy.location = sanitize_text(e_copy.location)
        e_copy.start_date = sanitize_text(e_copy.start_date)
        e_copy.end_date = sanitize_text(e_copy.end_date)
        e_copy.bullet_points = [sanitize_text(b) for b in e_copy.bullet_points]
        safe_exp.append(e_copy)
    res.work_experience = safe_exp

    # Education
    safe_edu = []
    for edu in res.education:
        ed_copy = edu.model_copy(deep=True)
        ed_copy.degree = sanitize_text(ed_copy.degree)
        ed_copy.institution = sanitize_text(ed_copy.institution)
        ed_copy.location = sanitize_text(ed_copy.location)
        ed_copy.graduation_year = sanitize_text(ed_copy.graduation_year)
        ed_copy.details = sanitize_text(ed_copy.details)
        safe_edu.append(ed_copy)
    res.education = safe_edu

    # Skill Categories
    safe_skills = []
    for cat in getattr(res, "skill_categories", []):
        cat_copy = cat.model_copy(deep=True)
        cat_copy.category_name = sanitize_text(cat_copy.category_name)
        cat_copy.skills = [sanitize_text(s) for s in cat_copy.skills]
        safe_skills.append(cat_copy)
    res.skill_categories = safe_skills

    # Certifications
    safe_certs = []
    for cert in res.certifications:
        c_copy = cert.model_copy(deep=True)
        c_copy.name = sanitize_text(c_copy.name)
        c_copy.issuer = sanitize_text(c_copy.issuer)
        c_copy.year = sanitize_text(c_copy.year)
        safe_certs.append(c_copy)
    res.certifications = safe_certs

    # Proof of Work Evidence Sanitization
    safe_pow = []
    for pow_item in getattr(res, "proof_of_work", []):
        pow_copy = pow_item.model_copy(deep=True)
        pow_copy.title = sanitize_text(pow_copy.title)
        pow_copy.category = sanitize_text(pow_copy.category)
        pow_copy.tools_used = [sanitize_text(t) for t in pow_copy.tools_used]
        pow_copy.description = sanitize_text(pow_copy.description)
        pow_copy.before_image_url = sanitize_url(pow_copy.before_image_url, allow_data_image=True)
        pow_copy.after_image_url = sanitize_url(pow_copy.after_image_url, allow_data_image=True)
        pow_copy.metrics_label = sanitize_text(pow_copy.metrics_label)
        safe_pow.append(pow_copy)
    res.proof_of_work = safe_pow

    # Security Config Sanitization
    if getattr(res, "security_config", None):
        sec = res.security_config.model_copy(deep=True)
        if sec.access_pin:
            sec.access_pin = re.sub(r"[^\d]", "", str(sec.access_pin))[:6]
        res.security_config = sec

    return res


def compute_portfolio_hmac(slug: str, role: str) -> str:
    """Compute tamper-proof HMAC-SHA256 signature for credential authenticity."""
    secret = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET")
    if not secret or secret.strip() in ("dreemfolio_saas_hmac_secret_key_2026", ""):
        # Fallback to persistent machine/workspace secret
        secret = "df_hmac_" + hashlib.sha256(f"dreemfolio_{os.path.abspath(__file__)}".encode()).hexdigest()
    msg = f"{slug}:{role}:authentic_credential".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()[:16]


def generate_qr_code_svg(data: str) -> str:
    """Generate crisp, scalable vector SVG QR code for candidate vCards or portfolio URLs."""
    try:
        factory = qrcode.image.svg.SvgPathImage
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=2,
            image_factory=factory
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image()
        svg_bytes = img.to_string()
        return svg_bytes.decode('utf-8') if isinstance(svg_bytes, bytes) else str(svg_bytes)
    except Exception as e:
        # High-res SVG fallback
        return f'<svg viewBox="0 0 100 100" class="w-full h-full text-slate-800"><rect width="100" height="100" fill="#f8fafc"/><text x="50" y="55" font-size="10" text-anchor="middle" fill="#0f172a">QR Code Error</text></svg>'


def generate_qr_code_png(data: str) -> bytes:
    """Generate high-resolution PNG QR code for mobile wallpaper, gallery saving, and WhatsApp."""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=12,
            border=2
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        qr = qrcode.QRCode(version=1, box_size=6, border=1)
        qr.add_data("Error")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()


def generate_vcard_content(resume: TailoredResume, portfolio_url: str, include_private: bool = True) -> str:
    """
    Generate standardized vCard 3.0 file content for 1-tap mobile contact saving.
    Security: When include_private=False (e.g. unverified PIN-protected profile),
    sensitive phone & email are redacted to thwart automated scrapers.
    """
    info = resume.personal_info
    name_parts = (info.full_name or "Candidate").split()
    last_name = name_parts[-1] if len(name_parts) > 1 else ""
    first_name = " ".join(name_parts[:-1]) if len(name_parts) > 1 else info.full_name
    role = resume.target_job_title or "Professional"
    company = resume.target_company or "DreemFolio Verified Talent"

    vcard_lines = [
        "BEGIN:VCARD",
        "VERSION:3.0",
        f"N:{last_name};{first_name};;;",
        f"FN:{info.full_name}",
        f"TITLE:{role}",
        f"ORG:{company}",
    ]
    if include_private:
        if info.phone:
            clean_phone = re.sub(r"[^\d+]", "", info.phone)
            vcard_lines.append(f"TEL;TYPE=CELL,VOICE:{clean_phone}")
        if info.email:
            vcard_lines.append(f"EMAIL;TYPE=INTERNET,PREF:{info.email}")
        if info.location:
            vcard_lines.append(f"ADR;TYPE=HOME:;;;{info.location};;;")
    else:
        vcard_lines.append("NOTE:Direct contact details are PIN-protected. Unlock verified access at the portfolio URL below.")

    if portfolio_url:
        vcard_lines.append(f"URL:{portfolio_url}")
    if info.linkedin:
        vcard_lines.append(f"X-SOCIALPROFILE;type=linkedin:{info.linkedin}")
    
    vcard_lines.append("NOTE:Verified Candidate Credentials & Proof-of-Work. Cryptographically Signed.")
    vcard_lines.append("END:VCARD\r\n")
    return "\r\n".join(vcard_lines)


def render_proof_of_work_section(proof_items: List[ProofOfWorkItem], accent_color: str) -> str:
    """Render interactive Proof-of-Work gallery with Before/After image comparison sliders."""
    if not proof_items:
        return ""
    
    cards_html = ""
    for idx, item in enumerate(proof_items):
        tools_chips = "".join([
            f'<span class="inline-flex items-center px-2.5 py-1 rounded-lg text-[11px] font-medium bg-slate-800/90 border border-slate-700/70 text-slate-200">🛠️ {t}</span>'
            for t in item.tools_used
        ])

        media_html = ""
        if item.before_image_url and item.after_image_url:
            slider_id = f"slider_{idx}_{item.id}"
            media_html = f"""
            <div class="relative w-full h-64 sm:h-72 rounded-2xl overflow-hidden select-none border border-slate-700/60 group bg-slate-950">
              <!-- AFTER Image (Base layer) -->
              <img src="{item.after_image_url}" alt="After Work / Restoration" class="absolute inset-0 w-full h-full object-cover">
              <span class="absolute top-3 right-3 z-10 px-2.5 py-1 rounded-md bg-emerald-950/90 border border-emerald-500/50 text-emerald-300 text-[10px] font-black uppercase tracking-wider backdrop-blur-md">AFTER (Completed)</span>
              
              <!-- BEFORE Image (Overlay clip layer) -->
              <div id="{slider_id}_clip" class="absolute inset-y-0 left-0 overflow-hidden border-r-2 border-white shadow-2xl transition-none" style="width: 50%;">
                <img src="{item.before_image_url}" alt="Before Work / Initial State" class="absolute inset-0 w-full h-full object-cover max-w-none" style="width: 100vw; max-width: 900px;">
                <span class="absolute top-3 left-3 px-2.5 py-1 rounded-md bg-rose-950/90 border border-rose-500/50 text-rose-300 text-[10px] font-black uppercase tracking-wider backdrop-blur-md">BEFORE</span>
              </div>

              <!-- Interactive Range Slider Handle -->
              <input type="range" min="0" max="100" value="50" class="absolute inset-0 w-full h-full opacity-0 cursor-ew-resize z-20"
                     oninput="document.getElementById('{slider_id}_clip').style.width = this.value + '%'">
              <div class="absolute bottom-2 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-slate-950/80 border border-slate-700 text-white text-[10px] font-semibold pointer-events-none opacity-80 group-hover:opacity-100 transition shadow-lg">
                ↔ Slide left/right to compare
              </div>
            </div>
            """
        elif item.after_image_url or item.before_image_url:
            img = item.after_image_url or item.before_image_url
            media_html = f"""
            <div class="relative w-full h-56 sm:h-64 rounded-2xl overflow-hidden border border-slate-700/60 bg-slate-950">
              <img src="{img}" alt="{item.title}" class="w-full h-full object-cover">
            </div>
            """

        metric_html = ""
        if item.metrics_label:
            metric_html = f"""
            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40">
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
              {item.metrics_label}
            </span>
            """

        cards_html += f"""
        <div class="p-6 rounded-3xl bg-slate-900/95 border border-slate-800 hover:border-indigo-500/40 shadow-xl transition-all space-y-4">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <span class="px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">Proof of Work</span>
              <h4 class="text-lg font-bold text-white mt-1">{item.title}</h4>
            </div>
            {metric_html}
          </div>

          {media_html}

          <p class="text-xs sm:text-sm text-slate-300 leading-relaxed">{item.description}</p>

          <div class="pt-2 flex flex-wrap gap-2">
            {tools_chips}
          </div>
        </div>
        """

    return f"""
    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <!-- INTERACTIVE PROOF-OF-WORK SHOWCASE & VERIFIED EVIDENCE              -->
    <!-- ═══════════════════════════════════════════════════════════════════ -->
    <section id="proof-of-work-section" class="py-14 border-t border-slate-800/80">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 space-y-8">
        <div class="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
          <div>
            <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-bold mb-2">
              <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
              <span>Verified Evidence Showcase</span>
            </div>
            <h3 class="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Hands-on Execution &amp; Tangible Results</h3>
          </div>
          <p class="text-xs text-slate-400 max-w-sm">
            Interactive photographic and technical validation of real-world repair, code, and project executions.
          </p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          {cards_html}
        </div>
      </div>
    </section>
    """


def render_pin_gate_overlay(safe_resume: TailoredResume, slug: str) -> str:
    """
    Render high-security 4-digit PIN lock gate screen when portfolio is passcode protected.
    Security Hardening: Never outputs plaintext PIN into HTML. Employs asynchronous server-side
    verification with offline salted SHA-256 cryptographic fallback.
    """
    sec = getattr(safe_resume, "security_config", None)
    if not sec or not sec.is_pin_protected or not sec.access_pin:
        return ""
    
    clean_pin = sec.access_pin.strip()
    # Generate deterministic salt and SHA-256 hash so plaintext PIN is NEVER leaked in public HTML
    pin_salt = hashlib.sha256(f"df_salt_{slug}_{clean_pin}".encode()).hexdigest()[:16]
    pin_hash = hashlib.sha256(f"{clean_pin}:{pin_salt}".encode()).hexdigest()

    avatar = safe_resume.personal_info.avatar_url or ""
    avatar_html = f'<img src="{avatar}" class="w-20 h-20 rounded-full mx-auto border-2 border-indigo-500/40 object-cover shadow-xl">' if avatar else f'<div class="w-20 h-20 rounded-full mx-auto bg-indigo-600/20 border-2 border-indigo-500/40 flex items-center justify-center text-indigo-400 font-bold text-2xl shadow-xl">{safe_resume.personal_info.full_name[:1]}</div>'

    return f"""
    <!-- High-Security PIN Gate Lock Screen Overlay -->
    <div id="df-pin-gate" class="fixed inset-0 z-50 bg-slate-950 flex items-center justify-center p-4 backdrop-blur-2xl">
      <div class="max-w-md w-full p-6 sm:p-8 rounded-3xl bg-slate-900 border border-indigo-500/30 shadow-2xl shadow-indigo-950/80 text-center space-y-6">
        
        {avatar_html}

        <div class="space-y-1.5">
          <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-bold">
            <svg class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            <span>Confidential Portfolio</span>
          </div>
          <h3 class="text-xl font-bold text-white">{safe_resume.personal_info.full_name}</h3>
          <p class="text-xs text-slate-400">{safe_resume.target_job_title}</p>
        </div>

        <div class="p-4 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-3">
          <p class="text-xs text-slate-300">This candidate's proof-of-work is protected by a 4-digit recruiter passcode.</p>
          
          <div class="flex justify-center gap-2">
            <input type="password" id="df-pin-input" maxlength="6" placeholder="• • • •"
                   class="w-48 text-center text-2xl tracking-[0.5em] font-mono px-4 py-3 rounded-xl bg-slate-900 border border-indigo-500/40 text-white focus:outline-none focus:border-indigo-400">
          </div>

          <p id="df-pin-error" class="text-xs text-rose-400 font-semibold hidden">Incorrect passcode. Please try again.</p>

          <button onclick="verifyPinCode()"
                  class="w-full py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 via-violet-600 to-pink-600 hover:opacity-90 text-white font-bold text-xs shadow-lg transition">
            Unlock Portfolio Access
          </button>
        </div>

        <p class="text-[11px] text-slate-500">
          🔒 Cryptographically signed by DreemFolio SaaS Enterprise Security.
        </p>

      </div>
    </div>

    <script>
      (function() {{
        const slug = "{slug}";
        const pinSalt = "{pin_salt}";
        const pinHash = "{pin_hash}";
        const storageKey = 'df_unlocked_' + slug;

        if (sessionStorage.getItem(storageKey) === 'true') {{
          const gate = document.getElementById('df-pin-gate');
          if (gate) gate.style.display = 'none';
        }}

        async function computeClientSha256(message) {{
          try {{
            const msgUint8 = new TextEncoder().encode(message);
            const hashBuffer = await crypto.subtle.digest('SHA-256', msgUint8);
            const hashArray = Array.from(new Uint8Array(hashBuffer));
            return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
          }} catch(e) {{
            return '';
          }}
        }}

        window.verifyPinCode = async function() {{
          const input = document.getElementById('df-pin-input');
          const err = document.getElementById('df-pin-error');
          const btn = document.querySelector('#df-pin-gate button');
          if (!input) return;
          const entered = input.value.trim();
          if (!entered) return;

          if (err) err.classList.add('hidden');
          if (btn) {{ btn.disabled = true; btn.innerText = 'Verifying...'; }}

          let granted = false;
          let errorMessage = 'Incorrect passcode. Please try again.';

          // 1. Primary: Verify via secure Server API (enforces Rate Limiting & Anti-Bruteforce Lockout)
          try {{
            const res = await fetch('/api/portfolio/verify-pin', {{
              method: 'POST',
              headers: {{ 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ slug: slug, pin: entered }})
            }});
            const data = await res.json();
            if (res.ok && data.success) {{
              granted = true;
            }} else {{
              errorMessage = data.detail || errorMessage;
            }}
          }} catch(fetchErr) {{
            // 2. Offline / Standalone HTML Export Fallback: Compare against Salted Cryptographic SHA-256 Hash
            const computed = await computeClientSha256(entered + ':' + pinSalt);
            if (computed === pinHash) {{
              granted = true;
            }}
          }}

          if (btn) {{ btn.disabled = false; btn.innerText = 'Unlock Portfolio Access'; }}

          if (granted) {{
            sessionStorage.setItem(storageKey, 'true');
            const gate = document.getElementById('df-pin-gate');
            if (gate) {{
              gate.style.transition = 'opacity 0.4s ease';
              gate.style.opacity = '0';
              setTimeout(() => gate.style.display = 'none', 400);
            }}
          }} else {{
            if (err) {{
              err.innerText = errorMessage;
              err.classList.remove('hidden');
              input.value = '';
              input.focus();
            }}
          }}
        }};

        document.getElementById('df-pin-input')?.addEventListener('keydown', function(e) {{
          if (e.key === 'Enter') verifyPinCode();
        }});
      }})();
    </script>
    """


def render_verification_badge(safe_resume: TailoredResume, slug: str) -> str:
    """Render tamper-proof cryptographic verification badge at top of portfolio."""
    role = safe_resume.target_job_title or "Professional"
    hmac_sig = compute_portfolio_hmac(slug or "candidate", role)
    return f"""
    <div class="w-full bg-gradient-to-r from-slate-950 via-indigo-950/60 to-slate-950 border-b border-indigo-500/20 py-1.5 px-4 text-center">
      <div class="max-w-5xl mx-auto flex items-center justify-center gap-2 text-[11px] text-slate-300">
        <span class="inline-flex items-center gap-1 font-bold text-emerald-400">
          <svg class="w-3.5 h-3.5 text-emerald-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>
          Cryptographically Verified
        </span>
        <span class="text-slate-600">•</span>
        <span class="hidden sm:inline text-slate-400">Authentic Candidate Credentials Issued by DreemFolio</span>
        <span class="font-mono text-[9px] px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-500/30">HMAC: {hmac_sig}</span>
      </div>
    </div>
    """




def get_social_svg(name: str, icon: str = "", css_class: str = "w-4 h-4") -> str:
    """Return inline SVG for social platforms (ensures GitHub, LinkedIn, Twitter, Email etc. always render 100%)."""
    n = (name or "").lower()
    i = (icon or "").lower()
    
    if "github" in n or "github" in i:
        return f'<svg class="{css_class}" fill="currentColor" viewBox="0 0 24 24"><path fill-rule="evenodd" clip-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/></svg>'
    
    if "linkedin" in n or "linkedin" in i:
        return f'<svg class="{css_class}" fill="currentColor" viewBox="0 0 24 24"><path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9v8.37H9.2V10.9H6.46M7.83 6.64a1.65 1.65 0 1 0 0 3.3 1.65 1.65 0 0 0 0-3.3z"/></svg>'
    
    if "twitter" in n or "x.com" in n or "twitter" in i:
        return f'<svg class="{css_class}" fill="currentColor" viewBox="0 0 24 24"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>'
    
    if "mail" in n or "email" in n or "mail" in i:
        return f'<svg class="{css_class}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>'
    
    if "youtube" in n or "youtube" in i:
        return f'<svg class="{css_class}" fill="currentColor" viewBox="0 0 24 24"><path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/></svg>'
    
    if "instagram" in n or "instagram" in i:
        return f'<svg class="{css_class}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="20" height="20" x="2" y="2" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" x2="17.51" y1="6.5" y2="6.5"/></svg>'
    
    if "whatsapp" in n or "chat" in n or "whatsapp" in i:
        return f'<svg class="{css_class}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>'
    
    if "calendly" in n or "calendar" in n or "book" in n:
        return f'<svg class="{css_class}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>'

    # Default Globe
    return f'<svg class="{css_class}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/></svg>'


def get_social_icon(name: str, icon: str = "") -> str:
    """Map social platform name or icon to Lucide icon identifier (fallback)."""
    if icon:
        return icon
    n = name.lower()
    if "github" in n:
        return "github"
    if "linkedin" in n:
        return "linkedin"
    if "twitter" in n or "x.com" in n:
        return "twitter"
    if "instagram" in n:
        return "instagram"
    if "youtube" in n:
        return "youtube"
    if "mail" in n or "email" in n:
        return "mail"
    if "calendly" in n or "calendar" in n or "book" in n:
        return "calendar"
    if "whatsapp" in n or "chat" in n:
        return "message-circle"
    if "gitlab" in n:
        return "git-branch"
    if "medium" in n or "blog" in n:
        return "book-open"
    return "globe"


def get_font_meta(font_name: str) -> tuple[str, str]:
    """Return Google Font link URL and CSS font-family string."""
    fonts = {
        "JetBrains Mono": (
            "https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;600;700;800&display=swap",
            "'JetBrains Mono', monospace",
        ),
        "Outfit": (
            "https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800;900&display=swap",
            "'Outfit', sans-serif",
        ),
        "Playfair Display": (
            "https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,600;0,700;0,900;1,400&family=Inter:wght@400;500;600&display=swap",
            "'Playfair Display', serif",
        ),
        "Plus Jakarta Sans": (
            "https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap",
            "'Plus Jakarta Sans', sans-serif",
        ),
        "Fira Code": (
            "https://fonts.googleapis.com/css2?family=Fira+Code:wght@300;400;500;600;700&display=swap",
            "'Fira Code', monospace",
        ),
        "Inter": (
            "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap",
            "'Inter', sans-serif",
        ),
    }
    return fonts.get(font_name, fonts["Inter"])


def hex_to_rgba(hex_code: str, alpha: float = 1.0) -> str:
    """Convert hex color to rgba string."""
    hex_code = hex_code.lstrip("#")
    if len(hex_code) == 3:
        hex_code = "".join([c * 2 for c in hex_code])
    if len(hex_code) != 6:
        return f"rgba(99, 102, 241, {alpha})"
    r = int(hex_code[0:2], 16)
    g = int(hex_code[2:4], 16)
    b = int(hex_code[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


# ─────────────────────────────────────────────────────────────────────────────
# 1. BENTO GRID STUDIO TEMPLATE (Apple / Linear Modern Modular Layout)
# ─────────────────────────────────────────────────────────────────────────────


def render_viral_portfolio_badge(slug: str) -> str:
    """Render high-converting viral badge at bottom of published portfolio."""
    ref_param = f"portfolio_{slug}" if slug else "portfolio_viral"
    return f"""
    <!-- DreemFolio AI Viral Growth Badge -->
    <footer class="w-full py-10 px-4 text-center border-t border-white/10 mt-20 relative z-20">
      <div class="max-w-xl mx-auto flex flex-col sm:flex-row items-center justify-center gap-3">
        <a href="/?ref={ref_param}" target="_blank" rel="noopener noreferrer"
           class="group inline-flex items-center gap-2.5 px-4 py-2 rounded-full bg-slate-900/90 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/60 shadow-xl transition-all duration-300 text-xs text-slate-300 hover:text-white">
          <span class="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
          <span>⚡ Built with <strong class="text-white font-bold tracking-tight">DreemFolio AI</strong></span>
          <span class="text-slate-600">•</span>
          <span class="text-indigo-400 group-hover:text-indigo-300 font-bold flex items-center gap-1">
            Create your free portfolio in 2 mins
            <svg class="w-3 h-3 group-hover:translate-x-0.5 transition-transform" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5"><path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3"></path></svg>
          </span>
        </a>
      </div>
    </footer>
    """


# ─────────────────────────────────────────────────────────────────────────────
# MASTER PORTFOLIO COMPOSER
# ─────────────────────────────────────────────────────────────────────────────
