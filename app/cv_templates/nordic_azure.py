"""
Nordic Azure CV Template:
- Inspired by modern Scandinavian / Nordic minimalist aesthetic (Lorna Alvarado Marketing style)
- 34% Light Gray (#F2F2F2) left sidebar with signature diagonal Steel Blue (#5B8FC7) top-left triangle
- Circular candidate avatar overlapping the diagonal cut with 5pt solid white border
- Candidate Name & Role styled in Steel Blue & slate inside the left sidebar
- Contact, About Me, and Technical Skills in the left column with clean blue underlines
- Education, Work Experience, Key Projects & Certifications in the right column
- Continuous Steel Blue vertical timeline with circular node dots
"""
import io
import os
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


class NordicSectionIcon(Flowable):
    """
    Renders a minimalist vector icon for section headings.
    Matches the clean stroke/fill style of the Nordic design.
    """
    def __init__(self, icon_type: str = "education", icon_color=colors.HexColor("#3A3A3A"), size: float = 16.0):
        super().__init__()
        self.icon_type = icon_type.lower()
        self.icon_color = icon_color
        self.size = size
        self.width = size
        self.height = size

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        c.saveState()
        cx = self.size / 2.0
        cy = self.size / 2.0

        c.setFillColor(self.icon_color)
        c.setStrokeColor(self.icon_color)
        c.setLineWidth(1.2)

        itype = self.icon_type
        if itype in ("education", "school", "grad"):
            p = c.beginPath()
            p.moveTo(cx, cy + 4.5)
            p.lineTo(cx + 6.0, cy + 1.5)
            p.lineTo(cx, cy - 1.5)
            p.lineTo(cx - 6.0, cy + 1.5)
            p.close()
            c.drawPath(p, fill=1, stroke=0)
            c.line(cx - 3.5, cy + 0.2, cx - 3.5, cy - 3.5)
            c.arc(cx - 3.5, cy - 5.0, cx + 3.5, cy + 0.5, 200, 140)
        elif itype in ("experience", "work", "briefcase"):
            c.roundRect(cx - 5.5, cy - 4.5, 11, 8.0, 1.2, fill=0, stroke=1)
            c.rect(cx - 2.5, cy + 3.5, 5, 2.0, fill=0, stroke=1)
            c.line(cx - 5.5, cy + 0.5, cx + 5.5, cy + 0.5)
        elif itype in ("projects", "references", "folder"):
            # Open book / references icon
            c.roundRect(cx - 6.0, cy - 5.0, 12, 10.0, 1.2, fill=0, stroke=1)
            c.line(cx, cy - 5.0, cx, cy + 5.0)
            c.line(cx - 4.0, cy + 1.5, cx - 1.5, cy + 1.5)
            c.line(cx + 1.5, cy + 1.5, cx + 4.0, cy + 1.5)
            c.line(cx - 4.0, cy - 1.5, cx - 1.5, cy - 1.5)
            c.line(cx + 1.5, cy - 1.5, cx + 4.0, cy - 1.5)
        elif itype in ("about", "user", "profile"):
            c.circle(cx, cy + 2.5, 3.0, fill=1, stroke=0)
            p = c.beginPath()
            p.arc(cx - 5.5, cy - 7.0, cx + 5.5, cy + 2.0, 0, 180)
            c.drawPath(p, fill=1, stroke=0)
        elif itype in ("contact", "phone"):
            c.roundRect(cx - 3.5, cy - 5.5, 7, 11, 1.5, fill=0, stroke=1)
            c.circle(cx, cy - 3.5, 0.7, fill=1, stroke=0)
        elif itype in ("skills", "tools"):
            c.circle(cx - 2.5, cy + 2.5, 1.5, fill=1, stroke=0)
            c.circle(cx + 2.5, cy + 2.5, 1.5, fill=1, stroke=0)
            c.circle(cx - 2.5, cy - 2.5, 1.5, fill=1, stroke=0)
            c.circle(cx + 2.5, cy - 2.5, 1.5, fill=1, stroke=0)
        elif itype in ("certifications", "award"):
            c.circle(cx, cy + 1.5, 3.8, fill=0, stroke=1)
            c.line(cx - 2.5, cy - 1.5, cx - 4.0, cy - 5.5)
            c.line(cx + 2.5, cy - 1.5, cx + 4.0, cy - 5.5)
        else:
            c.circle(cx, cy, 3.0, fill=1, stroke=0)

        c.restoreState()


