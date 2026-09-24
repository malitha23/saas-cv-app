"""
Emerald Prestige Template:
- Executive luxury deep emerald green accents
- Prestigious serif/sans header styling
- Elegant borders and refined section dividers
"""
import io
import os
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
from app.cv_templates.common import (
    _add, _hex_to_rgb, _load_avatar_image, _get_font_names,
    _draw_diagonal_watermark, _draw_sidebar_para, _draw_skill_progress_bar,
    _sync_resume_social_links
)

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

