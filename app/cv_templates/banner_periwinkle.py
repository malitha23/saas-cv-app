"""
Periwinkle Banner Template:
- Periwinkle / Violet colored stylish header banner
- Modern clean typography and structured section cards
- Prominent contact info & skills layout
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

