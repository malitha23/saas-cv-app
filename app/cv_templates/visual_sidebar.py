"""
Visual Sidebar Template:
- 2-Column layout with stylish dark slate/navy left sidebar
- Candidate avatar photo display
- Dynamic skill progress meters (sleek, segmented, badge)
- High-impact white main content column
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

