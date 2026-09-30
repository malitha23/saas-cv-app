"""
Aurelian Executive CV Template:
- High-end luxury editorial executive aesthetic (Lorna Alvarado Aurelian style)
- 36% Left Sidebar in warm luxury Ivory/Cream (#FAF7F2) with fine hairline border (#E5E0D8)
- Subtle candidate monogram watermark in top-right of sidebar
- Candidate avatar with double concentric refined frames (inner bronze ring, outer hairline ring)
- Centered Candidate Name in editorial serif with small-caps bronze eyebrow and divider
- Numbered sidebar section headers (01 Contact, 02 Profile, 03 Expertise, 04 Languages)
- Refined 5-dot bronze rating indicators for skills
- Right main column with Roman numeral serif headers (I. Education, II. Experience, III. Projects, IV. Certifications)
- Delicate hairline timeline with hollow bronze node dots
- Bottom executive signature styling with candidate name & date
"""
import io
import os
import datetime
from typing import Optional, List

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Flowable, Paragraph, Spacer, Table, TableStyle, SimpleDocTemplate, KeepTogether, HRFlowable
)

from app.schemas import TailoredResume
from app.cv_templates.common import (
    _add, _hex_to_rgb, _load_avatar_image, _get_font_names,
    _draw_diagonal_watermark, _draw_sidebar_para, _draw_skill_progress_bar, _clean_pdf_text,
    _sync_resume_social_links, _sanitize_pdf_data
)


class AurelianTimelineDot(Flowable):
    """
    Renders the elegant hollow circular bronze node dot on the left of each experience and education item.
    """
    def __init__(self, dot_color=colors.HexColor("#B8935A"), ring_color=colors.white, radius: float = 3.2):
        super().__init__()
        self.dot_color = dot_color
        self.ring_color = ring_color
        self.radius = radius
        self.width = 14
        self.height = 14

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        c.saveState()
        x = 9.0
        y = 7.0
        # White fill background with bronze outer ring
        c.setFillColor(self.ring_color)
        c.setStrokeColor(self.dot_color)
        c.setLineWidth(1.4)
        c.circle(x, y, self.radius, fill=1, stroke=1)
        c.restoreState()


def _draw_aurelian_sidebar_header(canvas, num_str: str, title: str, bronze_color, hairline_color, x: float, y_top: float, max_w: float, f_bold: str, f_reg: str) -> float:
    """
    Draws a numbered section header in the sidebar:
    e.g. '01  Contact ──────────'
    Returns vertical height consumed.
    """
    canvas.saveState()

    # Number in bronze
    canvas.setFont(f_bold, 8.5)
    canvas.setFillColor(bronze_color)
    canvas.drawString(x, y_top - 9.0, num_str)
    num_w = canvas.stringWidth(num_str, f_bold, 8.5)

    # Title in serif / dark ink
    canvas.setFont("Times-Bold", 12.0)
    canvas.setFillColor(colors.HexColor("#0F0F0F"))
    title_x = x + num_w + 6.0
    canvas.drawString(title_x, y_top - 9.0, title)
    title_w = canvas.stringWidth(title, "Times-Bold", 12.0)

    # Hairline rule extending to the right edge
    rule_start_x = title_x + title_w + 6.0
    rule_end_x = x + max_w
    if rule_end_x > rule_start_x + 5.0:
        canvas.setStrokeColor(hairline_color)
        canvas.setLineWidth(0.8)
        canvas.line(rule_start_x, y_top - 5.5, rule_end_x, y_top - 5.5)

    canvas.restoreState()
    return 20.0


