"""
Navy Executive CV Template:
- Inspired by high-end modern corporate executive design (Lorna Alvarado style)
- 35% Deep Navy (#1B3A5C) architectural left column
- Circular candidate avatar photo with 4.5pt solid white border (or monogram)
- Circular white badge section headers for left sidebar (Contact, Education, Skills)
- Prominent bold uppercase candidate name & subtitle in main column
- Circular navy badge section headers in right column (About Me, Experience, Projects)
- Vertical timeline with continuous connecting line (#D0D5DC) and circular node dots
"""
import io
import os
from typing import Optional, List

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Flowable, Paragraph, Spacer, Table, TableStyle, SimpleDocTemplate, KeepTogether
)

from app.schemas import TailoredResume
from app.cv_templates.common import (
    _add, _hex_to_rgb, _load_avatar_image, _get_font_names,
    _draw_diagonal_watermark, _draw_sidebar_para, _draw_skill_progress_bar, _clean_pdf_text,
    _sync_resume_social_links, _sanitize_pdf_data
)


class CircularBadge(Flowable):
    """
    Renders a crisp vector circular badge with custom glyph/icon.
    Used for section headers in both the sidebar (white badge + navy icon)
    and the main content column (navy badge + white icon).
    """
    def __init__(self, icon_type: str = "about", bg_color=colors.HexColor("#1B3A5C"), fg_color=colors.white, size: float = 22.0):
        super().__init__()
        self.icon_type = icon_type
        self.bg_color = bg_color
        self.fg_color = fg_color
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
        r = self.size / 2.0

        # Background circle
        c.setFillColor(self.bg_color)
        c.circle(cx, cy, r, fill=1, stroke=0)

        # Foreground icon
        c.setFillColor(self.fg_color)
        c.setStrokeColor(self.fg_color)
        c.setLineWidth(1.1)

        itype = self.icon_type.lower()
        if itype in ("about", "user", "profile"):
            # User head & shoulders
            c.circle(cx, cy + 2.5, 3.0, fill=1, stroke=0)
            p = c.beginPath()
            p.arc(cx - 5.5, cy - 7.0, cx + 5.5, cy + 2.0, 0, 180)
            c.drawPath(p, fill=1, stroke=0)
        elif itype in ("experience", "work", "briefcase"):
            # Briefcase body & handle
            c.roundRect(cx - 5.5, cy - 4.5, 11, 7.5, 1, fill=0, stroke=1)
            c.rect(cx - 2.5, cy + 3.0, 5, 2.3, fill=0, stroke=1)
            c.line(cx - 5.5, cy - 0.5, cx + 5.5, cy - 0.5)
        elif itype in ("education", "school", "grad"):
            # Graduation cap
            p = c.beginPath()
            p.moveTo(cx, cy + 4.5)
            p.lineTo(cx + 6.0, cy + 1.5)
            p.lineTo(cx, cy - 1.5)
            p.lineTo(cx - 6.0, cy + 1.5)
            p.close()
            c.drawPath(p, fill=1, stroke=0)
            c.line(cx - 3.5, cy + 0.2, cx - 3.5, cy - 3.5)
            c.arc(cx - 3.5, cy - 5.0, cx + 3.5, cy + 0.5, 200, 140)
        elif itype in ("projects", "folder", "code"):
            # Folder
            c.roundRect(cx - 5.5, cy - 4.5, 11, 8.0, 1, fill=0, stroke=1)
            c.line(cx - 5.5, cy + 1.5, cx - 1.5, cy + 1.5)
            c.line(cx - 1.5, cy + 1.5, cx + 0.5, cy + 3.5)
            c.line(cx + 0.5, cy + 3.5, cx + 5.5, cy + 3.5)
        elif itype in ("contact", "phone"):
            # Phone handset
            c.roundRect(cx - 3.5, cy - 5.5, 7, 11, 1.5, fill=0, stroke=1)
            c.circle(cx, cy - 3.5, 0.7, fill=1, stroke=0)
        elif itype in ("skills", "tools"):
            # 4 dots matrix
            c.circle(cx - 2.5, cy + 2.5, 1.4, fill=1, stroke=0)
            c.circle(cx + 2.5, cy + 2.5, 1.4, fill=1, stroke=0)
            c.circle(cx - 2.5, cy - 2.5, 1.4, fill=1, stroke=0)
            c.circle(cx + 2.5, cy - 2.5, 1.4, fill=1, stroke=0)
        elif itype in ("certifications", "award", "medal"):
            # Medal / certificate ribbon
            c.circle(cx, cy + 1.5, 4.0, fill=0, stroke=1)
            c.line(cx - 2.5, cy - 1.5, cx - 4.0, cy - 5.5)
            c.line(cx + 2.5, cy - 1.5, cx + 4.0, cy - 5.5)
        else:
            # Generic clean bullet
            c.circle(cx, cy, 3.5, fill=1, stroke=0)

        c.restoreState()