class NordicTimelineDot(Flowable):
    """
    Renders the circular node dot on the left of each experience and education item.
    The vertical timeline line passes through x=12.
    """
    def __init__(self, dot_color=colors.HexColor("#5B8FC7"), ring_color=colors.white, radius: float = 3.6):
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
        x = 12.0
        y = 7.0
        # White background ring halo
        c.setFillColor(self.ring_color)
        c.circle(x, y, self.radius + 1.8, fill=1, stroke=0)
        # Inner Steel Blue node dot
        c.setFillColor(self.dot_color)
        c.circle(x, y, self.radius, fill=1, stroke=0)
        c.restoreState()


def _draw_nordic_sidebar_header(canvas, title: str, icon_type: str, blue_color, x: float, y_top: float, max_w: float, font_bold: str) -> float:
    """
    Draws a section title in the sidebar with an icon and a solid blue underline.
    Returns total vertical height consumed.
    """
    canvas.saveState()
    cx = x + 7.0
    cy = y_top - 7.0

    canvas.setFillColor(colors.HexColor("#3A3A3A"))
    canvas.setStrokeColor(colors.HexColor("#3A3A3A"))
    canvas.setLineWidth(1.2)

    itype = icon_type.lower()
    if itype in ("contact", "phone"):
        canvas.roundRect(cx - 3.0, cy - 5.0, 6, 10, 1.2, fill=0, stroke=1)
        canvas.circle(cx, cy - 3.2, 0.6, fill=1, stroke=0)
    elif itype in ("about", "user", "profile"):
        canvas.circle(cx, cy + 2.0, 2.8, fill=1, stroke=0)
        p = canvas.beginPath()
        p.arc(cx - 5.0, cy - 6.5, cx + 5.0, cy + 1.5, 0, 180)
        canvas.drawPath(p, fill=1, stroke=0)
    elif itype in ("skills", "tools"):
        canvas.circle(cx - 2.2, cy + 2.2, 1.3, fill=1, stroke=0)
        canvas.circle(cx + 2.2, cy + 2.2, 1.3, fill=1, stroke=0)
        canvas.circle(cx - 2.2, cy - 2.2, 1.3, fill=1, stroke=0)
        canvas.circle(cx + 2.2, cy - 2.2, 1.3, fill=1, stroke=0)
    else:
        canvas.circle(cx, cy, 2.8, fill=1, stroke=0)

    # Title text
    canvas.setFont(font_bold, 10.5)
    canvas.setFillColor(colors.HexColor("#3A3A3A"))
    canvas.drawString(x + 18.0, cy - 3.5, title)

    # Underline in Steel Blue
    line_y = y_top - 18.0
    canvas.setStrokeColor(blue_color)
    canvas.setLineWidth(1.4)
    canvas.line(x, line_y, x + max_w, line_y)

    canvas.restoreState()
    return 24.0