def _draw_aurelian_skill_dots(canvas, name: str, level_pct: int, bronze_color, hairline_color, x: float, y: float, max_w: float, font_name: str, font_size: float = 7.8) -> float:
    """
    Draws a skill entry with 5 refined dot ratings on the right.
    """
    canvas.saveState()
    canvas.setFont(font_name, font_size)
    canvas.setFillColor(colors.HexColor("#2A2A2A"))

    dots_total_w = 5 * 7.0
    text_max_w = max_w - dots_total_w - 6.0
    display_name = name
    while canvas.stringWidth(display_name, font_name, font_size) > text_max_w and len(display_name) > 3:
        display_name = display_name[:-1]
    if display_name != name:
        display_name = display_name[:-2] + ".."

    canvas.drawString(x, y, display_name)

    filled_count = max(1, min(5, round((level_pct / 100.0) * 5)))
    dots_start_x = x + max_w - dots_total_w
    dot_y = y + 2.5
    for i in range(5):
        dx = dots_start_x + (i * 7.0)
        if i < filled_count:
            canvas.setFillColor(bronze_color)
            canvas.circle(dx, dot_y, 2.0, fill=1, stroke=0)
        else:
            canvas.setFillColor(hairline_color)
            canvas.circle(dx, dot_y, 1.8, fill=1, stroke=0)

    # Soft hairline divider below
    canvas.setStrokeColor(colors.HexColor("#F0ECE5"))
    canvas.setLineWidth(0.5)
    canvas.line(x, y - 3.0, x + max_w, y - 3.0)

    canvas.restoreState()
    return 11.0


def _extract_monogram(full_name: str) -> str:
    """Extract candidate initials for the corner monogram watermark."""
    parts = [p.strip() for p in (full_name or "").split() if p.strip()]
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    elif len(parts) == 1 and parts[0]:
        return parts[0][:2].upper()
    return "CV"


