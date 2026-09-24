"""
ATS Single-Column Templates:
- Classic: Standard professional ATS format
- Modern (Navy): Crisp dark-navy accented ATS format
- Minimal (Compact): Space-saving compact single-column format
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

def _ats_pdf(resume: TailoredResume, style: str) -> bytes:
    buf = io.BytesIO()
    f_reg, f_bold, f_italic = _get_font_names(getattr(resume, "font_family", "Helvetica"))
    font_scale = getattr(resume, "font_size_scale", "standard") or "standard"

    if font_scale == "compact":
        margin = 26
        top_margin = 20
        body_font_size = 8.5
        body_leading = 11.5
        hdr_font_size = 10.2
        hdr_leading = 13.0
        name_font_size = 16.5
        spacer_gap = 2.0
    elif font_scale == "large":
        margin = 38
        top_margin = 26
        body_font_size = 9.8
        body_leading = 13.6
        hdr_font_size = 11.5
        hdr_leading = 14.5
        name_font_size = 19.0
        spacer_gap = 3.8
    elif font_scale == "spacious":
        margin = 42
        top_margin = 28
        body_font_size = 10.5
        body_leading = 14.5
        hdr_font_size = 12.2
        hdr_leading = 15.5
        name_font_size = 20.0
        spacer_gap = 4.5
    else:  # standard
        margin = 36
        top_margin = 24
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
        topMargin=top_margin,
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