def _nordic_azure_pdf(resume: TailoredResume) -> bytes:
    """
    Renders the modern 'Nordic Azure' CV layout:
    - 34% Left Sidebar in Scandinavian Light Gray (#F2F2F2)
    - Signature diagonal Steel Blue (#5B8FC7) triangle in top-left
    - Circular candidate avatar overlapping the diagonal cut with 5pt solid white border
    - Candidate Name & Role in Left Sidebar (Page 1 Only!)
    - Contact, About Me & Skills with progress bars in the left column
    - Education, Experience, Projects & Certifications in the right column
    - Continuous Steel Blue vertical timeline with node dots
    """
    _sanitize_pdf_data(resume)
    _sync_resume_social_links(resume)

    PAGE_W, PAGE_H = A4  # 595.28 x 841.89 pt
    SIDE_W = 202.0       # 34% of page width
    SIDE_PAD = 18.0
    SIDE_MAX_W = SIDE_W - (SIDE_PAD * 2)  # 166 pt
    TRIANGLE_H = 210.0

    # Color Palette
    blue_hex = "#5B8FC7"
    if resume.custom_accent_color and resume.custom_accent_color.lower() not in ("#000000", "#ffffff"):
        blue_hex = resume.custom_accent_color
    blue_color = colors.HexColor(blue_hex)

    sidebar_bg = colors.HexColor("#F2F2F2")
    text_dark = colors.HexColor("#2D2D2D")
    text_gray = colors.HexColor("#6B6B6B")
    text_muted = colors.HexColor("#7A7A7A")
    body_text_color = colors.HexColor("#4A4A4A")

    f_reg, f_bold, f_italic = _get_font_names(getattr(resume, "font_family", "Helvetica"))
    font_scale = getattr(resume, "font_size_scale", "standard") or "standard"

    if font_scale == "compact":
        body_size, body_leading, name_size = 8.2, 11.5, 22.0
        spacer_h = 3.5
    elif font_scale == "large":
        body_size, body_leading, name_size = 9.8, 13.8, 26.0
        spacer_h = 6.0
    elif font_scale == "spacious":
        body_size, body_leading, name_size = 10.5, 14.8, 28.0
        spacer_h = 7.0
    else:
        body_size, body_leading, name_size = 9.0, 12.8, 24.0
        spacer_h = 4.8

    # Platypus Styles for Right Main Column
    S = getSampleStyleSheet()
    _add(S, ParagraphStyle("NaSecTitle", fontName=f_bold, fontSize=11.5, leading=14.5, textColor=colors.HexColor("#3A3A3A")))
    _add(S, ParagraphStyle("NaJobTitle", fontName=f_bold, fontSize=body_size + 0.8, leading=body_leading + 1.2, textColor=text_dark))
    _add(S, ParagraphStyle("NaJobCompany", fontName=f_italic, fontSize=body_size - 0.2, leading=body_leading, textColor=text_gray, spaceAfter=2))
    _add(S, ParagraphStyle("NaBullet", fontName=f_reg, fontSize=body_size - 0.2, leading=body_leading, textColor=body_text_color, leftIndent=8, firstLineIndent=-6, spaceAfter=2))
    _add(S, ParagraphStyle("NaProjTitle", fontName=f_bold, fontSize=body_size + 0.6, leading=body_leading + 1, textColor=text_dark))
    _add(S, ParagraphStyle("NaProjSub", fontName=f_reg, fontSize=body_size - 0.4, leading=body_leading, textColor=text_muted, spaceAfter=2))

    # Styles for Left Sidebar Text
    _add(S, ParagraphStyle("NaSideName", fontName=f_reg, fontSize=name_size, leading=name_size + 3.0, textColor=blue_color, spaceAfter=3))
    _add(S, ParagraphStyle("NaSideRole", fontName=f_reg, fontSize=11.0, leading=14.0, textColor=colors.HexColor("#5A5A5A"), spaceAfter=14))
    _add(S, ParagraphStyle("NaSideContact", fontName=f_reg, fontSize=7.6, leading=10.8, textColor=body_text_color))
    _add(S, ParagraphStyle("NaSideAbout", fontName=f_reg, fontSize=7.8, leading=11.5, textColor=colors.HexColor("#555555"), spaceAfter=6))
    _add(S, ParagraphStyle("NaSideSkill", fontName=f_reg, fontSize=7.5, leading=10.2, textColor=body_text_color, leftIndent=7, firstLineIndent=-5, spaceAfter=2))
    _add(S, ParagraphStyle("NaSideCat", fontName=f_bold, fontSize=7.4, leading=9.5, textColor=colors.HexColor("#5A5A5A"), spaceAfter=2))

    # State tracking for multi-page skills continuation
    rendered_skills_state = {"cat_idx": 0, "skill_idx": 0}

    def on_first_page(canvas, doc):
        canvas.saveState()
        info = resume.personal_info

        # 1. Left Light Gray Sidebar Background
        canvas.setFillColor(sidebar_bg)
        canvas.rect(0, 0, SIDE_W, PAGE_H, fill=1, stroke=0)

        # 2. Diagonal Steel Blue Triangle in Top-Left
        canvas.setFillColor(blue_color)
        p = canvas.beginPath()
        p.moveTo(0, PAGE_H)
        p.lineTo(SIDE_W, PAGE_H)
        p.lineTo(0, PAGE_H - TRIANGLE_H)
        p.close()
        canvas.drawPath(p, fill=1, stroke=0)

        # 3. Avatar Overlapping the Diagonal Cut
        photo_size = 88.0
        photo_x = (SIDE_W - photo_size) / 2.0
        photo_y = PAGE_H - 125.0
        radius = photo_size / 2.0
        cx = photo_x + radius
        cy = photo_y + radius

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
                    # 5pt solid white circular border
                    canvas.setStrokeColor(colors.white)
                    canvas.setLineWidth(5.0)
                    canvas.circle(cx, cy, radius, stroke=1, fill=0)
                    img_drawn = True
                except Exception:
                    img_drawn = False

        if not img_drawn:
            # Monogram placeholder with white border
            canvas.setFillColor(colors.HexColor("#D8E3EF"))
            canvas.circle(cx, cy, radius, fill=1, stroke=0)
            canvas.setStrokeColor(colors.white)
            canvas.setLineWidth(5.0)
            canvas.circle(cx, cy, radius, stroke=1, fill=0)

            names = (info.full_name or "C").split()
            initials = "".join([n[0] for n in names[:2]]).upper()
            canvas.setFillColor(blue_color)
            canvas.setFont(f_bold, 24)
            canvas.drawCentredString(cx, cy - 8, initials)

        y = photo_y - 18.0

        # 4. CANDIDATE NAME & ROLE IN LEFT SIDEBAR (Page 1 Only!)
        full_name = info.full_name or "Candidate Name"
        y -= _draw_sidebar_para(canvas, full_name, S["NaSideName"], SIDE_PAD, y, SIDE_MAX_W)
        y -= 2.0
        if resume.target_job_title:
            y -= _draw_sidebar_para(canvas, resume.target_job_title, S["NaSideRole"], SIDE_PAD, y, SIDE_MAX_W)
            y -= 4.0

        # 5. CONTACT SECTION (Left Sidebar)
        y -= _draw_nordic_sidebar_header(canvas, "Contact", "contact", blue_color, SIDE_PAD, y, SIDE_MAX_W, f_bold)
        contacts = []
        if info.phone:     contacts.append(info.phone)
        if info.email:     contacts.append(info.email)
        if info.location:  contacts.append(info.location)
        if info.linkedin:  contacts.append(info.linkedin.replace("https://www.", "").replace("https://", ""))
        if info.portfolio: contacts.append(info.portfolio.replace("https://www.", "").replace("https://", ""))
        if info.github:    contacts.append(info.github.replace("https://www.", "").replace("https://", ""))

        for c_text in contacts:
            if y < 70: break
            y -= _draw_sidebar_para(canvas, c_text, S["NaSideContact"], SIDE_PAD, y, SIDE_MAX_W)
            y -= 3.5

        y -= 8.0

        # 6. ABOUT ME SECTION (Left Sidebar)
        if resume.show_summary and resume.professional_summary and y > 150:
            y -= _draw_nordic_sidebar_header(canvas, "About Me", "about", blue_color, SIDE_PAD, y, SIDE_MAX_W, f_bold)
            y -= _draw_sidebar_para(canvas, resume.professional_summary, S["NaSideAbout"], SIDE_PAD, y, SIDE_MAX_W)
            y -= 8.0

        # 7. SKILLS SECTION (Left Sidebar with Progress Bars)
        if resume.show_skills and resume.skill_categories and y > 60:
            y -= _draw_nordic_sidebar_header(canvas, "Skills", "skills", blue_color, SIDE_PAD, y, SIDE_MAX_W, f_bold)
            show_bars = getattr(resume, "show_skill_bars", True)
            bar_style = getattr(resume, "skill_bar_style", "sleek") or "sleek"

            bar_fill_color = blue_color
            bar_track_color = colors.HexColor("#D8D8D8")

            completed_all = True
            for cat_idx in range(len(resume.skill_categories)):
                cat = resume.skill_categories[cat_idx]
                if y < 45:
                    completed_all = False
                    rendered_skills_state["cat_idx"] = cat_idx
                    rendered_skills_state["skill_idx"] = 0
                    break

                if cat.category_name and len(resume.skill_categories) > 1:
                    y -= _draw_sidebar_para(canvas, cat.category_name.upper(), S["NaSideCat"], SIDE_PAD, y, SIDE_MAX_W)
                    y -= 2.0

                levels = getattr(cat, "skill_levels", {}) or {}
                skills_list = cat.skills or []
                cat_finished = True
                for s_idx in range(len(skills_list)):
                    s = skills_list[s_idx]
                    req_h = 19.0 if show_bars else 13.0
                    if y < 35 + req_h:
                        completed_all = False
                        cat_finished = False
                        rendered_skills_state["cat_idx"] = cat_idx
                        rendered_skills_state["skill_idx"] = s_idx
                        break

                    if show_bars:
                        s_level = levels.get(s, 85)
                        consumed = _draw_skill_progress_bar(
                            canvas, s, s_level, SIDE_PAD, y, SIDE_MAX_W,
                            style=bar_style, bar_color=bar_fill_color, bg_color=bar_track_color,
                            text_color=text_dark, pct_color=text_gray, font_name=f_reg
                        )
                        y -= (consumed + 3.0)
                    else:
                        y -= _draw_sidebar_para(canvas, f"• {s}", S["NaSideSkill"], SIDE_PAD + 2, y, SIDE_MAX_W - 2)
                        y -= 2.0

                if not cat_finished:
                    break

                y -= 4.0

            if completed_all:
                rendered_skills_state["cat_idx"] = len(resume.skill_categories)
                rendered_skills_state["skill_idx"] = 0

        # Page 1 Footer inside sidebar
        canvas.setFillColor(text_gray)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawCentredString(SIDE_W / 2.0, 14, "Page 1")

        if getattr(resume, "watermark", False):
            _draw_diagonal_watermark(canvas, PAGE_W, PAGE_H)

        canvas.restoreState()

    def on_later_pages(canvas, doc):
        canvas.saveState()

        # Left Light Gray Sidebar background continues cleanly
        # NO duplicate avatar circle, NO duplicate name/role block!
        canvas.setFillColor(sidebar_bg)
        canvas.rect(0, 0, SIDE_W, PAGE_H, fill=1, stroke=0)

        # Subtle top accent stripe on later pages
        canvas.setFillColor(blue_color)
        canvas.rect(0, PAGE_H - 4, SIDE_W, 4, fill=1, stroke=0)

        y = PAGE_H - 32.0

        # Overflow Skills if any
        if resume.show_skills and resume.skill_categories and rendered_skills_state["cat_idx"] < len(resume.skill_categories):
            y -= _draw_nordic_sidebar_header(canvas, "Skills (Cont.)", "skills", blue_color, SIDE_PAD, y, SIDE_MAX_W, f_bold)
            show_bars = getattr(resume, "show_skill_bars", True)
            bar_style = getattr(resume, "skill_bar_style", "sleek") or "sleek"

            bar_fill_color = blue_color
            bar_track_color = colors.HexColor("#D8D8D8")

            start_cat_idx = rendered_skills_state["cat_idx"]
            start_s_idx = rendered_skills_state["skill_idx"]

            for cat_idx in range(start_cat_idx, len(resume.skill_categories)):
                if y < 45: break
                cat = resume.skill_categories[cat_idx]
                s_from = start_s_idx if cat_idx == start_cat_idx else 0

                if cat.category_name and (len(resume.skill_categories) > 1 or s_from > 0):
                    cat_title = cat.category_name.upper()
                    if s_from > 0:
                        cat_title += " (CONT.)"
                    y -= _draw_sidebar_para(canvas, cat_title, S["NaSideCat"], SIDE_PAD, y, SIDE_MAX_W)
                    y -= 2.0

                levels = getattr(cat, "skill_levels", {}) or {}
                skills_list = cat.skills or []
                for s in skills_list[s_from:]:
                    req_h = 19.0 if show_bars else 13.0
                    if y < 35 + req_h: break

                    if show_bars:
                        s_level = levels.get(s, 85)
                        consumed = _draw_skill_progress_bar(
                            canvas, s, s_level, SIDE_PAD, y, SIDE_MAX_W,
                            style=bar_style, bar_color=bar_fill_color, bg_color=bar_track_color,
                            text_color=text_dark, pct_color=text_gray, font_name=f_reg
                        )
                        y -= (consumed + 3.0)
                    else:
                        y -= _draw_sidebar_para(canvas, f"• {s}", S["NaSideSkill"], SIDE_PAD + 2, y, SIDE_MAX_W - 2)
                        y -= 2.0

                y -= 4.0

        # Page N Footer inside sidebar
        canvas.setFillColor(text_gray)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawCentredString(SIDE_W / 2.0, 14, f"Page {doc.page}")

        # Top right subtle page header in main column
        canvas.setFillColor(text_muted)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(PAGE_W - 24, PAGE_H - 20, f"Page {doc.page}")
        canvas.setStrokeColor(colors.HexColor("#E0E0E0"))
        canvas.setLineWidth(0.5)
        canvas.line(SIDE_W + 24, PAGE_H - 24, PAGE_W - 24, PAGE_H - 24)

        if getattr(resume, "watermark", False):
            _draw_diagonal_watermark(canvas, PAGE_W, PAGE_H)

        canvas.restoreState()

    # RIGHT COLUMN FLOWABLES
    body = []
    CONTENT_W = PAGE_W - (SIDE_W + 24) - 24  # ~345 pt

    # Helper: Main Column Section Header with Icon & 1.5pt solid Steel Blue underline
    def make_main_header(title: str, icon_type: str) -> List:
        icon_flow = NordicSectionIcon(icon_type=icon_type, icon_color=colors.HexColor("#3A3A3A"), size=16.0)
        title_para = Paragraph(title, S["NaSecTitle"])
        hdr_table = Table([[icon_flow, title_para]], colWidths=[20, CONTENT_W - 20])
        hdr_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (1, 0), (1, 0), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        line_flow = HRFlowable(width="100%", thickness=1.4, color=blue_color, spaceBefore=2, spaceAfter=8)
        return [hdr_table, line_flow]

    # Section ordering for main column (Education, Experience, Projects, Certifications)
    # Note: Summary/About Me is already featured in the left sidebar!
    # 1. EDUCATION (Timeline with Steel Blue line & dots)
    def add_education():
        if resume.show_education and resume.education:
            body.extend(make_main_header("Education", "education"))

            edu_rows = []
            for edu in resume.education:
                dates = edu.graduation_year or (f"{edu.start_date} – {edu.end_date}" if (edu.start_date or edu.end_date) else "")
                loc_str = f" · {edu.location}" if edu.location else ""

                item_flowables = [
                    Paragraph(f"<b>{edu.degree}</b> <font color='#6B6B6B' size='7.5'>({dates})</font>", S["NaJobTitle"]),
                    Paragraph(f"{edu.institution}{loc_str}", S["NaJobCompany"]),
                ]
                if getattr(edu, "details", None) and str(edu.details).strip():
                    item_flowables.append(Paragraph(f"{edu.details}", S["NaBullet"]))

                dot = NordicTimelineDot(dot_color=blue_color, ring_color=colors.white, radius=3.5)
                edu_rows.append([dot, item_flowables])

            edu_table = Table(edu_rows, colWidths=[14, CONTENT_W - 14])
            edu_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (1, -1), 1.4, blue_color),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (1, 0), (1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            body.append(edu_table)
            body.append(Spacer(1, spacer_h * 0.6))

    # 2. WORK EXPERIENCE (Timeline with Steel Blue line & dots)
    def add_experience():
        if resume.show_experience and resume.work_experience:
            body.extend(make_main_header("Experience", "experience"))

            timeline_rows = []
            for exp in resume.work_experience:
                date_str = f"{exp.start_date} – {exp.end_date}"
                loc_str = f" · {exp.location}" if exp.location else ""

                item_flowables = [
                    Paragraph(f"<b>{exp.job_title}</b> <font color='#6B6B6B' size='7.5'>({date_str})</font>", S["NaJobTitle"]),
                    Paragraph(f"{exp.company}{loc_str}", S["NaJobCompany"]),
                ]
                for b in exp.bullet_points:
                    clean_b = b.lstrip("•- ")
                    item_flowables.append(Paragraph(f"• {clean_b}", S["NaBullet"]))

                dot = NordicTimelineDot(dot_color=blue_color, ring_color=colors.white, radius=3.5)
                timeline_rows.append([dot, item_flowables])

            timeline_table = Table(timeline_rows, colWidths=[14, CONTENT_W - 14])
            timeline_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (1, -1), 1.4, blue_color),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (1, 0), (1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            body.append(timeline_table)
            body.append(Spacer(1, spacer_h * 0.6))

    # 3. KEY PROJECTS / REFERENCES
    def add_projects():
        if resume.show_projects and resume.projects:
            body.extend(make_main_header("Projects & Work", "projects"))

            for proj in resume.projects:
                p_flow = []
                link_text = f" <font color='#6B6B6B' size='7.5'>({proj.link})</font>" if proj.link else ""
                p_flow.append(Paragraph(f"<b>{proj.name}</b>{link_text}", S["NaProjTitle"]))

                if proj.technologies:
                    tech_str = " · ".join(proj.technologies)
                    p_flow.append(Paragraph(f"<i>Technologies: {tech_str}</i>", S["NaProjSub"]))

                if hasattr(proj, "description_bullets") and proj.description_bullets:
                    for b in proj.description_bullets:
                        p_flow.append(Paragraph(f"• {b.lstrip('•- ')}", S["NaBullet"]))

                p_flow.append(Spacer(1, 4))
                body.append(KeepTogether(p_flow))

            body.append(Spacer(1, spacer_h * 0.5))

    # 4. CERTIFICATIONS
    def add_certifications():
        if resume.show_certifications and resume.certifications:
            body.extend(make_main_header("Certifications & Licenses", "certifications"))

            cert_flow = []
            for cert in resume.certifications:
                year_str = f" <font color='#6B6B6B' size='7.5'>({cert.year})</font>" if cert.year else ""
                cert_flow.append(Paragraph(f"• <b>{cert.name}</b> — {cert.issuer}{year_str}", S["NaJobTitle"]))
                cert_flow.append(Spacer(1, 2))

            body.append(KeepTogether(cert_flow))
            body.append(Spacer(1, spacer_h * 0.5))

    # Build sequence
    add_education()
    add_experience()
    add_projects()
    add_certifications()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=SIDE_W + 24,
        rightMargin=24,
        topMargin=36,
        bottomMargin=24
    )
    doc.build(body, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buf.seek(0)
    return buf.getvalue()