def _aurelian_executive_pdf(resume: TailoredResume) -> bytes:
    """
    Renders the luxury editorial 'Aurelian Executive' CV layout:
    - 36% Left Sidebar in Warm Ivory/Cream (#FAF7F2) with fine hairline border (#E5E0D8)
    - Monogram watermark in top-right of sidebar
    - Candidate avatar with double concentric refined frames (inner bronze ring, outer hairline ring)
    - Candidate Name in elegant serif with small-caps bronze eyebrow and divider
    - Numbered sidebar section headers (01 Contact, 02 Profile, 03 Expertise, 04 Languages)
    - Skills rendered with 5-dot bronze rating indicators
    - Right main column with Roman numeral serif headers (I. Education, II. Experience, III. Projects, IV. Certifications)
    - Delicate hairline timeline with hollow bronze node dots
    - Bottom executive signature styling with candidate name & date
    """
    _sanitize_pdf_data(resume)
    _sync_resume_social_links(resume)

    PAGE_W, PAGE_H = A4  # 595.28 x 841.89 pt
    SIDE_W = 214.0       # 36% of page width
    SIDE_PAD = 18.0
    SIDE_MAX_W = SIDE_W - (SIDE_PAD * 2)  # 178 pt

    # Luxury Bronze & Ink Palette
    bronze_hex = "#B8935A"
    if resume.custom_accent_color and resume.custom_accent_color.lower() not in ("#000000", "#ffffff"):
        bronze_hex = resume.custom_accent_color
    bronze_color = colors.HexColor(bronze_hex)

    sidebar_bg = colors.HexColor("#FAF7F2")      # Luxury Warm Ivory / Cream
    hairline_color = colors.HexColor("#E5E0D8")  # Warm soft beige border
    hairline_soft = colors.HexColor("#F0ECE5")
    ink_primary = colors.HexColor("#0F0F0F")
    ink_soft = colors.HexColor("#2A2A2A")
    ink_muted = colors.HexColor("#6B6B6B")
    ink_light = colors.HexColor("#9A9A9A")

    f_reg, f_bold, f_italic = _get_font_names(getattr(resume, "font_family", "Helvetica"))

    # Font size scaling
    font_scale = getattr(resume, "font_size_scale", "standard") or "standard"
    if font_scale == "compact":
        body_size, body_leading, name_size = 8.0, 11.2, 19.0
        spacer_h = 3.5
    elif font_scale == "large":
        body_size, body_leading, name_size = 9.6, 13.5, 24.0
        spacer_h = 6.0
    elif font_scale == "spacious":
        body_size, body_leading, name_size = 10.2, 14.5, 26.0
        spacer_h = 7.0
    else:
        body_size, body_leading, name_size = 8.8, 12.4, 21.5
        spacer_h = 4.8

    # Platypus Styles for Right Main Column
    S = getSampleStyleSheet()

    _add(S, ParagraphStyle("AuJobTitle", fontName="Times-Bold", fontSize=body_size + 1.8, leading=body_leading + 2.0, textColor=ink_primary, spaceAfter=1))
    _add(S, ParagraphStyle("AuCompany", fontName="Times-Italic", fontSize=body_size + 0.4, leading=body_leading + 0.6, textColor=ink_muted, spaceAfter=3))
    _add(S, ParagraphStyle("AuDate", fontName=f_bold, fontSize=body_size - 1.0, leading=body_leading, textColor=bronze_color, alignment=TA_RIGHT))
    _add(S, ParagraphStyle("AuBody", fontName=f_reg, fontSize=body_size, leading=body_leading + 1.5, textColor=ink_soft, spaceAfter=3))
    _add(S, ParagraphStyle("AuBullet", fontName=f_reg, fontSize=body_size, leading=body_leading + 1.2, textColor=ink_soft, leftIndent=9, firstLineIndent=-7, spaceAfter=2.5))
    _add(S, ParagraphStyle("AuProjTitle", fontName="Times-Bold", fontSize=body_size + 1.5, leading=body_leading + 1.8, textColor=ink_primary, spaceAfter=1))
    _add(S, ParagraphStyle("AuProjSub", fontName="Times-Italic", fontSize=body_size - 0.2, leading=body_leading, textColor=bronze_color, spaceAfter=2))

    # Styles for Left Sidebar
    _add(S, ParagraphStyle("AuEyebrow", fontName=f_bold, fontSize=7.2, leading=9.0, textColor=bronze_color, alignment=TA_CENTER, spaceAfter=4))
    _add(S, ParagraphStyle("AuSideName", fontName="Times-Bold", fontSize=name_size, leading=name_size + 2.5, textColor=ink_primary, alignment=TA_CENTER, spaceAfter=3))
    _add(S, ParagraphStyle("AuSideRole", fontName=f_bold, fontSize=8.5, leading=11.5, textColor=ink_muted, alignment=TA_CENTER, spaceAfter=6))
    _add(S, ParagraphStyle("AuSideContact", fontName=f_reg, fontSize=7.6, leading=10.8, textColor=ink_soft))
    _add(S, ParagraphStyle("AuSideAbout", fontName=f_reg, fontSize=7.6, leading=11.6, textColor=ink_soft, spaceAfter=4))
    _add(S, ParagraphStyle("AuSideCat", fontName=f_bold, fontSize=6.8, leading=9.0, textColor=bronze_color, spaceAfter=2))

    MAIN_LEFT = SIDE_W + 22.0
    MAIN_MAX_W = PAGE_W - MAIN_LEFT - 22.0

    rendered_skills_state = {"cat_idx": 0, "skill_idx": 0}

    info = resume.personal_info
    monogram = _extract_monogram(info.full_name)

    # PAGE 1 BACKGROUND & SIDEBAR
    def on_first_page(canvas, doc):
        canvas.saveState()

        # 1. Main Column Background (White)
        canvas.setFillColor(colors.white)
        canvas.rect(SIDE_W, 0, PAGE_W - SIDE_W, PAGE_H, fill=1, stroke=0)

        # 2. Sidebar Background (#FAF7F2 Warm Ivory)
        canvas.setFillColor(sidebar_bg)
        canvas.rect(0, 0, SIDE_W, PAGE_H, fill=1, stroke=0)

        # 3. Fine Hairline Right Border on Sidebar
        canvas.setStrokeColor(hairline_color)
        canvas.setLineWidth(1.0)
        canvas.line(SIDE_W, 0, SIDE_W, PAGE_H)

        # 4. Monogram Watermark in Top-Right of Sidebar
        canvas.setFillColor(bronze_color)
        canvas.setFont("Times-Italic", 13.0)
        canvas.drawRightString(SIDE_W - 20.0, PAGE_H - 34.0, monogram)

        # 5. Candidate Photo with Refined Double Frame
        photo_size = 82.0
        photo_x = (SIDE_W - photo_size) / 2.0
        photo_y = PAGE_H - 126.0
        radius = photo_size / 2.0
        cx = photo_x + radius
        cy = photo_y + radius

        # Outer delicate ring
        canvas.setStrokeColor(hairline_color)
        canvas.setLineWidth(0.8)
        canvas.circle(cx, cy, radius + 8.5, stroke=1, fill=0)

        # Inner refined bronze ring
        canvas.setStrokeColor(bronze_color)
        canvas.setLineWidth(1.0)
        canvas.circle(cx, cy, radius + 4.5, stroke=1, fill=0)

        has_photo = bool(getattr(resume, "show_photo", True) and info.avatar_url and info.avatar_url.strip())
        img_drawn = False
        if has_photo:
            img_bytes = _load_avatar_image(info.avatar_url)
            if img_bytes:
                try:
                    canvas.saveState()
                    cp = canvas.beginPath()
                    cp.circle(cx, cy, radius)
                    canvas.clipPath(cp, stroke=0)
                    reader = ImageReader(img_bytes)
                    canvas.drawImage(reader, photo_x, photo_y, width=photo_size, height=photo_size, preserveAspectRatio=True)
                    canvas.restoreState()
                    # Soft white border
                    canvas.setStrokeColor(colors.white)
                    canvas.setLineWidth(2.0)
                    canvas.circle(cx, cy, radius, stroke=1, fill=0)
                    img_drawn = True
                except Exception:
                    img_drawn = False

        if not img_drawn:
            # Monogram avatar fallback
            canvas.setFillColor(colors.HexColor("#EFEBE4"))
            canvas.circle(cx, cy, radius, fill=1, stroke=0)
            canvas.setStrokeColor(colors.white)
            canvas.setLineWidth(2.0)
            canvas.circle(cx, cy, radius, stroke=1, fill=0)

            canvas.setFillColor(bronze_color)
            canvas.setFont("Times-Italic", 22.0)
            canvas.drawCentredString(cx, cy - 7, monogram)

        y = photo_y - 14.0

        # 6. NAME BLOCK (Centered in Left Sidebar - Page 1 Only)
        y -= _draw_sidebar_para(canvas, "CURRICULUM VITAE", S["AuEyebrow"], SIDE_PAD, y, SIDE_MAX_W)
        y -= 1.0

        full_name = info.full_name or "Candidate Name"
        y -= _draw_sidebar_para(canvas, full_name, S["AuSideName"], SIDE_PAD, y, SIDE_MAX_W)
        y -= 1.0

        if resume.target_job_title:
            y -= _draw_sidebar_para(canvas, resume.target_job_title.upper(), S["AuSideRole"], SIDE_PAD, y, SIDE_MAX_W)
            y -= 2.0

        # Elegant centered bronze divider line
        canvas.setStrokeColor(bronze_color)
        canvas.setLineWidth(1.0)
        canvas.line(cx - 16.0, y, cx + 16.0, y)
        y -= 12.0

        # 7. SECTION 01: CONTACT
        y -= _draw_aurelian_sidebar_header(canvas, "01", "Contact", bronze_color, hairline_color, SIDE_PAD, y, SIDE_MAX_W, f_bold, f_reg)
        contacts = []
        if info.phone:     contacts.append(("phone", info.phone))
        if info.email:     contacts.append(("email", info.email))
        if info.location:  contacts.append(("location", info.location))
        if info.linkedin:  contacts.append(("linkedin", info.linkedin.replace("https://www.", "").replace("https://", "")))
        if info.portfolio: contacts.append(("portfolio", info.portfolio.replace("https://www.", "").replace("https://", "")))
        if info.github:    contacts.append(("github", info.github.replace("https://www.", "").replace("https://", "")))

        for c_type, c_text in contacts:
            if y < 70: break
            # Small bronze bullet dot
            canvas.setFillColor(bronze_color)
            canvas.circle(SIDE_PAD + 2.0, y - 5.5, 1.4, fill=1, stroke=0)
            y -= _draw_sidebar_para(canvas, c_text, S["AuSideContact"], SIDE_PAD + 8.0, y, SIDE_MAX_W - 8.0)
            y -= 2.5

        y -= 8.0

        # 8. SECTION 02: PROFILE
        if resume.show_summary and resume.professional_summary and y > 150:
            y -= _draw_aurelian_sidebar_header(canvas, "02", "Profile", bronze_color, hairline_color, SIDE_PAD, y, SIDE_MAX_W, f_bold, f_reg)
            y -= _draw_sidebar_para(canvas, resume.professional_summary, S["AuSideAbout"], SIDE_PAD, y, SIDE_MAX_W)
            y -= 8.0

        # 9. SECTION 03: EXPERTISE (Skills with Dot Ratings)
        if resume.show_skills and resume.skill_categories and y > 60:
            y -= _draw_aurelian_sidebar_header(canvas, "03", "Expertise", bronze_color, hairline_color, SIDE_PAD, y, SIDE_MAX_W, f_bold, f_reg)

            completed_all = True
            for cat_idx in range(len(resume.skill_categories)):
                cat = resume.skill_categories[cat_idx]
                if y < 45:
                    completed_all = False
                    rendered_skills_state["cat_idx"] = cat_idx
                    rendered_skills_state["skill_idx"] = 0
                    break

                if cat.category_name and len(resume.skill_categories) > 1:
                    y -= _draw_sidebar_para(canvas, cat.category_name.upper(), S["AuSideCat"], SIDE_PAD, y, SIDE_MAX_W)
                    y -= 2.0

                for s_idx in range(len(cat.skills)):
                    skill_name = cat.skills[s_idx]
                    if y < 35:
                        completed_all = False
                        rendered_skills_state["cat_idx"] = cat_idx
                        rendered_skills_state["skill_idx"] = s_idx
                        break

                    level = cat.skill_levels.get(skill_name, 80) if cat.skill_levels else 80
                    y -= _draw_aurelian_skill_dots(canvas, skill_name, level, bronze_color, hairline_color, SIDE_PAD, y, SIDE_MAX_W, f_reg, 7.8)

            if completed_all:
                rendered_skills_state["cat_idx"] = 9999

        # Continuous vertical timeline line in right main column
        canvas.setStrokeColor(hairline_color)
        canvas.setLineWidth(1.0)
        canvas.line(MAIN_LEFT + 9.0, 50.0, MAIN_LEFT + 9.0, PAGE_H - 45.0)

        # Watermark
        if getattr(resume, "watermark", False):
            _draw_diagonal_watermark(canvas, PAGE_W, PAGE_H)
        canvas.restoreState()

    # LATER PAGES BACKGROUND & SIDEBAR
    def on_later_pages(canvas, doc):
        canvas.saveState()

        # 1. Main Column Background (White)
        canvas.setFillColor(colors.white)
        canvas.rect(SIDE_W, 0, PAGE_W - SIDE_W, PAGE_H, fill=1, stroke=0)

        # 2. Sidebar Background
        canvas.setFillColor(sidebar_bg)
        canvas.rect(0, 0, SIDE_W, PAGE_H, fill=1, stroke=0)

        # 3. Fine Hairline Border
        canvas.setStrokeColor(hairline_color)
        canvas.setLineWidth(1.0)
        canvas.line(SIDE_W, 0, SIDE_W, PAGE_H)

        # 4. Continuation Monogram & Header
        canvas.setFillColor(bronze_color)
        canvas.setFont("Times-Italic", 13.0)
        canvas.drawRightString(SIDE_W - 20.0, PAGE_H - 34.0, monogram)

        full_name = info.full_name or "Candidate Name"
        canvas.setFont("Times-Bold", 10.5)
        canvas.setFillColor(ink_primary)
        canvas.drawCentredString(SIDE_W / 2.0, PAGE_H - 42.0, full_name)

        canvas.setFont(f_bold, 7.0)
        canvas.setFillColor(bronze_color)
        canvas.drawCentredString(SIDE_W / 2.0, PAGE_H - 53.0, f"CURRICULUM VITAE · PAGE {doc.page}")

        canvas.setStrokeColor(hairline_color)
        canvas.setLineWidth(0.8)
        canvas.line(SIDE_PAD, PAGE_H - 62.0, SIDE_W - SIDE_PAD, PAGE_H - 62.0)

        y = PAGE_H - 78.0

        # Remaining Skills Continuation
        cat_start = rendered_skills_state["cat_idx"]
        if cat_start < len(resume.skill_categories):
            y -= _draw_aurelian_sidebar_header(canvas, "03", "Expertise (Cont.)", bronze_color, hairline_color, SIDE_PAD, y, SIDE_MAX_W, f_bold, f_reg)
            for c_idx in range(cat_start, len(resume.skill_categories)):
                cat = resume.skill_categories[c_idx]
                if y < 45: break

                s_start = rendered_skills_state["skill_idx"] if c_idx == cat_start else 0
                for s_idx in range(s_start, len(cat.skills)):
                    if y < 35: break
                    skill_name = cat.skills[s_idx]
                    level = cat.skill_levels.get(skill_name, 80) if cat.skill_levels else 80
                    y -= _draw_aurelian_skill_dots(canvas, skill_name, level, bronze_color, hairline_color, SIDE_PAD, y, SIDE_MAX_W, f_reg, 7.8)

        # Continuous vertical timeline line in right main column
        canvas.setStrokeColor(hairline_color)
        canvas.setLineWidth(1.0)
        canvas.line(MAIN_LEFT + 9.0, 50.0, MAIN_LEFT + 9.0, PAGE_H - 45.0)

        # Watermark
        if getattr(resume, "watermark", False):
            _draw_diagonal_watermark(canvas, PAGE_W, PAGE_H)
        canvas.restoreState()

    # RIGHT COLUMN FLOWABLE BUILDER
    body = []

    def make_main_header(roman_num: str, title: str):
        flow = []
        flow.append(Spacer(1, spacer_h * 0.4))

        # Title row with Roman Numeral in bronze italic serif and hairline divider
        h_table = Table(
            [[
                Paragraph(f"<font color='{bronze_hex}' size='{body_size + 6.0}'><i>{roman_num}</i></font>&nbsp;&nbsp;<font color='#0F0F0F' size='{body_size + 4.0}'><b>{title}</b></font>", S["AuJobTitle"])
            ]],
            colWidths=[MAIN_MAX_W]
        )
        h_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, -1), 0.8, hairline_color),
        ]))
        flow.append(h_table)
        flow.append(Spacer(1, spacer_h * 0.8))
        return flow

    # SECTION I: EDUCATION
    section_counter = 1
    romans = ["I.", "II.", "III.", "IV.", "V.", "VI."]

    def add_education():
        nonlocal section_counter
        if resume.show_education and resume.education:
            r_num = romans[min(section_counter - 1, len(romans) - 1)]
            section_counter += 1
            body.extend(make_main_header(r_num, "Education"))

            for edu in resume.education:
                e_flow = []
                date_str = edu.graduation_year or ""
                if not date_str and (edu.start_date or edu.end_date):
                    date_str = f"{edu.start_date or ''} — {edu.end_date or ''}".strip(" —")

                header_tbl = Table(
                    [[
                        AurelianTimelineDot(dot_color=bronze_color),
                        Paragraph(f"<b>{edu.degree}</b>", S["AuJobTitle"]),
                        Paragraph(date_str, S["AuDate"]),
                    ]],
                    colWidths=[18, MAIN_MAX_W - 108, 90]
                )
                header_tbl.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                ]))
                e_flow.append(header_tbl)

                sub_tbl = Table(
                    [[
                        Spacer(1, 1),
                        Paragraph(f"<i>{edu.institution}</i>", S["AuCompany"]),
                    ]],
                    colWidths=[18, MAIN_MAX_W - 18]
                )
                sub_tbl.setStyle(TableStyle([
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ]))
                e_flow.append(sub_tbl)

                if edu.details:
                    desc_tbl = Table(
                        [[
                            Spacer(1, 1),
                            Paragraph(edu.details, S["AuBody"]),
                        ]],
                        colWidths=[18, MAIN_MAX_W - 18]
                    )
                    desc_tbl.setStyle(TableStyle([
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ]))
                    e_flow.append(desc_tbl)

                e_flow.append(Spacer(1, 5))
                body.append(KeepTogether(e_flow))

            body.append(Spacer(1, spacer_h * 0.5))

    # SECTION II: WORK EXPERIENCE
    def add_experience():
        nonlocal section_counter
        if resume.show_experience and resume.work_experience:
            r_num = romans[min(section_counter - 1, len(romans) - 1)]
            section_counter += 1
            body.extend(make_main_header(r_num, "Experience"))

            for job in resume.work_experience:
                j_flow = []
                date_str = f"{job.start_date} — {job.end_date}" if job.start_date and job.end_date else (job.start_date or job.end_date or "")

                header_tbl = Table(
                    [[
                        AurelianTimelineDot(dot_color=bronze_color),
                        Paragraph(f"<b>{job.job_title}</b>", S["AuJobTitle"]),
                        Paragraph(date_str, S["AuDate"]),
                    ]],
                    colWidths=[18, MAIN_MAX_W - 108, 90]
                )
                header_tbl.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                ]))
                j_flow.append(header_tbl)

                comp_loc = job.company
                if job.location:
                    comp_loc += f" &middot; {job.location}"

                sub_tbl = Table(
                    [[
                        Spacer(1, 1),
                        Paragraph(f"<i>{comp_loc}</i>", S["AuCompany"]),
                    ]],
                    colWidths=[18, MAIN_MAX_W - 18]
                )
                sub_tbl.setStyle(TableStyle([
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ]))
                j_flow.append(sub_tbl)

                if job.bullet_points:
                    for b in job.bullet_points:
                        b_tbl = Table(
                            [[
                                Spacer(1, 1),
                                Paragraph(f"• {b.lstrip('•- ')}", S["AuBullet"]),
                            ]],
                            colWidths=[18, MAIN_MAX_W - 18]
                        )
                        b_tbl.setStyle(TableStyle([
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                        ]))
                        j_flow.append(b_tbl)

                j_flow.append(Spacer(1, 6))
                body.append(KeepTogether(j_flow))

            body.append(Spacer(1, spacer_h * 0.5))

    # SECTION III: KEY PROJECTS
    def add_projects():
        nonlocal section_counter
        if resume.show_projects and resume.projects:
            r_num = romans[min(section_counter - 1, len(romans) - 1)]
            section_counter += 1
            body.extend(make_main_header(r_num, "Key Projects"))

            for proj in resume.projects:
                p_flow = []
                p_head_tbl = Table(
                    [[
                        AurelianTimelineDot(dot_color=bronze_color),
                        Paragraph(f"<b>{proj.name}</b>", S["AuProjTitle"]),
                    ]],
                    colWidths=[18, MAIN_MAX_W - 18]
                )
                p_head_tbl.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                ]))
                p_flow.append(p_head_tbl)

                if proj.technologies:
                    tech_str = " &middot; ".join(proj.technologies)
                    t_tbl = Table(
                        [[
                            Spacer(1, 1),
                            Paragraph(f"<i>Technologies: {tech_str}</i>", S["AuProjSub"]),
                        ]],
                        colWidths=[18, MAIN_MAX_W - 18]
                    )
                    t_tbl.setStyle(TableStyle([
                        ('LEFTPADDING', (0, 0), (-1, -1), 0),
                        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                    ]))
                    p_flow.append(t_tbl)

                if hasattr(proj, "description_bullets") and proj.description_bullets:
                    for b in proj.description_bullets:
                        b_tbl = Table(
                            [[
                                Spacer(1, 1),
                                Paragraph(f"• {b.lstrip('•- ')}", S["AuBullet"]),
                            ]],
                            colWidths=[18, MAIN_MAX_W - 18]
                        )
                        b_tbl.setStyle(TableStyle([
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                        ]))
                        p_flow.append(b_tbl)

                p_flow.append(Spacer(1, 5))
                body.append(KeepTogether(p_flow))

            body.append(Spacer(1, spacer_h * 0.5))

    # SECTION IV: CERTIFICATIONS & LICENSES
    def add_certifications():
        nonlocal section_counter
        if resume.show_certifications and resume.certifications:
            r_num = romans[min(section_counter - 1, len(romans) - 1)]
            section_counter += 1
            body.extend(make_main_header(r_num, "Certifications & Credentials"))

            cert_flow = []
            for cert in resume.certifications:
                year_str = f" <font color='{bronze_hex}' size='7.5'>({cert.year})</font>" if cert.year else ""
                c_tbl = Table(
                    [[
                        AurelianTimelineDot(dot_color=bronze_color),
                        Paragraph(f"<b>{cert.name}</b> — <i>{cert.issuer}</i>{year_str}", S["AuJobTitle"]),
                    ]],
                    colWidths=[18, MAIN_MAX_W - 18]
                )
                c_tbl.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (-1, -1), 0),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                    ('TOPPADDING', (0, 0), (-1, -1), 0),
                ]))
                cert_flow.append(c_tbl)
                cert_flow.append(Spacer(1, 2))

            body.append(KeepTogether(cert_flow))
            body.append(Spacer(1, spacer_h * 0.5))

    # Build sequence
    add_education()
    add_experience()
    add_projects()
    add_certifications()

    # Signature line at bottom of document
    cur_year = datetime.datetime.now().year
    full_name = info.full_name or "Candidate Name"
    sig_flow = []
    sig_flow.append(Spacer(1, spacer_h * 1.5))
    sig_table = Table(
        [[
            Paragraph(f"<i>{full_name}</i>", ParagraphStyle("AuSigName", fontName="Times-Italic", fontSize=15.0, leading=18.0, textColor=ink_primary)),
            Paragraph(f"CURRICULUM VITAE &middot; {cur_year}", ParagraphStyle("AuSigTag", fontName=f_bold, fontSize=7.5, leading=10.0, textColor=bronze_color, alignment=TA_RIGHT)),
        ]],
        colWidths=[MAIN_MAX_W * 0.6, MAIN_MAX_W * 0.4]
    )
    sig_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), 0.8, hairline_color),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    sig_flow.append(sig_table)
    body.append(KeepTogether(sig_flow))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MAIN_LEFT,
        rightMargin=22,
        topMargin=36,
        bottomMargin=24
    )
    doc.build(body, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buf.seek(0)
    return buf.getvalue()
