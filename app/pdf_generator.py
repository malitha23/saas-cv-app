import io
import os
import ssl
import base64
import socket
import ipaddress
import urllib.request
import urllib.parse
from typing import Optional, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Paragraph, Spacer, HRFlowable, Table, TableStyle, SimpleDocTemplate, KeepTogether, Image as RLImage
)

from app.schemas import TailoredResume


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETON-SAFE STYLE ADDER & HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _add(S, style: ParagraphStyle):
    """Add ParagraphStyle; safely updates singleton stylesheet attributes."""
    try:
        S.add(style)
    except KeyError:
        existing = S[style.name]
        for k, v in style.__dict__.items():
            try:
                setattr(existing, k, v)
            except Exception:
                pass


def _hex_to_rgb(hex_color: str):
    """Convert '#RRGGBB' to (r, g, b) floats 0-1."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return (0.12, 0.23, 0.54)
    return tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))


MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 MB ceiling


def _is_safe_remote_url(url_str: str) -> bool:
    """Verify that a URL does not target localhost, private networks, or cloud metadata services."""
    try:
        parsed = urllib.parse.urlsplit(url_str)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False

        # Block literal localhost names
        if hostname.lower() in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
            return False

        # Resolve IP addresses to protect against DNS rebinding & private IP ranges
        addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        for entry in addr_info:
            sockaddr = entry[4]
            ip_str = sockaddr[0]
            ip_obj = ipaddress.ip_address(ip_str)

            if (
                ip_obj.is_private
                or ip_obj.is_loopback
                or ip_obj.is_link_local
                or ip_obj.is_multicast
                or ip_obj.is_reserved
                or ip_obj.is_unspecified
                # Block AWS/GCP/Azure link-local metadata address (169.254.169.254) explicitly
                or str(ip_obj) == "169.254.169.254"
            ):
                return False
        return True
    except Exception:
        return False


def _load_avatar_image(avatar_url: Optional[str]) -> Optional[io.BytesIO]:
    """Safely load avatar image from Base64 data URL or validated public HTTP/HTTPS endpoints."""
    if not avatar_url or not isinstance(avatar_url, str) or not avatar_url.strip():
        return None
    url = avatar_url.strip()
    try:
        # 1. Base64 data URL (strictly data:image/*)
        if url.startswith("data:image/"):
            parts = url.split(",", 1)
            if len(parts) == 2:
                raw = base64.b64decode(parts[1])
                if len(raw) > MAX_AVATAR_BYTES:
                    print(f"[pdf_generator] Avatar Base64 payload exceeds 5MB limit ({len(raw)} bytes)")
                    return None
                return io.BytesIO(raw)

        # 2. Local file access is strictly blocked to eliminate LFI / arbitrary file disclosure.
        # Any string starting with file://, ../, /, C:\, or existing path is intentionally forbidden.

        # 3. HTTP / HTTPS URL with SSRF protection
        if url.startswith(("http://", "https://")):
            if not _is_safe_remote_url(url):
                print(f"[pdf_generator] SSRF block: rejected suspicious URL: {url}")
                return None

            ctx = ssl.create_default_context()
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "DreemFolio-Avatar-Validator/1.0"}
            )
            with urllib.request.urlopen(req, timeout=3.0, context=ctx) as resp:
                data = resp.read(MAX_AVATAR_BYTES + 1)
                if len(data) > MAX_AVATAR_BYTES:
                    print("[pdf_generator] Remote avatar response exceeded 5MB limit")
                    return None
                return io.BytesIO(data)
    except Exception as e:
        print(f"[pdf_generator] Avatar load warning: {e}")
    return None


def _get_font_names(family: Optional[str]):
    """Return (regular, bold, italic) PostScript font names based on family."""
    fam = (family or "Helvetica").strip()
    if fam == "Times-Roman":
        return ("Times-Roman", "Times-Bold", "Times-Italic")
    elif fam == "Courier":
        return ("Courier", "Courier-Bold", "Courier-Oblique")
    return ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique")


def _draw_diagonal_watermark(canvas, page_w: float, page_h: float, brand_title: str = "DreemFolio AI", subtitle: str = "FREE STARTER TIER • UPGRADE TO PRO"):
    """
    Draw an elegant, semi-transparent diagonal watermark badge centered across the page text.
    Designed with vector geometry and subtle transparency so content remains legible while cleanly branded.
    """
    canvas.saveState()
    try:
        # Move to exact page center and rotate diagonally
        canvas.translate(page_w / 2.0, page_h / 2.0)
        canvas.rotate(32)

        # Subtle alpha for watermark badge background & borders
        if hasattr(canvas, "setFillAlpha"):
            canvas.setFillAlpha(0.07)
        if hasattr(canvas, "setStrokeAlpha"):
            canvas.setStrokeAlpha(0.16)

        # Center pill badge coordinates
        bw = 420
        bh = 126
        bx = -bw / 2.0
        by = -bh / 2.0

        # Background rounded badge with gentle indigo tint
        canvas.setFillColor(colors.HexColor("#EEF2FF"))
        canvas.setStrokeColor(colors.HexColor("#6366F1"))
        canvas.setLineWidth(2.5)
        canvas.roundRect(bx, by, bw, bh, 18, fill=1, stroke=1)

        # Inner decorative dash border
        canvas.setDash(4, 4)
        canvas.setLineWidth(1.0)
        canvas.setStrokeColor(colors.HexColor("#94A3B8"))
        canvas.roundRect(bx + 6, by + 6, bw - 12, bh - 12, 14, fill=0, stroke=1)
        canvas.setDash([], 0)

        # 1. Top Decorative Tag
        if hasattr(canvas, "setFillAlpha"):
            canvas.setFillAlpha(0.18)
        canvas.setFont("Helvetica-Bold", 9.5)
        canvas.setFillColor(colors.HexColor("#4F46E5"))
        canvas.drawCentredString(0, by + bh - 26, "[ OFFICIAL EVALUATION COPY ]")

        # 2. Prominent Brand Name in Center
        if hasattr(canvas, "setFillAlpha"):
            canvas.setFillAlpha(0.13)
        canvas.setFont("Helvetica-Bold", 34)
        canvas.setFillColor(colors.HexColor("#312E81"))
        canvas.drawCentredString(0, by + bh / 2.0 - 9, brand_title)

        # 3. Bottom Upgrade Guidance
        if hasattr(canvas, "setFillAlpha"):
            canvas.setFillAlpha(0.17)
        canvas.setFont("Helvetica-Bold", 9.0)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawCentredString(0, by + 18, subtitle)

    finally:
        canvas.restoreState()


def _draw_sidebar_para(canvas, text: str, style: ParagraphStyle, x: float, y_top: float, max_w: float) -> float:
    """Wrap text inside max_w and draw on canvas. Returns total height consumed."""
    if not text or not text.strip():
        return 0.0
    p = Paragraph(text, style)
    w, h = p.wrap(max_w, 400)
    p.drawOn(canvas, x, y_top - h)
    return h


def _draw_skill_progress_bar(
    canvas,
    skill_name: str,
    level: int,
    x: float,
    y_top: float,
    w: float,
    style: str = "sleek",
    bar_color: colors.Color = colors.HexColor("#2563EB"),
    bg_color: colors.Color = colors.HexColor("#E2E8F0"),
    text_color: colors.Color = colors.HexColor("#0F172A"),
    pct_color: colors.Color = colors.HexColor("#64748B"),
    font_name: str = "Helvetica"
) -> float:
    """
    Draws a skill progress bar cleanly bounded within [y_top - 16.0, y_top].
    - Text baseline: y_top - 7.5 (safely below y_top)
    - Progress bar: y_top - 10.5 down to y_top - 14.0 (3.5pt bar height)
    - Returns exact height consumed: 16.0pt
    """
    pct = max(10, min(100, int(level)))
    slot_h = 16.0

    fn_bold = f"{font_name}-Bold" if "Bold" not in font_name and font_name != "Times-Roman" else ("Times-Bold" if font_name == "Times-Roman" else font_name)
    fn_reg = font_name.replace("-Bold", "")

    # 1. Text sits safely below y_top
    text_y = y_top - 7.5
    canvas.setFont(fn_bold, 7.5)
    canvas.setFillColor(text_color)
    canvas.drawString(x, text_y, skill_name[:24])

    canvas.setFont(fn_reg, 7.0)
    canvas.setFillColor(pct_color)
    canvas.drawRightString(x + w, text_y, f"{pct}%")

    # 2. Bar sits safely below text
    bar_top = y_top - 10.5
    bar_h = 3.5

    if style == "segmented":
        seg_count = 10
        gap = 1.6
        seg_w = (w - (seg_count - 1) * gap) / seg_count
        for s in range(seg_count):
            sx = x + s * (seg_w + gap)
            if (s + 1) * 10 <= pct + 4:
                canvas.setFillColor(bar_color)
            else:
                canvas.setFillColor(bg_color)
            canvas.rect(sx, bar_top - bar_h, seg_w, bar_h, fill=1, stroke=0)
    elif style == "badge":
        canvas.setFillColor(bg_color)
        canvas.roundRect(x, bar_top - bar_h, w, bar_h, 1.5, fill=1, stroke=0)
        canvas.setFillColor(bar_color)
        canvas.roundRect(x, bar_top - bar_h, w * (pct / 100.0), bar_h, 1.5, fill=1, stroke=0)
    else:  # sleek continuous
        canvas.setFillColor(bg_color)
        canvas.roundRect(x, bar_top - bar_h, w, bar_h, 1.8, fill=1, stroke=0)
        canvas.setFillColor(bar_color)
        canvas.roundRect(x, bar_top - bar_h, w * (pct / 100.0), bar_h, 1.8, fill=1, stroke=0)

    return slot_h


def _sync_resume_social_links(resume: TailoredResume):
    if not resume or not resume.personal_info:
        return
    info = resume.personal_info
    if hasattr(info, "social_links") and info.social_links:
        has_linkedin = False
        has_github = False
        has_portfolio = False

        active_linkedin = ""
        active_github = ""
        active_portfolio = ""
        other_active_links = []

        for sl in info.social_links:
            name_l = (sl.name or "").lower().strip()
            url = (sl.url or "").strip()
            if not url or url.startswith("tel:") or url.startswith("mailto:"):
                continue

            if "linkedin" in name_l:
                has_linkedin = True
                if sl.enabled:
                    active_linkedin = url
            elif "github" in name_l:
                has_github = True
                if sl.enabled:
                    active_github = url
            elif "portfolio" in name_l or "website" in name_l or "site" in name_l or "blog" in name_l:
                has_portfolio = True
                if sl.enabled:
                    active_portfolio = url
            elif sl.enabled:
                other_active_links.append(url)

        if has_linkedin:
            info.linkedin = active_linkedin
        if has_github:
            info.github = active_github
        if has_portfolio:
            info.portfolio = active_portfolio
        elif other_active_links and not info.portfolio:
            info.portfolio = other_active_links[0]

# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def generate_resume_pdf(resume: TailoredResume) -> bytes:
    _sync_resume_social_links(resume)
    style = resume.template_style or "classic"
    if style == "visual_sidebar":
        return _visual_sidebar_pdf(resume)
    elif style == "banner_periwinkle":
        return _banner_periwinkle_pdf(resume)
    elif style == "creative_gradient":
        return _creative_gradient_pdf(resume)
    elif style == "emerald_prestige":
        return _emerald_prestige_pdf(resume)
    elif style == "tech_noir":
        return _tech_noir_pdf(resume)
    return _ats_pdf(resume, style)


# ─────────────────────────────────────────────────────────────────────────────
# ATS SINGLE-COLUMN (classic / modern / minimal)
# ─────────────────────────────────────────────────────────────────────────────

def _ats_pdf(resume: TailoredResume, style: str) -> bytes:
    buf = io.BytesIO()
    f_reg, f_bold, f_italic = _get_font_names(getattr(resume, "font_family", "Helvetica"))
    font_scale = getattr(resume, "font_size_scale", "standard") or "standard"

    if font_scale == "compact":
        margin = 26
        body_font_size = 8.5
        body_leading = 11.5
        hdr_font_size = 10.2
        hdr_leading = 13.0
        name_font_size = 16.5
        spacer_gap = 2.0
    elif font_scale == "large":
        margin = 38
        body_font_size = 9.8
        body_leading = 13.6
        hdr_font_size = 11.5
        hdr_leading = 14.5
        name_font_size = 19.0
        spacer_gap = 3.8
    elif font_scale == "spacious":
        margin = 42
        body_font_size = 10.5
        body_leading = 14.5
        hdr_font_size = 12.2
        hdr_leading = 15.5
        name_font_size = 20.0
        spacer_gap = 4.5
    else:  # standard
        margin = 36
        body_font_size = 9.2
        body_leading = 12.8
        hdr_font_size = 11.0
        hdr_leading = 14.0
        name_font_size = 18.0
        spacer_gap = 3.0

    # Color palette
    if resume.custom_accent_color:
        primary = colors.HexColor(resume.custom_accent_color)
        body = colors.HexColor("#0F172A")
        sub = colors.HexColor("#475569")
        div = colors.HexColor("#CBD5E1")
    elif style == "modern":
        primary = colors.HexColor("#1E3A8A")
        body = colors.HexColor("#0F172A")
        sub = colors.HexColor("#475569")
        div = colors.HexColor("#CBD5E1")
    elif style == "minimal":
        primary = colors.HexColor("#18181B")
        body = colors.HexColor("#18181B")
        sub = colors.HexColor("#52525B")
        div = colors.HexColor("#E4E4E7")
    else:  # classic
        primary = colors.HexColor("#111827")
        body = colors.HexColor("#111827")
        sub = colors.HexColor("#4B5563")
        div = colors.HexColor("#9CA3AF")

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin
    )

    S = getSampleStyleSheet()
    _add(S, ParagraphStyle("AtsName", fontName=f_bold, fontSize=name_font_size,
                            leading=name_font_size + 4, alignment=TA_CENTER, textColor=primary, spaceAfter=2))
    _add(S, ParagraphStyle("AtsTitle", fontName=f_bold, fontSize=10.5,
                            leading=14, alignment=TA_CENTER, textColor=primary, spaceAfter=2))
    _add(S, ParagraphStyle("AtsCntct", fontName=f_reg, fontSize=body_font_size,
                            leading=body_leading, alignment=TA_CENTER, textColor=sub, spaceAfter=6))
    _add(S, ParagraphStyle("AtsSecHdr", fontName=f_bold, fontSize=hdr_font_size,
                            leading=hdr_leading, textColor=primary, spaceBefore=6, spaceAfter=2, keepWithNext=True))
    _add(S, ParagraphStyle("AtsJob", fontName=f_bold, fontSize=body_font_size + 0.5,
                            leading=body_leading + 1, textColor=body, keepWithNext=True))
    _add(S, ParagraphStyle("AtsBody", fontName=f_reg, fontSize=body_font_size,
                            leading=body_leading, textColor=body, spaceAfter=2))
    _add(S, ParagraphStyle("AtsBullet", fontName=f_reg, fontSize=body_font_size,
                            leading=body_leading, textColor=body, leftIndent=11, firstLineIndent=-7, spaceAfter=1.8))
    _add(S, ParagraphStyle("AtsSkill", fontName=f_reg, fontSize=body_font_size,
                            leading=body_leading, textColor=body, spaceAfter=2.0))

    # Apply dynamic colors & sizes
    S["AtsName"].fontName = f_bold
    S["AtsName"].fontSize = name_font_size
    S["AtsName"].leading = name_font_size + 4
    S["AtsName"].textColor = primary
    S["AtsTitle"].fontName = f_bold
    S["AtsTitle"].textColor = primary
    S["AtsCntct"].fontName = f_reg
    S["AtsCntct"].textColor = sub
    S["AtsCntct"].fontSize = body_font_size
    S["AtsCntct"].leading = body_leading
    S["AtsSecHdr"].fontName = f_bold
    S["AtsSecHdr"].textColor = primary
    S["AtsSecHdr"].fontSize = hdr_font_size
    S["AtsSecHdr"].leading = hdr_leading
    S["AtsJob"].fontName = f_bold
    S["AtsJob"].textColor = body
    S["AtsJob"].fontSize = body_font_size + 0.5
    S["AtsJob"].leading = body_leading + 1
    S["AtsBody"].fontName = f_reg
    S["AtsBody"].textColor = body
    S["AtsBody"].fontSize = body_font_size
    S["AtsBody"].leading = body_leading
    S["AtsBullet"].fontName = f_reg
    S["AtsBullet"].textColor = body
    S["AtsBullet"].fontSize = body_font_size
    S["AtsBullet"].leading = body_leading
    S["AtsSkill"].fontName = f_reg
    S["AtsSkill"].textColor = body
    S["AtsSkill"].fontSize = body_font_size
    S["AtsSkill"].leading = body_leading

    story = []
    info = resume.personal_info

    story.append(Paragraph(info.full_name.upper(), S["AtsName"]))
    if resume.target_job_title:
        story.append(Paragraph(resume.target_job_title.upper(), S["AtsTitle"]))

    contacts = [p for p in [info.location, info.phone, info.email,
                             info.linkedin, info.github, info.portfolio] if p]
    story.append(Paragraph(" | ".join(contacts), S["AtsCntct"]))
    story.append(HRFlowable(width="100%", thickness=1.5, color=primary, spaceBefore=1, spaceAfter=5))

    order = list(getattr(resume, "section_order", None) or ["summary", "skills", "experience", "projects", "education", "certifications"])
    for sec_name, is_active in [
        ("summary", resume.show_summary and resume.professional_summary),
        ("skills", resume.show_skills and resume.skill_categories),
        ("experience", resume.show_experience and resume.work_experience),
        ("projects", resume.show_projects and resume.projects),
        ("education", resume.show_education and resume.education),
        ("certifications", resume.show_certifications and resume.certifications),
    ]:
        if is_active and sec_name not in order:
            order.append(sec_name)

    arch = (getattr(resume, "role_archetype", "general_professional") or "general_professional").lower()
    skills_hdr = "TECHNICAL SKILLS"
    if arch == "software_engineering":
        skills_hdr = "TECHNICAL SKILLS & TECHNOLOGIES"
    elif arch == "trade_technical":
        skills_hdr = "CORE COMPETENCIES & DIAGNOSTICS"
    elif arch == "management_executive":
        skills_hdr = "LEADERSHIP & CORE COMPETENCIES"
    elif arch == "healthcare_medical":
        skills_hdr = "CLINICAL SKILLS & CORE COMPETENCIES"

    proj_hdr = "KEY PROJECTS"
    if arch == "software_engineering":
        proj_hdr = "KEY PROJECTS & SYSTEMS"
    elif arch == "management_executive":
        proj_hdr = "KEY INITIATIVES & DELIVERABLES"

    edu_hdr = "EDUCATION"
    if arch == "trade_technical":
        edu_hdr = "VOCATIONAL QUALIFICATIONS & EDUCATION"
    elif arch == "healthcare_medical":
        edu_hdr = "MEDICAL ACCREDITATIONS & EDUCATION"

    def add_ats_summary():
        if resume.show_summary and resume.professional_summary:
            sec_flow = [
                Paragraph("PROFESSIONAL SUMMARY", S["AtsSecHdr"]),
                HRFlowable(width="100%", thickness=0.6, color=div, spaceBefore=1, spaceAfter=3),
                Paragraph(resume.professional_summary, S["AtsBody"])
            ]
            story.append(KeepTogether(sec_flow))
            story.append(Spacer(1, spacer_gap))

    def add_ats_skills():
        if resume.show_skills and resume.skill_categories:
            sec_flow = [
                Paragraph(skills_hdr, S["AtsSecHdr"]),
                HRFlowable(width="100%", thickness=0.6, color=div, spaceBefore=1, spaceAfter=3)
            ]
            for cat in resume.skill_categories:
                if cat.skills:
                    sec_flow.append(Paragraph(f"<b>{cat.category_name}:</b> " + ", ".join(cat.skills), S["AtsSkill"]))
            story.append(KeepTogether(sec_flow))
            story.append(Spacer(1, spacer_gap))

    def add_ats_experience():
        if resume.show_experience and resume.work_experience:
            first_exp = resume.work_experience[0]
            loc0 = f" | {first_exp.location}" if first_exp.location else ""
            date0 = f"{first_exp.start_date} – {first_exp.end_date}"
            first_flow = [
                Paragraph("WORK EXPERIENCE", S["AtsSecHdr"]),
                HRFlowable(width="100%", thickness=0.6, color=div, spaceBefore=1, spaceAfter=3),
                Paragraph(f"<b>{first_exp.job_title}</b> – {first_exp.company}{loc0} <font color='#4B5563'>({date0})</font>", S["AtsJob"])
            ]
            if first_exp.bullet_points:
                first_flow.append(Paragraph(f"• {first_exp.bullet_points[0].lstrip('•- ')}", S["AtsBullet"]))
            story.append(KeepTogether(first_flow))
            for b in first_exp.bullet_points[1:]:
                story.append(Paragraph(f"• {b.lstrip('•- ')}", S["AtsBullet"]))
            story.append(Spacer(1, spacer_gap))

            for exp in resume.work_experience[1:]:
                loc = f" | {exp.location}" if exp.location else ""
                date_str = f"{exp.start_date} – {exp.end_date}"
                item_flow = [
                    Paragraph(f"<b>{exp.job_title}</b> – {exp.company}{loc} <font color='#4B5563'>({date_str})</font>", S["AtsJob"])
                ]
                if exp.bullet_points:
                    item_flow.append(Paragraph(f"• {exp.bullet_points[0].lstrip('•- ')}", S["AtsBullet"]))
                story.append(KeepTogether(item_flow))
                for b in exp.bullet_points[1:]:
                    story.append(Paragraph(f"• {b.lstrip('•- ')}", S["AtsBullet"]))
                story.append(Spacer(1, spacer_gap))

    def add_ats_projects():
        if resume.show_projects and resume.projects:
            first_proj = resume.projects[0]
            tech0 = f" <font color='#4B5563'>[{', '.join(first_proj.technologies)}]</font>" if first_proj.technologies else ""
            demo0 = f" | <i>Demo: {first_proj.demo_url}</i>" if getattr(first_proj, "demo_url", None) else ""
            lnk0 = f" | <i>{first_proj.link}</i>" if first_proj.link else ""
            first_flow = [
                Paragraph(proj_hdr, S["AtsSecHdr"]),
                HRFlowable(width="100%", thickness=0.6, color=div, spaceBefore=1, spaceAfter=3),
                Paragraph(f"<b>{first_proj.name}</b>{tech0}{demo0}{lnk0}", S["AtsJob"])
            ]
            if first_proj.description_bullets:
                first_flow.append(Paragraph(f"• {first_proj.description_bullets[0].lstrip('•- ')}", S["AtsBullet"]))
            story.append(KeepTogether(first_flow))
            for b in first_proj.description_bullets[1:]:
                story.append(Paragraph(f"• {b.lstrip('•- ')}", S["AtsBullet"]))
            story.append(Spacer(1, spacer_gap * 0.8))

            for p in resume.projects[1:]:
                tech = f" <font color='#4B5563'>[{', '.join(p.technologies)}]</font>" if p.technologies else ""
                demo = f" | <i>Demo: {p.demo_url}</i>" if getattr(p, "demo_url", None) else ""
                lnk = f" | <i>{p.link}</i>" if p.link else ""
                item_flow = [Paragraph(f"<b>{p.name}</b>{tech}{demo}{lnk}", S["AtsJob"])]
                if p.description_bullets:
                    item_flow.append(Paragraph(f"• {p.description_bullets[0].lstrip('•- ')}", S["AtsBullet"]))
                story.append(KeepTogether(item_flow))
                for b in p.description_bullets[1:]:
                    story.append(Paragraph(f"• {b.lstrip('•- ')}", S["AtsBullet"]))
                story.append(Spacer(1, spacer_gap * 0.8))

    def add_ats_education():
        if resume.show_education and resume.education:
            sec_flow = [
                Paragraph(edu_hdr, S["AtsSecHdr"]),
                HRFlowable(width="100%", thickness=0.6, color=div, spaceBefore=1, spaceAfter=3)
            ]
            for edu in resume.education:
                loc = f" | {edu.location}" if edu.location else ""
                det = f" – {edu.details}" if edu.details else ""
                sec_flow.append(Paragraph(f"<b>{edu.degree}</b> – {edu.institution}{loc} <font color='#4B5563'>({edu.graduation_year})</font>{det}", S["AtsBody"]))
            story.append(KeepTogether(sec_flow))
            story.append(Spacer(1, spacer_gap * 0.8))

    def add_ats_certifications():
        if resume.show_certifications and resume.certifications:
            sec_flow = [
                Paragraph("CERTIFICATIONS & AWARDS", S["AtsSecHdr"]),
                HRFlowable(width="100%", thickness=0.6, color=div, spaceBefore=1, spaceAfter=3)
            ]
            for cert in resume.certifications:
                year_str = f" <font color='#4B5563'>({cert.year})</font>" if cert.year else ""
                sec_flow.append(Paragraph(f"<b>{cert.name}</b> – {cert.issuer}{year_str}", S["AtsBody"]))
            story.append(KeepTogether(sec_flow))
            story.append(Spacer(1, spacer_gap * 0.8))

    for sec in order:
        if sec == "summary":
            add_ats_summary()
        elif sec == "skills":
            add_ats_skills()
        elif sec == "experience":
            add_ats_experience()
        elif sec == "projects":
            add_ats_projects()
        elif sec == "education":
            add_ats_education()
        elif sec == "certifications":
            add_ats_certifications()

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 1. VISUAL SIDEBAR PHOTO (Classic Architectural Left Column)
# ─────────────────────────────────────────────────────────────────────────────

def _visual_sidebar_pdf(resume: TailoredResume) -> bytes:
    """
    Format 1: Left Architectural Column
    - Page 1 Sidebar features Candidate Full Name & Target Job Title at the top!
    - Right Column starts directly with Professional Summary.
    - Deep Slate (#0F172A) + Royal Blue (#2563EB) accents.
    """
    PAGE_W, PAGE_H = letter
    SIDE_W = 185
    SIDE_X = 14
    SIDE_MAX_W = SIDE_W - (SIDE_X * 2)  # 157 pt

    side_bg = colors.HexColor("#0F172A")
    accent = colors.HexColor("#2563EB")
    acc_hex = "#2563EB"
    top_stripe = colors.HexColor("#1D4ED8")

    if resume.custom_accent_color:
        acc_hex = resume.custom_accent_color
        accent = colors.HexColor(acc_hex)
        top_stripe = accent

    f_reg, f_bold, f_italic = _get_font_names(getattr(resume, "font_family", "Helvetica"))
    font_scale = getattr(resume, "font_size_scale", "standard") or "standard"

    if font_scale == "compact":
        body_size, body_leading, sec_size, spacer_h = 8.4, 11.5, 10.2, 3.0
    elif font_scale == "large":
        body_size, body_leading, sec_size, spacer_h = 9.8, 13.8, 11.8, 5.5
    elif font_scale == "spacious":
        body_size, body_leading, sec_size, spacer_h = 10.5, 14.8, 12.5, 6.5
    else:
        body_size, body_leading, sec_size, spacer_h = 9.0, 12.8, 11.0, 4.5

    dark_text = colors.HexColor("#0F172A")
    body_text = colors.HexColor("#1E293B")
    date_text = colors.HexColor("#64748B")

    S = getSampleStyleSheet()
    _add(S, ParagraphStyle("V1SecHdr", fontName=f_bold, fontSize=sec_size, leading=sec_size + 3.0, textColor=accent, spaceBefore=6, spaceAfter=2, keepWithNext=True))
    _add(S, ParagraphStyle("V1Job", fontName=f_bold, fontSize=body_size + 0.8, leading=body_leading + 1, textColor=dark_text, keepWithNext=True))
    _add(S, ParagraphStyle("V1Company", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=colors.HexColor("#334155")))
    _add(S, ParagraphStyle("V1Date", fontName=f_italic, fontSize=8.2, leading=11, textColor=date_text, spaceAfter=1))
    _add(S, ParagraphStyle("V1Body", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=body_text, spaceAfter=2))
    _add(S, ParagraphStyle("V1Bullet", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=body_text, leftIndent=10, firstLineIndent=-7, spaceAfter=1.8))

    _add(S, ParagraphStyle("V1SideName", fontName=f_bold, fontSize=13, leading=16, textColor=colors.white, alignment=TA_CENTER))
    _add(S, ParagraphStyle("V1SideTitle", fontName=f_bold, fontSize=8.8, leading=11.5, textColor=accent, alignment=TA_CENTER))
    _add(S, ParagraphStyle("V1SideSecHdr", fontName=f_bold, fontSize=8, leading=11, textColor=accent, keepWithNext=True))
    _add(S, ParagraphStyle("V1SideLabel", fontName=f_bold, fontSize=6.8, leading=9, textColor=colors.HexColor("#94A3B8")))
    _add(S, ParagraphStyle("V1SideVal", fontName=f_reg, fontSize=7.5, leading=10, textColor=colors.white))
    _add(S, ParagraphStyle("V1SideCat", fontName=f_bold, fontSize=7.2, leading=9.5, textColor=colors.HexColor("#CBD5E1")))
    _add(S, ParagraphStyle("V1SideSkill", fontName=f_reg, fontSize=6.8, leading=9, textColor=colors.HexColor("#E2E8F0")))
    _add(S, ParagraphStyle("V1SideEduDeg", fontName=f_bold, fontSize=7.2, leading=9.5, textColor=colors.white))
    _add(S, ParagraphStyle("V1SideEduSub", fontName=f_reg, fontSize=6.8, leading=9, textColor=colors.HexColor("#94A3B8")))

    rendered_v1_skills = [0]

    def on_first_page(canvas, doc):
        canvas.saveState()
        info = resume.personal_info
        ACC_RGB = _hex_to_rgb(acc_hex)

        canvas.setFillColor(side_bg)
        canvas.rect(0, 0, SIDE_W, PAGE_H, fill=1, stroke=0)
        canvas.setFillColor(top_stripe)
        canvas.rect(SIDE_W, PAGE_H - 4, PAGE_W - SIDE_W, 4, fill=1, stroke=0)
        canvas.setStrokeColor(top_stripe)
        canvas.setLineWidth(1.5)
        canvas.line(SIDE_W, 0, SIDE_W, PAGE_H)

        y = PAGE_H - 24

        # Profile photo
        has_photo = bool(getattr(resume, "show_photo", False) and info.avatar_url and info.avatar_url.strip())
        if has_photo:
            img_bytes = _load_avatar_image(info.avatar_url)
            if img_bytes:
                photo_size = 54
                photo_x = (SIDE_W - photo_size) / 2
                photo_y = y - photo_size
                try:
                    canvas.saveState()
                    p = canvas.beginPath()
                    p.roundRect(photo_x, photo_y, photo_size, photo_size, 6)
                    canvas.clipPath(p, stroke=0)
                    reader = ImageReader(img_bytes)
                    canvas.drawImage(reader, photo_x, photo_y, width=photo_size, height=photo_size, preserveAspectRatio=True)
                    canvas.restoreState()
                    canvas.setStrokeColorRGB(*ACC_RGB)
                    canvas.setLineWidth(1.5)
                    canvas.roundRect(photo_x, photo_y, photo_size, photo_size, 6, stroke=1, fill=0)
                    y = photo_y - 12
                except Exception as e:
                    y -= 4

        # FULL NAME & TARGET TITLE IN LEFT SIDEBAR (Page 1 Only!)
        y -= _draw_sidebar_para(canvas, (info.full_name or "").upper(), S["V1SideName"], SIDE_X, y, SIDE_MAX_W)
        y -= 3
        if resume.target_job_title:
            y -= _draw_sidebar_para(canvas, resume.target_job_title, S["V1SideTitle"], SIDE_X, y, SIDE_MAX_W)
            y -= 6

        canvas.setStrokeColorRGB(0.25, 0.32, 0.45)
        canvas.setLineWidth(0.6)
        canvas.line(SIDE_X, y, SIDE_W - SIDE_X, y)
        y -= 10

        # Contact Details (Page 1 Only!)
        y -= _draw_sidebar_para(canvas, "CONTACT", S["V1SideSecHdr"], SIDE_X, y, SIDE_MAX_W)
        y -= 4
        contacts = []
        if info.email:     contacts.append(("EMAIL", info.email))
        if info.phone:     contacts.append(("PHONE", info.phone))
        if info.location:  contacts.append(("LOCATION", info.location))
        if info.linkedin:  contacts.append(("LINKEDIN", info.linkedin))
        if info.github:    contacts.append(("GITHUB", info.github))
        if info.portfolio: contacts.append(("PORTFOLIO", info.portfolio))

        for lbl, val in contacts:
            if y < 60: break
            y -= _draw_sidebar_para(canvas, lbl, S["V1SideLabel"], SIDE_X, y, SIDE_MAX_W)
            y -= 1
            y -= _draw_sidebar_para(canvas, val, S["V1SideVal"], SIDE_X, y, SIDE_MAX_W)
            y -= 5

        # Technical Skills in Sidebar (Page 1)
        if resume.show_skills and resume.skill_categories and y > 90:
            canvas.setStrokeColorRGB(0.25, 0.32, 0.45)
            canvas.setLineWidth(0.6)
            canvas.line(SIDE_X, y, SIDE_W - SIDE_X, y)
            y -= 8
            y -= _draw_sidebar_para(canvas, "SKILLS & EXPERTISE", S["V1SideSecHdr"], SIDE_X, y, SIDE_MAX_W)
            y -= 4
            show_bars = getattr(resume, "show_skill_bars", True)
            bar_style = getattr(resume, "skill_bar_style", "sleek")
            for cat_idx, cat in enumerate(resume.skill_categories):
                if y < 45: break
                if cat.skills:
                    y -= _draw_sidebar_para(canvas, cat.category_name, S["V1SideCat"], SIDE_X, y, SIDE_MAX_W)
                    y -= 4
                    if show_bars:
                        levels = getattr(cat, "skill_levels", {}) or {}
                        for s in cat.skills[:4]:
                            if y < 35: break
                            s_level = levels.get(s, 85)
                            consumed = _draw_skill_progress_bar(
                                canvas, s, s_level, SIDE_X, y, SIDE_MAX_W,
                                style=bar_style, bar_color=accent, bg_color=colors.HexColor('#334155'),
                                text_color=colors.white, pct_color=colors.HexColor('#94A3B8'), font_name=f_reg
                            )
                            y -= (consumed + 2.0)
                    else:
                        y -= _draw_sidebar_para(canvas, ", ".join(cat.skills), S["V1SideSkill"], SIDE_X, y, SIDE_MAX_W)
                        y -= 4
                    y -= 6
                    rendered_v1_skills[0] = cat_idx + 1

        canvas.setFillColorRGB(0.5, 0.58, 0.70)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(SIDE_W / 2, 14, "Page 1")
        canvas.restoreState()

    def on_later_pages(canvas, doc):
        canvas.saveState()

        canvas.setFillColor(side_bg)
        canvas.rect(0, 0, SIDE_W, PAGE_H, fill=1, stroke=0)
        canvas.setFillColor(top_stripe)
        canvas.rect(SIDE_W, PAGE_H - 4, PAGE_W - SIDE_W, 4, fill=1, stroke=0)
        canvas.setStrokeColor(top_stripe)
        canvas.setLineWidth(1.5)
        canvas.line(SIDE_W, 0, SIDE_W, PAGE_H)

        y = PAGE_H - 28

        # Overflow Technical Skills ONLY (if any categories could not fit on Page 1)
        # Absolutely NO duplicate Name, NO duplicate Title, NO duplicate Contacts!
        cats_overflow = resume.skill_categories[rendered_v1_skills[0]:] if (resume.skill_categories and rendered_v1_skills[0] < len(resume.skill_categories)) else []
        if resume.show_skills and cats_overflow and y > 90:
            y -= _draw_sidebar_para(canvas, "SKILLS & EXPERTISE (CONT.)", S["V1SideSecHdr"], SIDE_X, y, SIDE_MAX_W)
            y -= 4
            show_bars = getattr(resume, "show_skill_bars", True)
            bar_style = getattr(resume, "skill_bar_style", "sleek")
            for cat in cats_overflow:
                if y < 45: break
                if cat.skills:
                    y -= _draw_sidebar_para(canvas, cat.category_name, S["V1SideCat"], SIDE_X, y, SIDE_MAX_W)
                    y -= 4
                    if show_bars:
                        levels = getattr(cat, "skill_levels", {}) or {}
                        for s in cat.skills[:4]:
                            if y < 35: break
                            s_level = levels.get(s, 85)
                            consumed = _draw_skill_progress_bar(
                                canvas, s, s_level, SIDE_X, y, SIDE_MAX_W,
                                style=bar_style, bar_color=accent, bg_color=colors.HexColor('#334155'),
                                text_color=colors.white, pct_color=colors.HexColor('#94A3B8'), font_name=f_reg
                            )
                            y -= (consumed + 2.0)
                    else:
                        y -= _draw_sidebar_para(canvas, ", ".join(cat.skills), S["V1SideSkill"], SIDE_X, y, SIDE_MAX_W)
                        y -= 4
                    y -= 6

        canvas.setFillColorRGB(0.5, 0.58, 0.70)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(SIDE_W / 2, 14, f"Page {doc.page}")

        canvas.setFillColor(colors.HexColor("#94A3B8"))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(PAGE_W - 18, PAGE_H - 18, f"Page {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
        canvas.setLineWidth(0.5)
        canvas.line(SIDE_W + 16, PAGE_H - 22, PAGE_W - 18, PAGE_H - 22)
        canvas.restoreState()

    # Main Body: Starts directly with PROFESSIONAL SUMMARY (Name is in left sidebar!)
    body = []
    raw_order = getattr(resume, "section_order", None) or ["summary", "experience", "projects", "education", "certifications"]
    order = list(raw_order)
    for sec_name, is_active in [
        ("summary", resume.show_summary and resume.professional_summary),
        ("experience", resume.show_experience and resume.work_experience),
        ("projects", resume.show_projects and resume.projects),
        ("education", resume.show_education and resume.education),
        ("certifications", resume.show_certifications and resume.certifications),
    ]:
        if is_active and sec_name not in order:
            order.append(sec_name)

    def add_summary():
        if resume.show_summary and resume.professional_summary:
            sec_flow = [
                Paragraph("PROFESSIONAL SUMMARY", S["V1SecHdr"]),
                HRFlowable(width="100%", thickness=1.4, color=accent, spaceBefore=0, spaceAfter=3),
                Paragraph(resume.professional_summary, S["V1Body"])
            ]
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h))

    def add_experience():
        if resume.show_experience and resume.work_experience:
            first_exp = resume.work_experience[0]
            loc0 = f" · {first_exp.location}" if first_exp.location else ""
            date0 = f"{first_exp.start_date} – {first_exp.end_date}"
            first_flow = [
                Paragraph("WORK EXPERIENCE", S["V1SecHdr"]),
                HRFlowable(width="100%", thickness=1.4, color=accent, spaceBefore=0, spaceAfter=3),
                Paragraph(f"<b>{first_exp.job_title}</b>", S["V1Job"]),
                Paragraph(f"{first_exp.company}{loc0} <font color='#64748B' size='8'>({date0})</font>", S["V1Company"]),
            ]
            if first_exp.bullet_points:
                first_flow.append(Paragraph(f"• {first_exp.bullet_points[0].lstrip('•- ')}", S["V1Bullet"]))
            body.append(KeepTogether(first_flow))
            for b in first_exp.bullet_points[1:]:
                body.append(Paragraph(f"• {b.lstrip('•- ')}", S["V1Bullet"]))
            body.append(Spacer(1, spacer_h * 0.9))

            for exp in resume.work_experience[1:]:
                loc = f" · {exp.location}" if exp.location else ""
                date_str = f"{exp.start_date} – {exp.end_date}"
                item_flow = [
                    Paragraph(f"<b>{exp.job_title}</b>", S["V1Job"]),
                    Paragraph(f"{exp.company}{loc} <font color='#64748B' size='8'>({date_str})</font>", S["V1Company"]),
                ]
                if exp.bullet_points:
                    item_flow.append(Paragraph(f"• {exp.bullet_points[0].lstrip('•- ')}", S["V1Bullet"]))
                body.append(KeepTogether(item_flow))
                for b in exp.bullet_points[1:]:
                    body.append(Paragraph(f"• {b.lstrip('•- ')}", S["V1Bullet"]))
                body.append(Spacer(1, spacer_h * 0.9))

    def add_projects():
        if resume.show_projects and resume.projects:
            first_proj = resume.projects[0]
            tech0 = f" <font color='{acc_hex}'>[{', '.join(first_proj.technologies)}]</font>" if first_proj.technologies else ""
            demo0 = f" | <i>Demo: {first_proj.demo_url}</i>" if getattr(first_proj, "demo_url", None) else ""
            repo0 = f" | <i>Repo: {first_proj.link}</i>" if first_proj.link else ""
            first_flow = [
                Paragraph("KEY PROJECTS", S["V1SecHdr"]),
                HRFlowable(width="100%", thickness=1.4, color=accent, spaceBefore=0, spaceAfter=3),
                Paragraph(f"<b>{first_proj.name}</b>{tech0}{demo0}{repo0}", S["V1Job"])
            ]
            if first_proj.description_bullets:
                first_flow.append(Paragraph(f"• {first_proj.description_bullets[0].lstrip('•- ')}", S["V1Bullet"]))
            body.append(KeepTogether(first_flow))
            for b in first_proj.description_bullets[1:]:
                body.append(Paragraph(f"• {b.lstrip('•- ')}", S["V1Bullet"]))
            body.append(Spacer(1, spacer_h * 0.9))

            for proj in resume.projects[1:]:
                tech = f" <font color='{acc_hex}'>[{', '.join(proj.technologies)}]</font>" if proj.technologies else ""
                demo = f" | <i>Demo: {proj.demo_url}</i>" if getattr(proj, "demo_url", None) else ""
                repo = f" | <i>Repo: {proj.link}</i>" if proj.link else ""
                item_flow = [Paragraph(f"<b>{proj.name}</b>{tech}{demo}{repo}", S["V1Job"])]
                if proj.description_bullets:
                    item_flow.append(Paragraph(f"• {proj.description_bullets[0].lstrip('•- ')}", S["V1Bullet"]))
                body.append(KeepTogether(item_flow))
                for b in proj.description_bullets[1:]:
                    body.append(Paragraph(f"• {b.lstrip('•- ')}", S["V1Bullet"]))
                body.append(Spacer(1, spacer_h * 0.9))

    def add_education():
        if resume.show_education and resume.education:
            sec_flow = [
                Paragraph("EDUCATION", S["V1SecHdr"]),
                HRFlowable(width="100%", thickness=1.4, color=accent, spaceBefore=0, spaceAfter=3),
            ]
            first_edu = resume.education[0]
            loc0 = f" · {first_edu.location}" if first_edu.location else ""
            det0 = f" – {first_edu.details}" if getattr(first_edu, "details", None) else ""
            sec_flow.append(Paragraph(f"<b>{first_edu.degree}</b>", S["V1Job"]))
            sec_flow.append(Paragraph(f"{first_edu.institution}{loc0} <font color='#64748B' size='8'>({first_edu.graduation_year})</font>{det0}", S["V1Company"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h * 0.7))

            for edu in resume.education[1:]:
                loc = f" · {edu.location}" if edu.location else ""
                det = f" – {edu.details}" if getattr(edu, "details", None) else ""
                item_flow = [
                    Paragraph(f"<b>{edu.degree}</b>", S["V1Job"]),
                    Paragraph(f"{edu.institution}{loc} <font color='#64748B' size='8'>({edu.graduation_year})</font>{det}", S["V1Company"]),
                ]
                body.append(KeepTogether(item_flow))
                body.append(Spacer(1, spacer_h * 0.7))

    def add_certifications():
        if resume.show_certifications and resume.certifications:
            sec_flow = [
                Paragraph("CERTIFICATIONS & LICENSES", S["V1SecHdr"]),
                HRFlowable(width="100%", thickness=1.4, color=accent, spaceBefore=0, spaceAfter=3),
            ]
            first_cert = resume.certifications[0]
            year0 = f" <font color='#64748B' size='8'>({first_cert.year})</font>" if first_cert.year else ""
            sec_flow.append(Paragraph(f"• <b>{first_cert.name}</b> — {first_cert.issuer}{year0}", S["V1Job"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h * 0.6))

            for cert in resume.certifications[1:]:
                year_str = f" <font color='#64748B' size='8'>({cert.year})</font>" if cert.year else ""
                item_flow = [Paragraph(f"• <b>{cert.name}</b> — {cert.issuer}{year_str}", S["V1Job"])]
                body.append(KeepTogether(item_flow))
                body.append(Spacer(1, spacer_h * 0.6))

    for sec in order:
        if sec == "summary":
            add_summary()
        elif sec == "experience":
            add_experience()
        elif sec == "projects":
            add_projects()
        elif sec == "education":
            add_education()
        elif sec == "certifications":
            add_certifications()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=SIDE_W + 16, rightMargin=18, topMargin=28, bottomMargin=20)
    doc.build(body, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 2. BANNER PERIWINKLE (Matches Candidate's Uploaded CV Format)
# ─────────────────────────────────────────────────────────────────────────────

def _banner_periwinkle_pdf(resume: TailoredResume) -> bytes:
    """Format 2: Soft Periwinkle top banner with circular photo on right and 2-column layout."""
    PAGE_W, PAGE_H = letter
    BANNER_H = 92
    banner_color = colors.HexColor("#9FB5D6")
    if resume.custom_accent_color:
        banner_color = colors.HexColor(resume.custom_accent_color)

    dark_text = colors.HexColor("#0F172A")
    body_text = colors.HexColor("#1E293B")
    sub_text = colors.HexColor("#475569")

    f_reg, f_bold, f_italic = _get_font_names(getattr(resume, "font_family", "Helvetica"))
    font_scale = getattr(resume, "font_size_scale", "standard") or "standard"

    if font_scale == "compact":
        body_size, body_leading, sec_size, spacer_h = 8.4, 11.5, 10.5, 3.0
    elif font_scale == "large":
        body_size, body_leading, sec_size, spacer_h = 9.8, 13.8, 11.8, 5.5
    elif font_scale == "spacious":
        body_size, body_leading, sec_size, spacer_h = 10.5, 14.8, 12.5, 6.5
    else:
        body_size, body_leading, sec_size, spacer_h = 9.0, 12.8, 11.0, 4.5

    S = getSampleStyleSheet()
    _add(S, ParagraphStyle("PwSecHdr", fontName=f_bold, fontSize=sec_size, leading=sec_size + 3.0, textColor=dark_text, spaceBefore=6, spaceAfter=2, keepWithNext=True))
    _add(S, ParagraphStyle("PwJob", fontName=f_bold, fontSize=body_size + 0.8, leading=body_leading + 1, textColor=dark_text, keepWithNext=True))
    _add(S, ParagraphStyle("PwCompany", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=sub_text))
    _add(S, ParagraphStyle("PwBody", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=body_text, spaceAfter=2))
    _add(S, ParagraphStyle("PwBullet", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=body_text, leftIndent=10, firstLineIndent=-7, spaceAfter=1.8))
    _add(S, ParagraphStyle("PwSideSecHdr", fontName=f_bold, fontSize=9.5, leading=12, textColor=dark_text, keepWithNext=True))
    _add(S, ParagraphStyle("PwSideLabel", fontName=f_bold, fontSize=7.2, leading=9.5, textColor=sub_text))
    _add(S, ParagraphStyle("PwSideVal", fontName=f_reg, fontSize=7.8, leading=10.5, textColor=dark_text))
    _add(S, ParagraphStyle("PwSideEduDeg", fontName=f_bold, fontSize=7.8, leading=10.5, textColor=dark_text))
    _add(S, ParagraphStyle("PwSideEduSub", fontName=f_reg, fontSize=7.2, leading=9.5, textColor=sub_text))
    _add(S, ParagraphStyle("PwSideSkill", fontName=f_reg, fontSize=7.5, leading=10, textColor=body_text))

    SIDE_X = 24
    SIDE_MAX_W = 155

    rendered_pw_skills = [0]

    def on_first_page(canvas, doc):
        canvas.saveState()
        info = resume.personal_info

        canvas.setFillColor(banner_color)
        canvas.rect(0, PAGE_H - BANNER_H, PAGE_W, BANNER_H, fill=1, stroke=0)

        canvas.setFillColor(dark_text)
        canvas.setFont(f_bold, 22)
        canvas.drawString(28, PAGE_H - 46, (info.full_name or "MALITHA SAYURANGA"))

        canvas.setFont(f_reg, 12)
        canvas.setFillColor(colors.HexColor("#1E293B"))
        if resume.target_job_title:
            canvas.drawString(28, PAGE_H - 68, resume.target_job_title)

        has_photo = bool(getattr(resume, "show_photo", False) and info.avatar_url and info.avatar_url.strip())
        if has_photo:
            img_bytes = _load_avatar_image(info.avatar_url)
            if img_bytes:
                cx, cy, r = PAGE_W - 58, PAGE_H - 46, 30
                try:
                    canvas.saveState()
                    p = canvas.beginPath()
                    p.circle(cx, cy, r)
                    canvas.clipPath(p, stroke=0)
                    reader = ImageReader(img_bytes)
                    canvas.drawImage(reader, cx - r, cy - r, width=2*r, height=2*r, preserveAspectRatio=True)
                    canvas.restoreState()
                    canvas.setStrokeColor(colors.white)
                    canvas.setLineWidth(2.5)
                    canvas.circle(cx, cy, r, stroke=1, fill=0)
                except Exception as e:
                    pass

        y = PAGE_H - BANNER_H - 18
        y -= _draw_sidebar_para(canvas, "CONTACT", S["PwSideSecHdr"], SIDE_X, y, SIDE_MAX_W)
        y -= 4
        contacts = []
        if info.email:     contacts.append(("EMAIL", info.email))
        if info.phone:     contacts.append(("PHONE", info.phone))
        if info.location:  contacts.append(("LOCATION", info.location))
        if info.linkedin:  contacts.append(("LINKEDIN", info.linkedin))
        if info.github:    contacts.append(("GITHUB", info.github))
        if info.portfolio: contacts.append(("PORTFOLIO", info.portfolio))

        for lbl, val in contacts:
            if y < 80: break
            y -= _draw_sidebar_para(canvas, lbl, S["PwSideLabel"], SIDE_X, y, SIDE_MAX_W)
            y -= 1
            y -= _draw_sidebar_para(canvas, val, S["PwSideVal"], SIDE_X, y, SIDE_MAX_W)
            y -= 4

        # Technical Skills in Sidebar (Page 1)
        if resume.show_skills and resume.skill_categories and y > 80:
            canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
            canvas.setLineWidth(0.6)
            canvas.line(SIDE_X, y, SIDE_X + SIDE_MAX_W, y)
            y -= 10
            y -= _draw_sidebar_para(canvas, "SKILLS", S["PwSideSecHdr"], SIDE_X, y, SIDE_MAX_W)
            y -= 4
            show_bars = getattr(resume, "show_skill_bars", True)
            bar_style = getattr(resume, "skill_bar_style", "segmented")
            for cat_idx, cat in enumerate(resume.skill_categories):
                if y < 45: break
                if cat.skills:
                    y -= _draw_sidebar_para(canvas, cat.category_name, S["PwSideLabel"], SIDE_X, y, SIDE_MAX_W)
                    y -= 4
                    if show_bars:
                        levels = getattr(cat, "skill_levels", {}) or {}
                        for s in cat.skills[:4]:
                            if y < 35: break
                            s_level = levels.get(s, 85)
                            consumed = _draw_skill_progress_bar(
                                canvas, s, s_level, SIDE_X, y, SIDE_MAX_W,
                                style=bar_style,
                                bar_color=colors.HexColor("#1E3A8A"),
                                bg_color=colors.HexColor("#E2E8F0"),
                                text_color=dark_text,
                                pct_color=sub_text,
                                font_name=f_reg
                            )
                            y -= (consumed + 2.0)
                    else:
                        y -= _draw_sidebar_para(canvas, ", ".join(cat.skills), S["PwSideSkill"], SIDE_X, y, SIDE_MAX_W)
                        y -= 4
                    y -= 6
                    rendered_pw_skills[0] = cat_idx + 1

        canvas.setFillColor(colors.HexColor("#94A3B8"))
        canvas.setFont(f_reg, 7)
        canvas.drawString(SIDE_X, 14, "Page 1")
        canvas.restoreState()

    def on_later_pages(canvas, doc):
        canvas.saveState()

        canvas.setFillColor(banner_color)
        canvas.rect(0, PAGE_H - 6, PAGE_W, 6, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.setFont(f_reg, 8)
        canvas.drawRightString(PAGE_W - 24, PAGE_H - 20, f"Page {doc.page}")

        y = PAGE_H - 30

        # Overflow Technical Skills ONLY (if any categories could not fit on Page 1)
        # Absolutely NO duplicate Candidate Name, NO duplicate Job Title, NO duplicate Contacts, NO duplicate Links!
        cats_overflow = resume.skill_categories[rendered_pw_skills[0]:] if (resume.skill_categories and rendered_pw_skills[0] < len(resume.skill_categories)) else []
        if resume.show_skills and cats_overflow and y > 90:
            show_bars = getattr(resume, "show_skill_bars", True)
            bar_style = getattr(resume, "skill_bar_style", "segmented")
            y -= _draw_sidebar_para(canvas, "SKILLS (CONT.)", S["PwSideSecHdr"], SIDE_X, y, SIDE_MAX_W)
            y -= 5
            for cat in cats_overflow:
                if y < 45: break
                if cat.skills:
                    y -= _draw_sidebar_para(canvas, cat.category_name, S["PwSideLabel"], SIDE_X, y, SIDE_MAX_W)
                    y -= 4
                    if show_bars:
                        levels = getattr(cat, "skill_levels", {}) or {}
                        for s in cat.skills[:4]:
                            if y < 35: break
                            s_level = levels.get(s, 85)
                            consumed = _draw_skill_progress_bar(
                                canvas, s, s_level, SIDE_X, y, SIDE_MAX_W,
                                style=bar_style,
                                bar_color=colors.HexColor("#1E3A8A"),
                                bg_color=colors.HexColor("#E2E8F0"),
                                text_color=dark_text,
                                pct_color=sub_text,
                                font_name=f_reg
                            )
                            y -= (consumed + 2.0)
                    else:
                        y -= _draw_sidebar_para(canvas, ", ".join(cat.skills), S["PwSideSkill"], SIDE_X, y, SIDE_MAX_W)
                        y -= 4
                    y -= 6

        canvas.setFillColor(colors.HexColor("#94A3B8"))
        canvas.setFont(f_reg, 7)
        canvas.drawString(SIDE_X, 14, f"Page {doc.page}")
        canvas.restoreState()

    body = []
    body.append(Spacer(1, BANNER_H - 12))
    raw_order = getattr(resume, "section_order", None) or ["summary", "experience", "projects", "education", "certifications"]
    order = list(raw_order)
    for sec_name, is_active in [
        ("summary", resume.show_summary and resume.professional_summary),
        ("experience", resume.show_experience and resume.work_experience),
        ("projects", resume.show_projects and resume.projects),
        ("education", resume.show_education and resume.education),
        ("certifications", resume.show_certifications and resume.certifications),
    ]:
        if is_active and sec_name not in order:
            order.append(sec_name)

    def add_pw_summary():
        if resume.show_summary and resume.professional_summary:
            sec_flow = [
                Paragraph("OBJECTIVE", S["PwSecHdr"]),
                HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#CBD5E1"), spaceBefore=0, spaceAfter=4),
                Paragraph(resume.professional_summary, S["PwBody"])
            ]
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h))

    def add_pw_experience():
        if resume.show_experience and resume.work_experience:
            first_exp = resume.work_experience[0]
            loc0 = f", {first_exp.location}" if first_exp.location else ""
            date0 = f"{first_exp.start_date} - {first_exp.end_date}"
            first_flow = [
                Paragraph("WORK EXPERIENCE", S["PwSecHdr"]),
                HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#CBD5E1"), spaceBefore=0, spaceAfter=4),
                Paragraph(f"<b>{first_exp.job_title}</b>, {first_exp.company}{loc0}", S["PwJob"]),
                Paragraph(f"<font color='#64748B' size='8'>{date0}</font>", S["PwCompany"])
            ]
            if first_exp.bullet_points:
                first_flow.append(Paragraph(f"• {first_exp.bullet_points[0].lstrip('•- ')}", S["PwBullet"]))
            body.append(KeepTogether(first_flow))
            for b in first_exp.bullet_points[1:]:
                body.append(Paragraph(f"• {b.lstrip('•- ')}", S["PwBullet"]))
            body.append(Spacer(1, spacer_h * 0.9))

            for exp in resume.work_experience[1:]:
                loc = f", {exp.location}" if exp.location else ""
                date_str = f"{exp.start_date} - {exp.end_date}"
                item_flow = [
                    Paragraph(f"<b>{exp.job_title}</b>, {exp.company}{loc}", S["PwJob"]),
                    Paragraph(f"<font color='#64748B' size='8'>{date_str}</font>", S["PwCompany"])
                ]
                if exp.bullet_points:
                    item_flow.append(Paragraph(f"• {exp.bullet_points[0].lstrip('•- ')}", S["PwBullet"]))
                body.append(KeepTogether(item_flow))
                for b in exp.bullet_points[1:]:
                    body.append(Paragraph(f"• {b.lstrip('•- ')}", S["PwBullet"]))
                body.append(Spacer(1, spacer_h * 0.9))

    def add_pw_projects():
        if resume.show_projects and resume.projects:
            first_proj = resume.projects[0]
            tech0 = f" <font color='#475569'>[{', '.join(first_proj.technologies)}]</font>" if first_proj.technologies else ""
            demo0 = f" | <i>Demo: {first_proj.demo_url}</i>" if getattr(first_proj, "demo_url", None) else ""
            repo0 = f" | <i>Repo: {first_proj.link}</i>" if first_proj.link else ""
            first_flow = [
                Paragraph("PROJECTS AND MY WORKS", S["PwSecHdr"]),
                HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#CBD5E1"), spaceBefore=0, spaceAfter=4),
                Paragraph(f"<b>{first_proj.name}</b>{tech0}{demo0}{repo0}", S["PwJob"])
            ]
            if first_proj.description_bullets:
                first_flow.append(Paragraph(f"• {first_proj.description_bullets[0].lstrip('•- ')}", S["PwBullet"]))
            body.append(KeepTogether(first_flow))
            for b in first_proj.description_bullets[1:]:
                body.append(Paragraph(f"• {b.lstrip('•- ')}", S["PwBullet"]))
            body.append(Spacer(1, spacer_h * 0.9))

            for proj in resume.projects[1:]:
                tech = f" <font color='#475569'>[{', '.join(proj.technologies)}]</font>" if proj.technologies else ""
                demo = f" | <i>Demo: {proj.demo_url}</i>" if getattr(proj, "demo_url", None) else ""
                repo = f" | <i>Repo: {proj.link}</i>" if proj.link else ""
                item_flow = [Paragraph(f"<b>{proj.name}</b>{tech}{demo}{repo}", S["PwJob"])]
                if proj.description_bullets:
                    item_flow.append(Paragraph(f"• {proj.description_bullets[0].lstrip('•- ')}", S["PwBullet"]))
                body.append(KeepTogether(item_flow))
                for b in proj.description_bullets[1:]:
                    body.append(Paragraph(f"• {b.lstrip('•- ')}", S["PwBullet"]))
                body.append(Spacer(1, spacer_h * 0.9))

    def add_pw_education():
        if resume.show_education and resume.education:
            sec_flow = [
                Paragraph("EDUCATION", S["PwSecHdr"]),
                HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#CBD5E1"), spaceBefore=0, spaceAfter=4),
            ]
            first_edu = resume.education[0]
            loc0 = f", {first_edu.location}" if first_edu.location else ""
            det0 = f" – {first_edu.details}" if getattr(first_edu, "details", None) else ""
            sec_flow.append(Paragraph(f"<b>{first_edu.degree}</b>, {first_edu.institution}{loc0}", S["PwJob"]))
            sec_flow.append(Paragraph(f"<font color='#64748B' size='8'>{first_edu.graduation_year}{det0}</font>", S["PwCompany"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h * 0.7))

            for edu in resume.education[1:]:
                loc = f", {edu.location}" if edu.location else ""
                det = f" – {edu.details}" if getattr(edu, "details", None) else ""
                item_flow = [
                    Paragraph(f"<b>{edu.degree}</b>, {edu.institution}{loc}", S["PwJob"]),
                    Paragraph(f"<font color='#64748B' size='8'>{edu.graduation_year}{det}</font>", S["PwCompany"]),
                ]
                body.append(KeepTogether(item_flow))
                body.append(Spacer(1, spacer_h * 0.7))

    def add_pw_certifications():
        if resume.show_certifications and resume.certifications:
            sec_flow = [
                Paragraph("CERTIFICATIONS & CREDENTIALS", S["PwSecHdr"]),
                HRFlowable(width="100%", thickness=1.0, color=colors.HexColor("#CBD5E1"), spaceBefore=0, spaceAfter=4),
            ]
            first_cert = resume.certifications[0]
            year0 = f" <font color='#64748B' size='8'>({first_cert.year})</font>" if first_cert.year else ""
            sec_flow.append(Paragraph(f"• <b>{first_cert.name}</b> — {first_cert.issuer}{year0}", S["PwJob"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h * 0.6))

            for cert in resume.certifications[1:]:
                year_str = f" <font color='#64748B' size='8'>({cert.year})</font>" if cert.year else ""
                item_flow = [Paragraph(f"• <b>{cert.name}</b> — {cert.issuer}{year_str}", S["PwJob"])]
                body.append(KeepTogether(item_flow))
                body.append(Spacer(1, spacer_h * 0.6))

    for sec in order:
        if sec == "summary":
            add_pw_summary()
        elif sec == "experience":
            add_pw_experience()
        elif sec == "projects":
            add_pw_projects()
        elif sec == "education":
            add_pw_education()
        elif sec == "certifications":
            add_pw_certifications()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=195, rightMargin=24, topMargin=24, bottomMargin=20)
    doc.build(body, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 3. CREATIVE GRADIENT (Indigo Full-Width Header + Horizontal Ribbon + Timeline)
# ─────────────────────────────────────────────────────────────────────────────

def _creative_gradient_pdf(resume: TailoredResume) -> bytes:
    """
    Format 3: Full-Width Indigo Header + Horizontal Ribbon + Clean Asymmetric Body.
    - Deep Indigo #1E1B4B to #312E81 top header banner with candidate name and title.
    - Full-width horizontal Contact Ribbon (#EEF2FF) below the banner.
    - Clean asymmetric layout below ribbon.
    """
    PAGE_W, PAGE_H = letter
    BANNER_H = 78
    RIBBON_H = 22

    f_reg, f_bold, f_italic = _get_font_names(getattr(resume, "font_family", "Helvetica"))
    font_scale = getattr(resume, "font_size_scale", "standard") or "standard"

    if font_scale == "compact":
        body_size, body_leading, sec_size, spacer_h = 8.4, 11.5, 10.5, 3.0
    elif font_scale == "large":
        body_size, body_leading, sec_size, spacer_h = 9.8, 13.8, 11.8, 5.5
    elif font_scale == "spacious":
        body_size, body_leading, sec_size, spacer_h = 10.5, 14.8, 12.5, 6.5
    else:
        body_size, body_leading, sec_size, spacer_h = 9.0, 12.8, 11.0, 4.5

    dark_indigo = colors.HexColor("#1E1B4B")
    violet_accent = colors.HexColor("#6366F1")
    if resume.custom_accent_color:
        violet_accent = colors.HexColor(resume.custom_accent_color)
        dark_indigo = colors.HexColor(resume.custom_accent_color)

    dark_text = colors.HexColor("#0F172A")
    body_text = colors.HexColor("#1E293B")

    S = getSampleStyleSheet()
    _add(S, ParagraphStyle("CgSecHdr", fontName=f_bold, fontSize=sec_size, leading=sec_size + 3.0, textColor=violet_accent, spaceBefore=6, spaceAfter=2, keepWithNext=True))
    _add(S, ParagraphStyle("CgJob", fontName=f_bold, fontSize=body_size + 0.8, leading=body_leading + 1, textColor=dark_text, keepWithNext=True))
    _add(S, ParagraphStyle("CgCompany", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=colors.HexColor("#475569")))
    _add(S, ParagraphStyle("CgBody", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=body_text, spaceAfter=2))
    _add(S, ParagraphStyle("CgBullet", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=body_text, leftIndent=10, firstLineIndent=-7, spaceAfter=1.8))
    _add(S, ParagraphStyle("CgSkillCat", fontName=f_bold, fontSize=body_size, leading=body_leading, textColor=dark_indigo))

    def on_first_page(canvas, doc):
        canvas.saveState()
        info = resume.personal_info

        # 1. Deep Indigo Banner
        canvas.setFillColor(dark_indigo)
        canvas.rect(0, PAGE_H - BANNER_H, PAGE_W, BANNER_H, fill=1, stroke=0)

        # 2. Candidate Name & Target Title
        canvas.setFillColor(colors.white)
        canvas.setFont(f_bold, 22)
        canvas.drawString(32, PAGE_H - 38, (info.full_name or "").upper())

        canvas.setFont(f_bold, 11)
        canvas.setFillColor(colors.HexColor("#A5B4FC") if not resume.custom_accent_color else colors.white)
        if resume.target_job_title:
            canvas.drawString(32, PAGE_H - 56, resume.target_job_title.upper())

        # Photo on right side if enabled
        has_photo = bool(getattr(resume, "show_photo", False) and info.avatar_url and info.avatar_url.strip())
        if has_photo:
            img_bytes = _load_avatar_image(info.avatar_url)
            if img_bytes:
                photo_size = 50
                px, py = PAGE_W - 74, PAGE_H - BANNER_H + 14
                try:
                    canvas.saveState()
                    p = canvas.beginPath()
                    p.roundRect(px, py, photo_size, photo_size, 8)
                    canvas.clipPath(p, stroke=0)
                    reader = ImageReader(img_bytes)
                    canvas.drawImage(reader, px, py, width=photo_size, height=photo_size, preserveAspectRatio=True)
                    canvas.restoreState()
                    canvas.setStrokeColor(violet_accent)
                    canvas.setLineWidth(2)
                    canvas.roundRect(px, py, photo_size, photo_size, 8, stroke=1, fill=0)
                except Exception:
                    pass

        # 3. Horizontal Contact Ribbon
        ribbon_y = PAGE_H - BANNER_H - RIBBON_H
        canvas.setFillColor(colors.HexColor("#EEF2FF"))
        canvas.rect(0, ribbon_y, PAGE_W, RIBBON_H, fill=1, stroke=0)
        canvas.setStrokeColor(violet_accent)
        canvas.setLineWidth(0.8)
        canvas.line(0, ribbon_y, PAGE_W, ribbon_y)

        # Ribbon contacts
        contact_items = [p for p in [info.email, info.phone, info.location, info.linkedin, info.github] if p]
        ribbon_text = "   •   ".join(contact_items)
        canvas.setFillColor(colors.HexColor("#312E81"))
        canvas.setFont(f_bold, 7.8)
        canvas.drawString(32, ribbon_y + 7, ribbon_text[:125])

        canvas.restoreState()

    def on_later_pages(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(violet_accent)
        canvas.rect(0, PAGE_H - 5, PAGE_W, 5, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.setFont(f_reg, 8)
        canvas.drawRightString(PAGE_W - 32, PAGE_H - 18, f"Page {doc.page}")
        canvas.restoreState()

    body = []
    body.append(Spacer(1, BANNER_H + RIBBON_H - 8))
    order = getattr(resume, "section_order", None) or ["summary", "skills", "experience", "projects", "education", "certifications"]

    def add_cg_summary():
        if resume.show_summary and resume.professional_summary:
            sec_flow = [
                Paragraph("EXECUTIVE PROFILE", S["CgSecHdr"]),
                HRFlowable(width="100%", thickness=1.5, color=violet_accent, spaceBefore=0, spaceAfter=4),
                Paragraph(resume.professional_summary, S["CgBody"])
            ]
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h))

    def add_cg_skills():
        if resume.show_skills and resume.skill_categories:
            sec_flow = [
                Paragraph("CORE SKILLS & TECH STACK", S["CgSecHdr"]),
                HRFlowable(width="100%", thickness=1.5, color=violet_accent, spaceBefore=0, spaceAfter=4)
            ]
            for cat in resume.skill_categories:
                if cat.skills:
                    sec_flow.append(Paragraph(f"<b>{cat.category_name}:</b> " + ", ".join(cat.skills), S["CgBody"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h))

    def add_cg_experience():
        if resume.show_experience and resume.work_experience:
            first_exp = resume.work_experience[0]
            loc0 = f" · {first_exp.location}" if first_exp.location else ""
            date0 = f"{first_exp.start_date} – {first_exp.end_date}"
            first_flow = [
                Paragraph("PROFESSIONAL EXPERIENCE", S["CgSecHdr"]),
                HRFlowable(width="100%", thickness=1.5, color=violet_accent, spaceBefore=0, spaceAfter=4),
                Paragraph(f"<b>{first_exp.job_title}</b> — <font color='{violet_accent.hexval()}'>{first_exp.company}</font>{loc0}", S["CgJob"]),
                Paragraph(f"<font color='#64748B' size='8'>({date0})</font>", S["CgCompany"])
            ]
            if first_exp.bullet_points:
                first_flow.append(Paragraph(f"• {first_exp.bullet_points[0].lstrip('•- ')}", S["CgBullet"]))
            body.append(KeepTogether(first_flow))
            for b in first_exp.bullet_points[1:]:
                body.append(Paragraph(f"• {b.lstrip('•- ')}", S["CgBullet"]))
            body.append(Spacer(1, spacer_h * 0.9))

            for exp in resume.work_experience[1:]:
                loc = f" · {exp.location}" if exp.location else ""
                date_str = f"{exp.start_date} – {exp.end_date}"
                item_flow = [
                    Paragraph(f"<b>{exp.job_title}</b> — <font color='{violet_accent.hexval()}'>{exp.company}</font>{loc}", S["CgJob"]),
                    Paragraph(f"<font color='#64748B' size='8'>({date_str})</font>", S["CgCompany"])
                ]
                if exp.bullet_points:
                    item_flow.append(Paragraph(f"• {exp.bullet_points[0].lstrip('•- ')}", S["CgBullet"]))
                body.append(KeepTogether(item_flow))
                for b in exp.bullet_points[1:]:
                    body.append(Paragraph(f"• {b.lstrip('•- ')}", S["CgBullet"]))
                body.append(Spacer(1, spacer_h * 0.9))

    def add_cg_projects():
        if resume.show_projects and resume.projects:
            first_proj = resume.projects[0]
            tech0 = f" <font color='{violet_accent.hexval()}'>[{', '.join(first_proj.technologies)}]</font>" if first_proj.technologies else ""
            demo0 = f" | <i>Demo: {first_proj.demo_url}</i>" if getattr(first_proj, "demo_url", None) else ""
            repo0 = f" | <i>Repo: {first_proj.link}</i>" if first_proj.link else ""
            first_flow = [
                Paragraph("FEATURED PROJECTS", S["CgSecHdr"]),
                HRFlowable(width="100%", thickness=1.5, color=violet_accent, spaceBefore=0, spaceAfter=4),
                Paragraph(f"<b>{first_proj.name}</b>{tech0}{demo0}{repo0}", S["CgJob"])
            ]
            if first_proj.description_bullets:
                first_flow.append(Paragraph(f"• {first_proj.description_bullets[0].lstrip('•- ')}", S["CgBullet"]))
            body.append(KeepTogether(first_flow))
            for b in first_proj.description_bullets[1:]:
                body.append(Paragraph(f"• {b.lstrip('•- ')}", S["CgBullet"]))
            body.append(Spacer(1, spacer_h * 0.9))

            for proj in resume.projects[1:]:
                tech = f" <font color='{violet_accent.hexval()}'>[{', '.join(proj.technologies)}]</font>" if proj.technologies else ""
                demo = f" | <i>Demo: {proj.demo_url}</i>" if getattr(proj, "demo_url", None) else ""
                repo = f" | <i>Repo: {proj.link}</i>" if proj.link else ""
                item_flow = [Paragraph(f"<b>{proj.name}</b>{tech}{demo}{repo}", S["CgJob"])]
                if proj.description_bullets:
                    item_flow.append(Paragraph(f"• {proj.description_bullets[0].lstrip('•- ')}", S["CgBullet"]))
                body.append(KeepTogether(item_flow))
                for b in proj.description_bullets[1:]:
                    body.append(Paragraph(f"• {b.lstrip('•- ')}", S["CgBullet"]))
                body.append(Spacer(1, spacer_h * 0.9))

    def add_cg_education():
        if resume.show_education and resume.education:
            sec_flow = [
                Paragraph("EDUCATION & CREDENTIALS", S["CgSecHdr"]),
                HRFlowable(width="100%", thickness=1.5, color=violet_accent, spaceBefore=0, spaceAfter=4)
            ]
            for edu in resume.education:
                loc = f" · {edu.location}" if edu.location else ""
                det = f" – {edu.details}" if edu.details else ""
                sec_flow.append(Paragraph(f"<b>{edu.degree}</b> — {edu.institution}{loc} <font color='#64748B'>({edu.graduation_year})</font>{det}", S["CgBody"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h * 0.8))

    def add_cg_certifications():
        if resume.show_certifications and resume.certifications:
            sec_flow = [
                Paragraph("CERTIFICATIONS & LICENSES", S["CgSecHdr"]),
                HRFlowable(width="100%", thickness=1.5, color=violet_accent, spaceBefore=0, spaceAfter=4)
            ]
            for cert in resume.certifications:
                year_str = f" <font color='#64748B'>({cert.year})</font>" if cert.year else ""
                sec_flow.append(Paragraph(f"• <b>{cert.name}</b> — {cert.issuer}{year_str}", S["CgBody"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h * 0.8))

    raw_order = getattr(resume, "section_order", None) or ["summary", "skills", "experience", "projects", "education", "certifications"]
    order = list(raw_order)
    for sec_name, is_active in [
        ("summary", resume.show_summary and resume.professional_summary),
        ("skills", resume.show_skills and resume.skill_categories),
        ("experience", resume.show_experience and resume.work_experience),
        ("projects", resume.show_projects and resume.projects),
        ("education", resume.show_education and resume.education),
        ("certifications", resume.show_certifications and resume.certifications),
    ]:
        if is_active and sec_name not in order:
            order.append(sec_name)

    for sec in order:
        if sec == "summary":
            add_cg_summary()
        elif sec == "skills":
            add_cg_skills()
        elif sec == "experience":
            add_cg_experience()
        elif sec == "projects":
            add_cg_projects()
        elif sec == "education":
            add_cg_education()
        elif sec == "certifications":
            add_cg_certifications()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=32, rightMargin=32, topMargin=24, bottomMargin=22)
    doc.build(body, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 4. EMERALD PRESTIGE (Luxury Nordic Executive Layout)
# ─────────────────────────────────────────────────────────────────────────────

def _emerald_prestige_pdf(resume: TailoredResume) -> bytes:
    """
    Format 4: Luxury Nordic Executive Format.
    - Deep Forest Emerald (#064E3B) & Mint Teal (#10B981) palette.
    - Top executive header card with badge.
    - Numbered section blocks: '■ 01. EXECUTIVE SUMMARY', '■ 02. EXPERIENCE'.
    """
    PAGE_W, PAGE_H = letter
    CARD_H = 88

    f_reg, f_bold, f_italic = _get_font_names(getattr(resume, "font_family", "Helvetica"))
    font_scale = getattr(resume, "font_size_scale", "standard") or "standard"

    if font_scale == "compact":
        body_size, body_leading, sec_size, spacer_h = 8.4, 11.5, 10.2, 3.0
    elif font_scale == "large":
        body_size, body_leading, sec_size, spacer_h = 9.8, 13.8, 11.8, 5.5
    elif font_scale == "spacious":
        body_size, body_leading, sec_size, spacer_h = 10.5, 14.8, 12.5, 6.5
    else:
        body_size, body_leading, sec_size, spacer_h = 9.0, 12.8, 11.0, 4.5

    emerald_dark = colors.HexColor("#064E3B")
    mint_accent = colors.HexColor("#10B981")
    if resume.custom_accent_color:
        mint_accent = colors.HexColor(resume.custom_accent_color)
        emerald_dark = colors.HexColor(resume.custom_accent_color)

    dark_text = colors.HexColor("#0F172A")
    body_text = colors.HexColor("#1E293B")

    S = getSampleStyleSheet()
    _add(S, ParagraphStyle("EmSecHdr", fontName=f_bold, fontSize=sec_size, leading=sec_size + 3.0, textColor=emerald_dark, spaceBefore=6, spaceAfter=2, keepWithNext=True))
    _add(S, ParagraphStyle("EmJob", fontName=f_bold, fontSize=body_size + 0.8, leading=body_leading + 1, textColor=dark_text, keepWithNext=True))
    _add(S, ParagraphStyle("EmCompany", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=colors.HexColor("#047857")))
    _add(S, ParagraphStyle("EmBody", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=body_text, spaceAfter=2))
    _add(S, ParagraphStyle("EmBullet", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=body_text, leftIndent=10, firstLineIndent=-7, spaceAfter=1.8))

    def on_first_page(canvas, doc):
        canvas.saveState()
        info = resume.personal_info

        # Top Executive Header Card
        canvas.setFillColor(emerald_dark)
        canvas.rect(0, PAGE_H - CARD_H, PAGE_W, CARD_H, fill=1, stroke=0)
        canvas.setFillColor(mint_accent)
        canvas.rect(0, PAGE_H - 4, PAGE_W, 4, fill=1, stroke=0)

        # Name
        canvas.setFillColor(colors.white)
        canvas.setFont(f_bold, 21)
        canvas.drawString(32, PAGE_H - 36, (info.full_name or "").upper())

        # Pill badge for headline
        if resume.target_job_title:
            badge_text = f"[  {resume.target_job_title.upper()}  ]"
            canvas.setFont(f_bold, 9)
            canvas.setFillColor(colors.HexColor("#A7F3D0") if not resume.custom_accent_color else colors.white)
            canvas.drawString(32, PAGE_H - 52, badge_text)

        # Contact strip on dark card
        contacts = [p for p in [info.email, info.phone, info.location, info.linkedin] if p]
        canvas.setFont(f_reg, 7.8)
        canvas.setFillColor(colors.HexColor("#D1FAE5") if not resume.custom_accent_color else colors.white)
        canvas.drawString(32, PAGE_H - 72, "  |  ".join(contacts)[:130])

        # Photo if enabled
        has_photo = bool(getattr(resume, "show_photo", False) and info.avatar_url and info.avatar_url.strip())
        if has_photo:
            img_bytes = _load_avatar_image(info.avatar_url)
            if img_bytes:
                photo_size = 54
                px, py = PAGE_W - 78, PAGE_H - CARD_H + 16
                try:
                    canvas.saveState()
                    p = canvas.beginPath()
                    p.roundRect(px, py, photo_size, photo_size, 8)
                    canvas.clipPath(p, stroke=0)
                    reader = ImageReader(img_bytes)
                    canvas.drawImage(reader, px, py, width=photo_size, height=photo_size, preserveAspectRatio=True)
                    canvas.restoreState()
                    canvas.setStrokeColor(mint_accent)
                    canvas.setLineWidth(2)
                    canvas.roundRect(px, py, photo_size, photo_size, 8, stroke=1, fill=0)
                except Exception:
                    pass

        canvas.restoreState()

    def on_later_pages(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(emerald_dark)
        canvas.rect(0, PAGE_H - 5, PAGE_W, 5, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.setFont(f_reg, 8)
        canvas.drawRightString(PAGE_W - 32, PAGE_H - 18, f"Page {doc.page}")
        canvas.restoreState()

    body = []
    body.append(Spacer(1, CARD_H - 12))
    order = getattr(resume, "section_order", None) or ["summary", "skills", "experience", "projects", "education", "certifications"]

    def add_em_summary():
        if resume.show_summary and resume.professional_summary:
            sec_flow = [
                Paragraph(f"<font color='{mint_accent.hexval()}'>■</font>  EXECUTIVE SUMMARY", S["EmSecHdr"]),
                HRFlowable(width="100%", thickness=1.4, color=mint_accent, spaceBefore=0, spaceAfter=4),
                Paragraph(resume.professional_summary, S["EmBody"])
            ]
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h))

    def add_em_skills():
        if resume.show_skills and resume.skill_categories:
            sec_flow = [
                Paragraph(f"<font color='{mint_accent.hexval()}'>■</font>  CORE COMPETENCIES & EXPERTISE", S["EmSecHdr"]),
                HRFlowable(width="100%", thickness=1.4, color=mint_accent, spaceBefore=0, spaceAfter=4)
            ]
            for cat in resume.skill_categories:
                if cat.skills:
                    sec_flow.append(Paragraph(f"<b>{cat.category_name}:</b> " + ", ".join(cat.skills), S["EmBody"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h))

    def add_em_experience():
        if resume.show_experience and resume.work_experience:
            first_exp = resume.work_experience[0]
            loc0 = f" · {first_exp.location}" if first_exp.location else ""
            date0 = f"{first_exp.start_date} – {first_exp.end_date}"
            first_flow = [
                Paragraph(f"<font color='{mint_accent.hexval()}'>■</font>  PROFESSIONAL EXPERIENCE", S["EmSecHdr"]),
                HRFlowable(width="100%", thickness=1.4, color=mint_accent, spaceBefore=0, spaceAfter=4),
                Paragraph(f"<b>{first_exp.job_title}</b> — <font color='{emerald_dark.hexval()}'>{first_exp.company}</font>{loc0}", S["EmJob"]),
                Paragraph(f"<font color='#64748B' size='8'>({date0})</font>", S["EmCompany"])
            ]
            if first_exp.bullet_points:
                first_flow.append(Paragraph(f"• {first_exp.bullet_points[0].lstrip('•- ')}", S["EmBullet"]))
            body.append(KeepTogether(first_flow))
            for b in first_exp.bullet_points[1:]:
                body.append(Paragraph(f"• {b.lstrip('•- ')}", S["EmBullet"]))
            body.append(Spacer(1, spacer_h * 0.9))

            for exp in resume.work_experience[1:]:
                loc = f" · {exp.location}" if exp.location else ""
                date_str = f"{exp.start_date} – {exp.end_date}"
                item_flow = [
                    Paragraph(f"<b>{exp.job_title}</b> — <font color='{emerald_dark.hexval()}'>{exp.company}</font>{loc}", S["EmJob"]),
                    Paragraph(f"<font color='#64748B' size='8'>({date_str})</font>", S["EmCompany"])
                ]
                if exp.bullet_points:
                    item_flow.append(Paragraph(f"• {exp.bullet_points[0].lstrip('•- ')}", S["EmBullet"]))
                body.append(KeepTogether(item_flow))
                for b in exp.bullet_points[1:]:
                    body.append(Paragraph(f"• {b.lstrip('•- ')}", S["EmBullet"]))
                body.append(Spacer(1, spacer_h * 0.9))

    def add_em_projects():
        if resume.show_projects and resume.projects:
            first_proj = resume.projects[0]
            tech0 = f" <font color='{mint_accent.hexval()}'>[{', '.join(first_proj.technologies)}]</font>" if first_proj.technologies else ""
            demo0 = f" | <i>Demo: {first_proj.demo_url}</i>" if getattr(first_proj, "demo_url", None) else ""
            repo0 = f" | <i>Repo: {first_proj.link}</i>" if first_proj.link else ""
            first_flow = [
                Paragraph(f"<font color='{mint_accent.hexval()}'>■</font>  KEY SYSTEMS & PROJECTS", S["EmSecHdr"]),
                HRFlowable(width="100%", thickness=1.4, color=mint_accent, spaceBefore=0, spaceAfter=4),
                Paragraph(f"<b>{first_proj.name}</b>{tech0}{demo0}{repo0}", S["EmJob"])
            ]
            if first_proj.description_bullets:
                first_flow.append(Paragraph(f"• {first_proj.description_bullets[0].lstrip('•- ')}", S["EmBullet"]))
            body.append(KeepTogether(first_flow))
            for b in first_proj.description_bullets[1:]:
                body.append(Paragraph(f"• {b.lstrip('•- ')}", S["EmBullet"]))
            body.append(Spacer(1, spacer_h * 0.9))

            for proj in resume.projects[1:]:
                tech = f" <font color='{mint_accent.hexval()}'>[{', '.join(proj.technologies)}]</font>" if proj.technologies else ""
                demo = f" | <i>Demo: {proj.demo_url}</i>" if getattr(proj, "demo_url", None) else ""
                repo = f" | <i>Repo: {proj.link}</i>" if proj.link else ""
                item_flow = [Paragraph(f"<b>{proj.name}</b>{tech}{demo}{repo}", S["EmJob"])]
                if proj.description_bullets:
                    item_flow.append(Paragraph(f"• {proj.description_bullets[0].lstrip('•- ')}", S["EmBullet"]))
                body.append(KeepTogether(item_flow))
                for b in proj.description_bullets[1:]:
                    body.append(Paragraph(f"• {b.lstrip('•- ')}", S["EmBullet"]))
                body.append(Spacer(1, spacer_h * 0.9))

    def add_em_education():
        if resume.show_education and resume.education:
            sec_flow = [
                Paragraph(f"<font color='{mint_accent.hexval()}'>■</font>  EDUCATION & QUALIFICATIONS", S["EmSecHdr"]),
                HRFlowable(width="100%", thickness=1.4, color=mint_accent, spaceBefore=0, spaceAfter=4)
            ]
            for edu in resume.education:
                loc = f" · {edu.location}" if edu.location else ""
                det = f" – {edu.details}" if getattr(edu, "details", None) else ""
                sec_flow.append(Paragraph(f"<b>{edu.degree}</b> — {edu.institution}{loc} <font color='#64748B'>({edu.graduation_year})</font>{det}", S["EmBody"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h * 0.8))

    def add_em_certifications():
        if resume.show_certifications and resume.certifications:
            sec_flow = [
                Paragraph(f"<font color='{mint_accent.hexval()}'>■</font>  CERTIFICATIONS & HONORS", S["EmSecHdr"]),
                HRFlowable(width="100%", thickness=1.4, color=mint_accent, spaceBefore=0, spaceAfter=4)
            ]
            for cert in resume.certifications:
                year_str = f" <font color='#64748B'>({cert.year})</font>" if cert.year else ""
                sec_flow.append(Paragraph(f"• <b>{cert.name}</b> — {cert.issuer}{year_str}", S["EmBody"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h * 0.8))

    raw_order = getattr(resume, "section_order", None) or ["summary", "skills", "experience", "projects", "education", "certifications"]
    order = list(raw_order)
    for sec_name, is_active in [
        ("summary", resume.show_summary and resume.professional_summary),
        ("skills", resume.show_skills and resume.skill_categories),
        ("experience", resume.show_experience and resume.work_experience),
        ("projects", resume.show_projects and resume.projects),
        ("education", resume.show_education and resume.education),
        ("certifications", resume.show_certifications and resume.certifications),
    ]:
        if is_active and sec_name not in order:
            order.append(sec_name)

    for sec in order:
        if sec == "summary":
            add_em_summary()
        elif sec == "skills":
            add_em_skills()
        elif sec == "experience":
            add_em_experience()
        elif sec == "projects":
            add_em_projects()
        elif sec == "education":
            add_em_education()
        elif sec == "certifications":
            add_em_certifications()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=32, rightMargin=32, topMargin=24, bottomMargin=22)
    doc.build(body, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# 5. TECH NOIR (Cyber / Terminal Developer Blueprint)
# ─────────────────────────────────────────────────────────────────────────────

def _tech_noir_pdf(resume: TailoredResume) -> bytes:
    """
    Format 5: Cyber Terminal Developer Blueprint.
    - Obsidian slate (#0B1120) console header with macOS window dots (● ● ●).
    - Code syntax section headers: '// 01. PROFESSIONAL_SUMMARY', '// 02. WORK_EXPERIENCE'.
    - Terminal command prompt styling and Cyan Blue (#06B6D4) tech accents.
    """
    PAGE_W, PAGE_H = letter
    CONSOLE_H = 82

    f_reg, f_bold, f_italic = _get_font_names(getattr(resume, "font_family", "Courier"))
    font_scale = getattr(resume, "font_size_scale", "standard") or "standard"

    if font_scale == "compact":
        body_size, body_leading, sec_size, spacer_h = 8.4, 11.5, 10.2, 3.0
    elif font_scale == "large":
        body_size, body_leading, sec_size, spacer_h = 9.8, 13.8, 11.8, 5.5
    elif font_scale == "spacious":
        body_size, body_leading, sec_size, spacer_h = 10.5, 14.8, 12.5, 6.5
    else:
        body_size, body_leading, sec_size, spacer_h = 9.0, 12.8, 11.0, 4.5

    obsidian = colors.HexColor("#0B1120")
    cyan_tech = colors.HexColor("#06B6D4")
    if resume.custom_accent_color:
        cyan_tech = colors.HexColor(resume.custom_accent_color)

    dark_text = colors.HexColor("#0F172A")
    body_text = colors.HexColor("#1E293B")

    S = getSampleStyleSheet()
    _add(S, ParagraphStyle("TnSecHdr", fontName=f_bold, fontSize=sec_size, leading=sec_size + 3.0, textColor=obsidian, spaceBefore=6, spaceAfter=2, keepWithNext=True))
    _add(S, ParagraphStyle("TnJob", fontName=f_bold, fontSize=body_size + 0.8, leading=body_leading + 1, textColor=dark_text, keepWithNext=True))
    _add(S, ParagraphStyle("TnCompany", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=cyan_tech))
    _add(S, ParagraphStyle("TnBody", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=body_text, spaceAfter=2))
    _add(S, ParagraphStyle("TnBullet", fontName=f_reg, fontSize=body_size, leading=body_leading, textColor=body_text, leftIndent=10, firstLineIndent=-7, spaceAfter=1.8))

    def on_first_page(canvas, doc):
        canvas.saveState()
        info = resume.personal_info

        # Top Terminal Console Bar
        canvas.setFillColor(obsidian)
        canvas.rect(0, PAGE_H - CONSOLE_H, PAGE_W, CONSOLE_H, fill=1, stroke=0)

        # 3 Terminal Dots (Red, Yellow, Green)
        dot_y = PAGE_H - 18
        canvas.setFillColor(colors.HexColor("#EF4444"))
        canvas.circle(36, dot_y, 4, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#F59E0B"))
        canvas.circle(48, dot_y, 4, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#10B981"))
        canvas.circle(60, dot_y, 4, fill=1, stroke=0)

        # Terminal prompt string
        canvas.setFont(f_reg, 7.5)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.drawString(74, dot_y - 2.5, "user@cloud:~$ cat /sys/engineer_profile.json")

        # Candidate Name & Role
        canvas.setFillColor(colors.white)
        canvas.setFont(f_bold, 18)
        canvas.drawString(34, PAGE_H - 42, (info.full_name or "").upper())

        canvas.setFont(f_bold, 9.5)
        canvas.setFillColor(cyan_tech)
        if resume.target_job_title:
            canvas.drawString(34, PAGE_H - 56, f"// ROLE: {resume.target_job_title}")

        # Contact Prompt Line
        contacts = []
        if info.email:    contacts.append(f"> mail: {info.email}")
        if info.phone:    contacts.append(f"> tel: {info.phone}")
        if info.location: contacts.append(f"> loc: {info.location}")
        if info.github:   contacts.append(f"> git: {info.github}")

        canvas.setFont(f_reg, 7.5)
        canvas.setFillColor(colors.HexColor("#94A3B8"))
        canvas.drawString(34, PAGE_H - 72, "  |  ".join(contacts)[:135])

        # Photo if enabled
        has_photo = bool(getattr(resume, "show_photo", False) and info.avatar_url and info.avatar_url.strip())
        if has_photo:
            img_bytes = _load_avatar_image(info.avatar_url)
            if img_bytes:
                photo_size = 50
                px, py = PAGE_W - 74, PAGE_H - CONSOLE_H + 12
                try:
                    canvas.saveState()
                    p = canvas.beginPath()
                    p.roundRect(px, py, photo_size, photo_size, 6)
                    canvas.clipPath(p, stroke=0)
                    reader = ImageReader(img_bytes)
                    canvas.drawImage(reader, px, py, width=photo_size, height=photo_size, preserveAspectRatio=True)
                    canvas.restoreState()
                    canvas.setStrokeColor(cyan_tech)
                    canvas.setLineWidth(1.8)
                    canvas.roundRect(px, py, photo_size, photo_size, 6, stroke=1, fill=0)
                except Exception:
                    pass

        canvas.restoreState()

    def on_later_pages(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(obsidian)
        canvas.rect(0, PAGE_H - 5, PAGE_W, 5, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#64748B"))
        canvas.setFont(f_reg, 8)
        canvas.drawRightString(PAGE_W - 32, PAGE_H - 18, f"Page {doc.page}")
        canvas.restoreState()

    body = []
    body.append(Spacer(1, CONSOLE_H - 12))
    order = getattr(resume, "section_order", None) or ["summary", "skills", "experience", "projects", "education", "certifications"]

    def add_tn_summary():
        if resume.show_summary and resume.professional_summary:
            sec_flow = [
                Paragraph(f"<font color='{cyan_tech.hexval()}'>// </font><b>01. PROFESSIONAL_SUMMARY</b>", S["TnSecHdr"]),
                HRFlowable(width="100%", thickness=1.2, color=cyan_tech, spaceBefore=0, spaceAfter=4),
                Paragraph(resume.professional_summary, S["TnBody"])
            ]
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h))

    def add_tn_skills():
        if resume.show_skills and resume.skill_categories:
            sec_flow = [
                Paragraph(f"<font color='{cyan_tech.hexval()}'>// </font><b>02. TECHNICAL_STACK & REPOSITORIES</b>", S["TnSecHdr"]),
                HRFlowable(width="100%", thickness=1.2, color=cyan_tech, spaceBefore=0, spaceAfter=4)
            ]
            for cat in resume.skill_categories:
                if cat.skills:
                    sec_flow.append(Paragraph(f"<b>[{cat.category_name.upper()}]:</b> " + ", ".join(cat.skills), S["TnBody"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h))

    def add_tn_experience():
        if resume.show_experience and resume.work_experience:
            first_exp = resume.work_experience[0]
            loc0 = f" · {first_exp.location}" if first_exp.location else ""
            date0 = f"{first_exp.start_date} – {first_exp.end_date}"
            first_flow = [
                Paragraph(f"<font color='{cyan_tech.hexval()}'>// </font><b>03. PRODUCTION_WORK_EXPERIENCE</b>", S["TnSecHdr"]),
                HRFlowable(width="100%", thickness=1.2, color=cyan_tech, spaceBefore=0, spaceAfter=4),
                Paragraph(f"<b>{first_exp.job_title}</b> @ <font color='{cyan_tech.hexval()}'>{first_exp.company}</font>{loc0}", S["TnJob"]),
                Paragraph(f"<font color='#64748B' size='8'>({date0})</font>", S["TnCompany"])
            ]
            if first_exp.bullet_points:
                first_flow.append(Paragraph(f"> {first_exp.bullet_points[0].lstrip('•- ')}", S["TnBullet"]))
            body.append(KeepTogether(first_flow))
            for b in first_exp.bullet_points[1:]:
                body.append(Paragraph(f"> {b.lstrip('•- ')}", S["TnBullet"]))
            body.append(Spacer(1, spacer_h * 0.9))

            for exp in resume.work_experience[1:]:
                loc = f" · {exp.location}" if exp.location else ""
                date_str = f"{exp.start_date} – {exp.end_date}"
                item_flow = [
                    Paragraph(f"<b>{exp.job_title}</b> @ <font color='{cyan_tech.hexval()}'>{exp.company}</font>{loc}", S["TnJob"]),
                    Paragraph(f"<font color='#64748B' size='8'>({date_str})</font>", S["TnCompany"])
                ]
                if exp.bullet_points:
                    item_flow.append(Paragraph(f"> {exp.bullet_points[0].lstrip('•- ')}", S["TnBullet"]))
                body.append(KeepTogether(item_flow))
                for b in exp.bullet_points[1:]:
                    body.append(Paragraph(f"> {b.lstrip('•- ')}", S["TnBullet"]))
                body.append(Spacer(1, spacer_h * 0.9))

    def add_tn_projects():
        if resume.show_projects and resume.projects:
            first_proj = resume.projects[0]
            tech0 = f" <font color='{cyan_tech.hexval()}'>[{', '.join(first_proj.technologies)}]</font>" if first_proj.technologies else ""
            demo0 = f" | <i>Demo: {first_proj.demo_url}</i>" if getattr(first_proj, "demo_url", None) else ""
            repo0 = f" | <i>Repo: {first_proj.link}</i>" if first_proj.link else ""
            first_flow = [
                Paragraph(f"<font color='{cyan_tech.hexval()}'>// </font><b>04. KEY_ENGINEERED_SYSTEMS</b>", S["TnSecHdr"]),
                HRFlowable(width="100%", thickness=1.2, color=cyan_tech, spaceBefore=0, spaceAfter=4),
                Paragraph(f"<b>{first_proj.name}</b>{tech0}{demo0}{repo0}", S["TnJob"])
            ]
            if first_proj.description_bullets:
                first_flow.append(Paragraph(f"> {first_proj.description_bullets[0].lstrip('•- ')}", S["TnBullet"]))
            body.append(KeepTogether(first_flow))
            for b in first_proj.description_bullets[1:]:
                body.append(Paragraph(f"> {b.lstrip('•- ')}", S["TnBullet"]))
            body.append(Spacer(1, spacer_h * 0.9))

            for proj in resume.projects[1:]:
                tech = f" <font color='{cyan_tech.hexval()}'>[{', '.join(proj.technologies)}]</font>" if proj.technologies else ""
                demo = f" | <i>Demo: {proj.demo_url}</i>" if getattr(proj, "demo_url", None) else ""
                repo = f" | <i>Repo: {proj.link}</i>" if proj.link else ""
                item_flow = [Paragraph(f"<b>{proj.name}</b>{tech}{demo}{repo}", S["TnJob"])]
                if proj.description_bullets:
                    item_flow.append(Paragraph(f"> {proj.description_bullets[0].lstrip('•- ')}", S["TnBullet"]))
                body.append(KeepTogether(item_flow))
                for b in proj.description_bullets[1:]:
                    body.append(Paragraph(f"> {b.lstrip('•- ')}", S["TnBullet"]))
                body.append(Spacer(1, spacer_h * 0.9))

    def add_tn_education():
        if resume.show_education and resume.education:
            sec_flow = [
                Paragraph(f"<font color='{cyan_tech.hexval()}'>// </font><b>05. ACADEMIC_QUALIFICATIONS</b>", S["TnSecHdr"]),
                HRFlowable(width="100%", thickness=1.2, color=cyan_tech, spaceBefore=0, spaceAfter=4)
            ]
            for edu in resume.education:
                loc = f" · {edu.location}" if edu.location else ""
                det = f" – {edu.details}" if getattr(edu, "details", None) else ""
                sec_flow.append(Paragraph(f"<b>{edu.degree}</b> — {edu.institution}{loc} <font color='#64748B'>({edu.graduation_year})</font>{det}", S["TnBody"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h * 0.8))

    def add_tn_certifications():
        if resume.show_certifications and resume.certifications:
            sec_flow = [
                Paragraph(f"<font color='{cyan_tech.hexval()}'>// </font><b>06. CERTIFICATIONS_&_CREDENTIALS</b>", S["TnSecHdr"]),
                HRFlowable(width="100%", thickness=1.2, color=cyan_tech, spaceBefore=0, spaceAfter=4)
            ]
            for cert in resume.certifications:
                year_str = f" <font color='#64748B'>({cert.year})</font>" if cert.year else ""
                sec_flow.append(Paragraph(f"> <b>{cert.name}</b> — {cert.issuer}{year_str}", S["TnBody"]))
            body.append(KeepTogether(sec_flow))
            body.append(Spacer(1, spacer_h * 0.8))

    raw_order = getattr(resume, "section_order", None) or ["summary", "skills", "experience", "projects", "education", "certifications"]
    order = list(raw_order)
    for sec_name, is_active in [
        ("summary", resume.show_summary and resume.professional_summary),
        ("skills", resume.show_skills and resume.skill_categories),
        ("experience", resume.show_experience and resume.work_experience),
        ("projects", resume.show_projects and resume.projects),
        ("education", resume.show_education and resume.education),
        ("certifications", resume.show_certifications and resume.certifications),
    ]:
        if is_active and sec_name not in order:
            order.append(sec_name)

    for sec in order:
        if sec == "summary":
            add_tn_summary()
        elif sec == "skills":
            add_tn_skills()
        elif sec == "experience":
            add_tn_experience()
        elif sec == "projects":
            add_tn_projects()
        elif sec == "education":
            add_tn_education()
        elif sec == "certifications":
            add_tn_certifications()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=32, rightMargin=32, topMargin=24, bottomMargin=22)
    doc.build(body, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buf.seek(0)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# COVER LETTER PDF
# ─────────────────────────────────────────────────────────────────────────────

def generate_cover_letter_pdf(resume: TailoredResume, is_free_watermarked: bool = False) -> bytes:
    _sync_resume_social_links(resume)
    buf = io.BytesIO()
    primary = colors.HexColor(resume.custom_accent_color or "#1E3A8A")
    dark = colors.HexColor("#0F172A")
    PAGE_W, PAGE_H = letter

    cl = resume.cover_letter
    info = resume.personal_info
    layout = getattr(cl, "layout_style", "modern_banner") or "modern_banner"

    top_margin = 42
    if layout == "modern_banner":
        top_margin = 86

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=44,
        rightMargin=44,
        topMargin=top_margin,
        bottomMargin=46 if is_free_watermarked else 40,
    )
    f_reg, f_bold, f_italic = _get_font_names(getattr(resume, "font_family", "Helvetica"))
    S = getSampleStyleSheet()

    _add(S, ParagraphStyle("ClName", fontName=f_bold, fontSize=18, leading=22, textColor=primary, spaceAfter=2))
    _add(S, ParagraphStyle("ClNameCenter", fontName=f_bold, fontSize=19, leading=23, textColor=primary, alignment=TA_CENTER, spaceAfter=3))
    _add(S, ParagraphStyle("ClCont", fontName=f_reg, fontSize=9.0, leading=13, textColor=colors.HexColor("#475569"), spaceAfter=10))
    _add(S, ParagraphStyle("ClContCenter", fontName=f_reg, fontSize=9.0, leading=13, textColor=colors.HexColor("#475569"), alignment=TA_CENTER, spaceAfter=10))
    _add(S, ParagraphStyle("ClDate", fontName=f_bold, fontSize=9.2, leading=13, textColor=colors.HexColor("#334155"), spaceAfter=8))
    _add(S, ParagraphStyle("ClRec", fontName=f_reg, fontSize=9.5, leading=14, textColor=dark, spaceAfter=10))
    _add(S, ParagraphStyle("ClSubject", fontName=f_bold, fontSize=10.5, leading=14.5, textColor=primary, spaceBefore=4, spaceAfter=10))
    _add(S, ParagraphStyle("ClSal", fontName=f_bold, fontSize=10, leading=14, textColor=dark, spaceAfter=8))
    _add(S, ParagraphStyle("ClPar", fontName=f_reg, fontSize=9.8, leading=14.5, textColor=dark, spaceAfter=10))
    _add(S, ParagraphStyle("ClSignOff", fontName=f_reg, fontSize=10, leading=14, textColor=dark, spaceBefore=8, spaceAfter=4))
    _add(S, ParagraphStyle("ClSignerName", fontName=f_bold, fontSize=10.5, leading=14, textColor=dark, spaceAfter=1))
    _add(S, ParagraphStyle("ClSignerTitle", fontName=f_reg, fontSize=9, leading=12.5, textColor=colors.HexColor("#64748B"), spaceAfter=8))
    _add(S, ParagraphStyle("ClScriptSig", fontName="Times-Italic", fontSize=18, leading=22, textColor=primary, spaceBefore=2, spaceAfter=4))
    _add(S, ParagraphStyle("ClPostscript", fontName=f_italic, fontSize=9.2, leading=13.5, textColor=dark, spaceBefore=8, spaceAfter=3))
    _add(S, ParagraphStyle("ClEnclosure", fontName=f_reg, fontSize=8.5, leading=12, textColor=colors.HexColor("#64748B"), spaceBefore=4))

    story = []

    def on_first_page(canvas, doc):
        if layout == "modern_banner":
            canvas.saveState()
            BANNER_H = 68
            # Top Banner in Primary Accent Color
            canvas.setFillColor(primary)
            canvas.rect(0, PAGE_H - BANNER_H, PAGE_W, BANNER_H, fill=1, stroke=0)

            # Name & Title
            canvas.setFillColor(colors.white)
            canvas.setFont(f_bold, 20)
            canvas.drawString(44, PAGE_H - 32, (info.full_name or "").upper())

            canvas.setFont(f_bold, 9.5)
            canvas.setFillColor(colors.HexColor("#E2E8F0"))
            tag = getattr(cl, "sign_off_title", None) or getattr(resume, "target_job_title", "")
            if tag:
                canvas.drawString(44, PAGE_H - 46, tag.upper())

            # Contact ribbon underneath
            ribbon_y = PAGE_H - BANNER_H
            contacts = [p for p in [info.email, info.phone, info.location, info.linkedin] if p]
            canvas.setFillColor(colors.HexColor("#F8FAFC"))
            canvas.rect(0, ribbon_y - 18, PAGE_W, 18, fill=1, stroke=0)
            canvas.setStrokeColor(colors.HexColor("#E2E8F0"))
            canvas.setLineWidth(0.8)
            canvas.line(0, ribbon_y - 18, PAGE_W, ribbon_y - 18)

            canvas.setFillColor(colors.HexColor("#475569"))
            canvas.setFont(f_reg, 8)
            canvas.drawString(44, ribbon_y - 13, "   •   ".join(contacts)[:135])
            canvas.restoreState()

        # Watermark (Center Diagonal Badge + Bottom Footer) for Free Starter Plan
        if is_free_watermarked:
            # 1. Semi-transparent diagonal branding badge right across middle of text
            _draw_diagonal_watermark(
                canvas, PAGE_W, PAGE_H,
                brand_title="DreemFolio AI",
                subtitle="FREE STARTER TIER  •  UPGRADE TO PRO ($9/MO) FOR UNBRANDED"
            )

            # 2. Professional bottom footer line
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
            canvas.setLineWidth(0.6)
            canvas.line(44, 28, PAGE_W - 44, 28)

            canvas.setFont(f_bold, 7.5)
            canvas.setFillColor(colors.HexColor("#64748B"))
            watermark_text = "Generated via DreemFolio AI (Free Starter Tier)  •  Upgrade to Pro ($9/mo) for Unbranded & Unlimited Downloads"
            canvas.drawCentredString(PAGE_W / 2.0, 16, watermark_text)
            canvas.restoreState()

    # If layout is NOT modern_banner, build letterhead in story:
    if layout == "classic_corporate":
        story.append(Paragraph(info.full_name.upper(), S["ClName"]))
        contacts = [p for p in [info.location, info.phone, info.email, info.linkedin] if p]
        story.append(Paragraph(" | ".join(contacts), S["ClCont"]))
        story.append(HRFlowable(width="100%", thickness=1.5, color=primary, spaceBefore=0, spaceAfter=14))
    elif layout == "minimal_clean":
        story.append(Paragraph(info.full_name.upper(), S["ClNameCenter"]))
        contacts = [p for p in [info.location, info.phone, info.email, info.linkedin] if p]
        story.append(Paragraph(" • ".join(contacts), S["ClContCenter"]))
        story.append(HRFlowable(width="40%", thickness=0.8, color=primary, hAlign="CENTER", spaceBefore=0, spaceAfter=14))

    # Formal Letter Date
    letter_date = getattr(cl, "letter_date", None)
    if letter_date and letter_date.strip():
        story.append(Paragraph(letter_date.strip(), S["ClDate"]))

    # Recipient block
    rec_lines = [
        x for x in [
            f"<b>{cl.recipient_name}</b>" if cl.recipient_name else "",
            cl.recipient_title or "",
            cl.company_name or "",
            cl.company_address or "",
        ] if x.strip()
    ]
    if rec_lines:
        story.append(Paragraph("<br/>".join(rec_lines), S["ClRec"]))

    # Subject / RE line
    ref_sub = getattr(cl, "reference_subject", None)
    if ref_sub and ref_sub.strip():
        story.append(Paragraph(f"<b>RE: {ref_sub.strip()}</b>", S["ClSubject"]))

    # Salutation
    story.append(Paragraph(cl.salutation or "Dear Hiring Manager,", S["ClSal"]))

    # Body Paragraphs
    if cl.opening_paragraph:
        story.append(Paragraph(cl.opening_paragraph, S["ClPar"]))
    if cl.body_paragraph:
        story.append(Paragraph(cl.body_paragraph, S["ClPar"]))
    if cl.closing_paragraph:
        story.append(Paragraph(cl.closing_paragraph, S["ClPar"]))

    # Sign-off & Signature
    sign_block = []
    sign_block.append(Paragraph(cl.sign_off or "Sincerely,", S["ClSignOff"]))

    sig_mode = getattr(cl, "signature_mode", "script") or "script"
    sig_img_data = getattr(cl, "signature_image_data", None)

    if sig_mode in ["draw", "upload"] and sig_img_data:
        try:
            b64_str = sig_img_data
            if "," in b64_str:
                b64_str = b64_str.split(",")[1]
            raw_sig = base64.b64decode(b64_str)
            sig_stream = io.BytesIO(raw_sig)
            sign_block.append(Spacer(1, 2))
            sign_block.append(RLImage(sig_stream, width=125, height=34))
            sign_block.append(Spacer(1, 2))
        except Exception:
            sign_block.append(Spacer(1, 14))
    elif sig_mode == "script":
        sig_color = primary.hexval()
        sign_block.append(Spacer(1, 2))
        sign_block.append(Paragraph(f"<font color='{sig_color}'><i>{info.full_name}</i></font>", S["ClScriptSig"]))
        sign_block.append(Spacer(1, 2))
    else:
        sign_block.append(Spacer(1, 12))

    sign_block.append(Paragraph(info.full_name, S["ClSignerName"]))
    sign_title = getattr(cl, "sign_off_title", None) or getattr(resume, "target_job_title", None)
    if sign_title:
        sign_block.append(Paragraph(sign_title, S["ClSignerTitle"]))

    # Postscript & Enclosure
    ps = getattr(cl, "postscript", None)
    if ps and ps.strip():
        ps_clean = ps.strip()
        if not ps_clean.startswith("P.S."):
            ps_clean = f"P.S. {ps_clean}"
        sign_block.append(Paragraph(f"<b>{ps_clean[:4]}</b> {ps_clean[4:].strip()}", S["ClPostscript"]))

    enc = getattr(cl, "enclosure", None)
    if enc and enc.strip():
        sign_block.append(Paragraph(f"<i>{enc.strip()}</i>", S["ClEnclosure"]))

    story.append(KeepTogether(sign_block))

    doc.build(story, onFirstPage=on_first_page)
    buf.seek(0)
    return buf.getvalue()