class TimelineDot(Flowable):
    """
    Renders the circular node dot on the left of each experience item.
    The vertical timeline line passes through x=12.
    The outer white halo ring prevents the line from crossing inside the dot.
    """
    def __init__(self, dot_color=colors.HexColor("#1B3A5C"), ring_color=colors.white, radius: float = 3.8):
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
        x = 12.0  # Align exactly with the LINEBEFORE border of column 1
        y = 7.0   # Vertical center of the 14pt cell, aligning with the job title
        # Outer white ring
        c.setFillColor(self.ring_color)
        c.circle(x, y, self.radius + 1.8, fill=1, stroke=0)
        # Inner navy node dot
        c.setFillColor(self.dot_color)
        c.circle(x, y, self.radius, fill=1, stroke=0)
        c.restoreState()


def _draw_sidebar_badge_header(canvas, title: str, icon_type: str, navy_color, x: float, y_top: float, max_w: float, font_bold: str) -> float:
    """
    Draws a white circular badge with navy icon alongside an uppercase white heading in the sidebar.
    Returns total vertical height consumed.
    """
    badge_size = 20.0
    bx = x
    by = y_top - badge_size
    cx = bx + badge_size / 2.0
    cy = by + badge_size / 2.0

    canvas.saveState()
    # 1. White circular badge
    canvas.setFillColor(colors.white)
    canvas.circle(cx, cy, badge_size / 2.0, fill=1, stroke=0)

    # 2. Navy vector icon inside
    canvas.setFillColor(navy_color)
    canvas.setStrokeColor(navy_color)
    canvas.setLineWidth(1.1)

    itype = icon_type.lower()
    if itype in ("contact", "phone"):
        canvas.roundRect(cx - 3.0, cy - 4.5, 6, 9.5, 1.2, fill=0, stroke=1)
        canvas.circle(cx, cy - 3.0, 0.6, fill=1, stroke=0)
    elif itype in ("education", "school", "grad"):
        p = canvas.beginPath()
        p.moveTo(cx, cy + 3.8)
        p.lineTo(cx + 5.2, cy + 1.2)
        p.lineTo(cx, cy - 1.4)
        p.lineTo(cx - 5.2, cy + 1.2)
        p.close()
        canvas.drawPath(p, fill=1, stroke=0)
        canvas.line(cx - 3.0, cy + 0.2, cx - 3.0, cy - 3.0)
    elif itype in ("skills", "tools"):
        canvas.circle(cx - 2.2, cy + 2.2, 1.2, fill=1, stroke=0)
        canvas.circle(cx + 2.2, cy + 2.2, 1.2, fill=1, stroke=0)
        canvas.circle(cx - 2.2, cy - 2.2, 1.2, fill=1, stroke=0)
        canvas.circle(cx + 2.2, cy - 2.2, 1.2, fill=1, stroke=0)
    else:
        canvas.circle(cx, cy, 3.0, fill=1, stroke=0)

    # 3. Uppercase Heading text in White
    canvas.setFillColor(colors.white)
    canvas.setFont(font_bold, 9.5)
    canvas.drawString(bx + badge_size + 8, cy - 3.2, title.upper())

    canvas.restoreState()
    return badge_size + 8.0


def _navy_executive_pdf(resume: TailoredResume) -> bytes:
    """
    Renders the modern 'Navy Executive' CV layout:
    - 35% Left Sidebar in Deep Corporate Navy (#1B3A5C)
    - High-profile circular candidate avatar with 4.5pt white border
    - Contact, Education, and Skills in left sidebar with white badges
    - Name, Subtitle, Summary, Experience timeline & Projects in right column
    - Vertical timeline with node dots and crisp typography
    """
    _sanitize_pdf_data(resume)
    _sync_resume_social_links(resume)

    PAGE_W, PAGE_H = A4  # 595.28 x 841.89 pt
    SIDE_W = 208.0       # 35% of page width
    SIDE_PAD = 18.0
    SIDE_MAX_W = SIDE_W - (SIDE_PAD * 2)  # 172 pt

    # Color Palette
    navy_hex = "#1B3A5C"
    if resume.custom_accent_color and resume.custom_accent_color.lower() not in ("#000000", "#ffffff"):
        navy_hex = resume.custom_accent_color
    navy_color = colors.HexColor(navy_hex)

    text_primary = colors.HexColor("#1A1A1A")
    text_secondary = colors.HexColor("#4A4A4A")
    text_muted = colors.HexColor("#7A7A7A")
    divider_color = colors.HexColor("#D0D5DC")

    f_reg, f_bold, f_italic = _get_font_names(getattr(resume, "font_family", "Helvetica"))
    font_scale = getattr(resume, "font_size_scale", "standard") or "standard"

    if font_scale == "compact":
        body_size, body_leading, name_size = 7.8, 10.8, 21.0
        side_size, side_leading = 6.8, 9.4
        spacer_h = 3.2
    elif font_scale == "large":
        body_size, body_leading, name_size = 10.0, 14.0, 28.0
        side_size, side_leading = 8.5, 12.0
        spacer_h = 5.8
    elif font_scale == "spacious":
        body_size, body_leading, name_size = 11.0, 15.5, 30.0
        side_size, side_leading = 9.2, 13.0
        spacer_h = 7.0
    else:  # standard
        body_size, body_leading, name_size = 8.8, 12.4, 25.0
        side_size, side_leading = 7.8, 11.0
        spacer_h = 4.8

    # Platypus Styles for Right Main Column
    S = getSampleStyleSheet()
    _add(S, ParagraphStyle("NeName", fontName=f_bold, fontSize=name_size, leading=name_size + 3.0, textColor=text_primary, spaceAfter=2))
    _add(S, ParagraphStyle("NeRole", fontName=f_reg, fontSize=body_size + 2.5, leading=body_leading + 2.0, textColor=text_secondary, spaceAfter=10))
    _add(S, ParagraphStyle("NeSecTitle", fontName=f_bold, fontSize=body_size + 1.5, leading=body_leading + 1.2, textColor=text_primary))
    _add(S, ParagraphStyle("NeBody", fontName=f_reg, fontSize=body_size, leading=body_leading + 1.0, textColor=text_secondary, spaceAfter=4))
    _add(S, ParagraphStyle("NeJobTitle", fontName=f_bold, fontSize=body_size + 0.8, leading=body_leading + 1.2, textColor=text_primary))
    _add(S, ParagraphStyle("NeJobCompany", fontName=f_italic, fontSize=body_size - 0.2, leading=body_leading, textColor=text_secondary, spaceAfter=2))
    _add(S, ParagraphStyle("NeBullet", fontName=f_reg, fontSize=body_size - 0.2, leading=body_leading, textColor=text_secondary, leftIndent=8, firstLineIndent=-6, spaceAfter=2))
    _add(S, ParagraphStyle("NeProjTitle", fontName=f_bold, fontSize=body_size + 0.6, leading=body_leading + 1, textColor=text_primary))
    _add(S, ParagraphStyle("NeProjSub", fontName=f_reg, fontSize=body_size - 0.4, leading=body_leading, textColor=text_muted, spaceAfter=2))

    # Styles for Left Sidebar Text
    _add(S, ParagraphStyle("NeSideContact", fontName=f_reg, fontSize=side_size, leading=side_leading, textColor=colors.white))
    _add(S, ParagraphStyle("NeSideEduInst", fontName=f_bold, fontSize=side_size + 0.4, leading=side_leading, textColor=colors.white))
    _add(S, ParagraphStyle("NeSideEduDeg", fontName=f_reg, fontSize=side_size - 0.4, leading=side_leading - 0.5, textColor=colors.HexColor("#C5D3E0")))
    _add(S, ParagraphStyle("NeSideEduYear", fontName=f_reg, fontSize=side_size - 0.8, leading=side_leading - 1.0, textColor=colors.HexColor("#9FB7CE"), spaceAfter=5))
    _add(S, ParagraphStyle("NeSideSkill", fontName=f_reg, fontSize=side_size, leading=side_leading, textColor=colors.white, leftIndent=7, firstLineIndent=-5, spaceAfter=2))
    _add(S, ParagraphStyle("NeSideCat", fontName=f_bold, fontSize=side_size - 0.4, leading=side_leading - 0.5, textColor=colors.HexColor("#C5D3E0"), spaceAfter=2))

    # Track rendered items to handle clean multi-page continuation
    rendered_edu_count = [0]
    rendered_skills_state = {"cat_idx": 0, "skill_idx": 0}

    def on_first_page(canvas, doc):
        canvas.saveState()
        info = resume.personal_info

        # 1. Left Navy Sidebar background
        canvas.setFillColor(navy_color)
        canvas.rect(0, 0, SIDE_W, PAGE_H, fill=1, stroke=0)

        # 2. Profile Photo or Monogram in Left Sidebar
        y = PAGE_H - 32.0
        photo_size = 78.0
        photo_x = (SIDE_W - photo_size) / 2.0
        photo_y = y - photo_size
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
                    p = canvas.beginPath()
                    p.circle(cx, cy, radius)
                    canvas.clipPath(p, stroke=0)
                    reader = ImageReader(img_bytes)
                    canvas.drawImage(reader, photo_x, photo_y, width=photo_size, height=photo_size, preserveAspectRatio=True)
                    canvas.restoreState()
                    # Solid white circular border (4pt)
                    canvas.setStrokeColor(colors.white)
                    canvas.setLineWidth(4.0)
                    canvas.circle(cx, cy, radius, stroke=1, fill=0)
                    img_drawn = True
                except Exception:
                    img_drawn = False

        if not img_drawn:
            # Executive Monogram placeholder
            canvas.setFillColor(colors.HexColor("#244A72"))
            canvas.circle(cx, cy, radius, fill=1, stroke=0)
            canvas.setStrokeColor(colors.white)
            canvas.setLineWidth(3.5)
            canvas.circle(cx, cy, radius, stroke=1, fill=0)

            # Draw initials
            names = (info.full_name or "C").split()
            initials = "".join([n[0] for n in names[:2]]).upper()
            canvas.setFillColor(colors.white)
            canvas.setFont(f_bold, 24)
            canvas.drawCentredString(cx, cy - 8, initials)

        y = photo_y - 20.0

        # 3. CONTACT SECTION (Left Sidebar)
        y -= _draw_sidebar_badge_header(canvas, "Contact", "contact", navy_color, SIDE_PAD, y, SIDE_MAX_W, f_bold)
        contacts = []
        if info.phone:     contacts.append(info.phone)
        if info.email:     contacts.append(info.email)
        if info.location:  contacts.append(info.location)
        if info.linkedin:  contacts.append(info.linkedin.replace("https://www.", "").replace("https://", ""))
        if info.portfolio: contacts.append(info.portfolio.replace("https://www.", "").replace("https://", ""))
        if info.github:    contacts.append(info.github.replace("https://www.", "").replace("https://", ""))

        for c_text in contacts:
            if y < 70: break
            y -= _draw_sidebar_para(canvas, c_text, S["NeSideContact"], SIDE_PAD + 2, y, SIDE_MAX_W - 4)
            y -= 4.0

        y -= 10.0

        # 4. EDUCATION SECTION (Left Sidebar)
        if resume.show_education and resume.education:
            y -= _draw_sidebar_badge_header(canvas, "Education", "education", navy_color, SIDE_PAD, y, SIDE_MAX_W, f_bold)
            for idx, edu in enumerate(resume.education):
                if y < 85: break
                y -= _draw_sidebar_para(canvas, edu.institution, S["NeSideEduInst"], SIDE_PAD + 2, y, SIDE_MAX_W - 4)
                y -= 2.0
                y -= _draw_sidebar_para(canvas, edu.degree, S["NeSideEduDeg"], SIDE_PAD + 2, y, SIDE_MAX_W - 4)
                y -= 2.0
                dates = edu.graduation_year or (f"{edu.start_date} – {edu.end_date}" if (edu.start_date or edu.end_date) else "")
                if dates:
                    y -= _draw_sidebar_para(canvas, dates, S["NeSideEduYear"], SIDE_PAD + 2, y, SIDE_MAX_W - 4)
                y -= 4.0
                rendered_edu_count[0] = idx + 1

            y -= 8.0

        # 5. SKILLS SECTION (Left Sidebar with Progress Bars)
        if resume.show_skills and resume.skill_categories:
            y -= _draw_sidebar_badge_header(canvas, "Skills", "skills", navy_color, SIDE_PAD, y, SIDE_MAX_W, f_bold)
            show_bars = getattr(resume, "show_skill_bars", True)
            bar_style = getattr(resume, "skill_bar_style", "sleek") or "sleek"

            bar_fill_color = colors.HexColor("#38BDF8")
            if resume.custom_accent_color and resume.custom_accent_color.lower() not in ("#1b3a5c", "#000000"):
                bar_fill_color = colors.HexColor(resume.custom_accent_color)
            bar_track_color = colors.HexColor("#244A72")

            completed_all = True
            for cat_idx in range(len(resume.skill_categories)):
                cat = resume.skill_categories[cat_idx]
                if y < 45:
                    completed_all = False
                    rendered_skills_state["cat_idx"] = cat_idx
                    rendered_skills_state["skill_idx"] = 0
                    break

                if cat.category_name and len(resume.skill_categories) > 1:
                    y -= _draw_sidebar_para(canvas, cat.category_name.upper(), S["NeSideCat"], SIDE_PAD + 2, y, SIDE_MAX_W - 4)
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
                            canvas, s, s_level, SIDE_PAD + 2, y, SIDE_MAX_W - 4,
                            style=bar_style, bar_color=bar_fill_color, bg_color=bar_track_color,
                            text_color=colors.white, pct_color=colors.HexColor("#C5D3E0"), font_name=f_reg, font_size=side_size
                        )
                        y -= (consumed + 3.0)
                    else:
                        y -= _draw_sidebar_para(canvas, f"• {s}", S["NeSideSkill"], SIDE_PAD + 4, y, SIDE_MAX_W - 6)
                        y -= 2.0

                if not cat_finished:
                    break

                y -= 4.0

            if completed_all:
                rendered_skills_state["cat_idx"] = len(resume.skill_categories)
                rendered_skills_state["skill_idx"] = 0

        # Page 1 Footer inside sidebar
        canvas.setFillColor(colors.HexColor("#7A9EBF"))
        canvas.setFont("Helvetica", 7.5)
        canvas.drawCentredString(SIDE_W / 2.0, 14, "Page 1")

        # Watermark if enabled
        if getattr(resume, "watermark", False):
            _draw_diagonal_watermark(canvas, PAGE_W, PAGE_H)

        canvas.restoreState()

    def on_later_pages(canvas, doc):
        canvas.saveState()

        # Left Navy Sidebar background continues cleanly
        # Absolutely NO duplicate avatar circle, NO duplicate candidate name, NO duplicate role title!
        canvas.setFillColor(navy_color)
        canvas.rect(0, 0, SIDE_W, PAGE_H, fill=1, stroke=0)

        y = PAGE_H - 32.0

        # Overflow Education if any
        if resume.show_education and resume.education and rendered_edu_count[0] < len(resume.education):
            y -= _draw_sidebar_badge_header(canvas, "Education (Cont.)", "education", navy_color, SIDE_PAD, y, SIDE_MAX_W, f_bold)
            for edu in resume.education[rendered_edu_count[0]:]:
                if y < 85: break
                y -= _draw_sidebar_para(canvas, edu.institution, S["NeSideEduInst"], SIDE_PAD + 2, y, SIDE_MAX_W - 4)
                y -= 2.0
                y -= _draw_sidebar_para(canvas, edu.degree, S["NeSideEduDeg"], SIDE_PAD + 2, y, SIDE_MAX_W - 4)
                y -= 2.0
                dates = edu.graduation_year or (f"{edu.start_date} – {edu.end_date}" if (edu.start_date or edu.end_date) else "")
                if dates:
                    y -= _draw_sidebar_para(canvas, dates, S["NeSideEduYear"], SIDE_PAD + 2, y, SIDE_MAX_W - 4)
                y -= 4.0

        # Overflow Skills if any
        if resume.show_skills and resume.skill_categories and rendered_skills_state["cat_idx"] < len(resume.skill_categories):
            y -= _draw_sidebar_badge_header(canvas, "Skills (Cont.)", "skills", navy_color, SIDE_PAD, y, SIDE_MAX_W, f_bold)
            show_bars = getattr(resume, "show_skill_bars", True)
            bar_style = getattr(resume, "skill_bar_style", "sleek") or "sleek"

            bar_fill_color = colors.HexColor("#38BDF8")
            if resume.custom_accent_color and resume.custom_accent_color.lower() not in ("#1b3a5c", "#000000"):
                bar_fill_color = colors.HexColor(resume.custom_accent_color)
            bar_track_color = colors.HexColor("#244A72")

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
                    y -= _draw_sidebar_para(canvas, cat_title, S["NeSideCat"], SIDE_PAD + 2, y, SIDE_MAX_W - 4)
                    y -= 2.0

                levels = getattr(cat, "skill_levels", {}) or {}
                skills_list = cat.skills or []
                for s in skills_list[s_from:]:
                    req_h = 19.0 if show_bars else 13.0
                    if y < 35 + req_h: break

                    if show_bars:
                        s_level = levels.get(s, 85)
                        consumed = _draw_skill_progress_bar(
                            canvas, s, s_level, SIDE_PAD + 2, y, SIDE_MAX_W - 4,
                            style=bar_style, bar_color=bar_fill_color, bg_color=bar_track_color,
                            text_color=colors.white, pct_color=colors.HexColor("#C5D3E0"), font_name=f_reg, font_size=side_size
                        )
                        y -= (consumed + 3.0)
                    else:
                        y -= _draw_sidebar_para(canvas, f"• {s}", S["NeSideSkill"], SIDE_PAD + 4, y, SIDE_MAX_W - 6)
                        y -= 2.0

                y -= 4.0

        # Page N Footer inside sidebar
        canvas.setFillColor(colors.HexColor("#7A9EBF"))
        canvas.setFont("Helvetica", 7.5)
        canvas.drawCentredString(SIDE_W / 2.0, 14, f"Page {doc.page}")

        # Top right subtle page header in main column
        canvas.setFillColor(text_muted)
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(PAGE_W - 24, PAGE_H - 20, f"Page {doc.page}")
        canvas.setStrokeColor(divider_color)
        canvas.setLineWidth(0.5)
        canvas.line(SIDE_W + 24, PAGE_H - 24, PAGE_W - 24, PAGE_H - 24)

        if getattr(resume, "watermark", False):
            _draw_diagonal_watermark(canvas, PAGE_W, PAGE_H)

        canvas.restoreState()

    # RIGHT COLUMN FLOWABLES
    body = []
    CONTENT_W = PAGE_W - (SIDE_W + 24) - 24  # ~339 pt

    # Helper: Main Column Section Header Table (Navy circular badge + Section Title)
    def make_main_header(title: str, icon_type: str) -> Table:
        badge = CircularBadge(icon_type=icon_type, bg_color=navy_color, fg_color=colors.white, size=21.0)
        title_para = Paragraph(title.upper(), S["NeSecTitle"])
        hdr_table = Table([[badge, title_para]], colWidths=[27, CONTENT_W - 27])
        hdr_table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (0, 0), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING", (1, 0), (1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return hdr_table

    # 1. Header: Candidate Full Name & Target Role Subtitle
    info = resume.personal_info
    full_name_upper = (info.full_name or "CANDIDATE NAME").upper()
    body.append(Paragraph(full_name_upper, S["NeName"]))
    if resume.target_job_title:
        body.append(Paragraph(resume.target_job_title.upper(), S["NeRole"]))
    else:
        body.append(Spacer(1, 6))

    # Section ordering
    raw_order = getattr(resume, "section_order", None) or ["summary", "experience", "projects", "certifications"]
    order = list(raw_order)
    for sec_name, is_active in [
        ("summary", resume.show_summary and resume.professional_summary),
        ("experience", resume.show_experience and resume.work_experience),
        ("projects", resume.show_projects and resume.projects),
        ("certifications", resume.show_certifications and resume.certifications),
    ]:
        if is_active and sec_name not in order:
            order.append(sec_name)

    # 2. ABOUT ME / SUMMARY
    def add_summary():
        if resume.show_summary and resume.professional_summary:
            sec_flow = [
                make_main_header("About Me", "about"),
                Spacer(1, 2),
                Paragraph(resume.professional_summary, S["NeBody"]),
                Spacer(1, spacer_h * 0.8),
            ]
            body.append(KeepTogether(sec_flow))

    # 3. WORK EXPERIENCE (Vertical Timeline with Continuous Line & Node Dots)
    def add_experience():
        if resume.show_experience and resume.work_experience:
            body.append(make_main_header("Experience", "experience"))
            body.append(Spacer(1, 2))

            timeline_rows = []
            for exp in resume.work_experience:
                date_str = f"{exp.start_date} – {exp.end_date}"
                loc_str = f" · {exp.location}" if exp.location else ""

                item_flowables = [
                    # Header row: Job Title on left, Dates in muted gray
                    Paragraph(f"<b>{exp.job_title}</b> <font color='#7A7A7A' size='7.5'>({date_str})</font>", S["NeJobTitle"]),
                    Paragraph(f"{exp.company}{loc_str}", S["NeJobCompany"]),
                ]
                for b in exp.bullet_points:
                    clean_b = b.lstrip("•- ")
                    item_flowables.append(Paragraph(f"• {clean_b}", S["NeBullet"]))

                dot = TimelineDot(dot_color=navy_color, ring_color=colors.white, radius=3.6)
                timeline_rows.append([dot, item_flowables])

            timeline_table = Table(timeline_rows, colWidths=[14, CONTENT_W - 14])
            timeline_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (1, -1), 1.1, divider_color),
                ("LEFTPADDING", (0, 0), (0, 0), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (1, 0), (1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            body.append(timeline_table)
            body.append(Spacer(1, spacer_h * 0.6))

    # 4. KEY PROJECTS
    def add_projects():
        if resume.show_projects and resume.projects:
            body.append(make_main_header("Key Projects", "projects"))
            body.append(Spacer(1, 3))

            for proj in resume.projects:
                p_flow = []
                link_text = f" <font color='#7A7A7A' size='7.5'>({proj.link})</font>" if proj.link else ""
                p_flow.append(Paragraph(f"<b>{proj.name}</b>{link_text}", S["NeProjTitle"]))

                if proj.technologies:
                    tech_str = " · ".join(proj.technologies)
                    p_flow.append(Paragraph(f"<i>Technologies: {tech_str}</i>", S["NeProjSub"]))

                if hasattr(proj, "description_bullets") and proj.description_bullets:
                    for b in proj.description_bullets:
                        p_flow.append(Paragraph(f"• {b.lstrip('•- ')}", S["NeBullet"]))

                p_flow.append(Spacer(1, 4))
                body.append(KeepTogether(p_flow))

            body.append(Spacer(1, spacer_h * 0.5))

    # 5. CERTIFICATIONS
    def add_certifications():
        if resume.show_certifications and resume.certifications:
            body.append(make_main_header("Certifications & Licenses", "certifications"))
            body.append(Spacer(1, 3))

            cert_flow = []
            for cert in resume.certifications:
                year_str = f" <font color='#7A7A7A' size='7.5'>({cert.year})</font>" if cert.year else ""
                cert_flow.append(Paragraph(f"• <b>{cert.name}</b> — {cert.issuer}{year_str}", S["NeJobTitle"]))
                cert_flow.append(Spacer(1, 2))

            body.append(KeepTogether(cert_flow))
            body.append(Spacer(1, spacer_h * 0.5))

    for sec in order:
        if sec == "summary":
            add_summary()
        elif sec == "experience":
            add_experience()
        elif sec == "projects":
            add_projects()
        elif sec == "certifications":
            add_certifications()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=SIDE_W + 24,
        rightMargin=24,
        topMargin=32,
        bottomMargin=24
    )
    doc.build(body, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buf.seek(0)
    return buf.getvalue()
