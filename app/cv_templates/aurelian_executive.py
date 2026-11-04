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
    resolve_custom_avatar_metrics, _draw_styled_avatar,
    resolve_custom_layout_metrics, resolve_custom_sidebar_font_size, resolve_custom_vertical_margins,
    get_published_portfolio_url,
    render_cv_portfolio_footer,
    _add, _hex_to_rgb, _load_avatar_image, _get_font_names,
    _draw_diagonal_watermark, _draw_sidebar_para, _draw_skill_progress_bar, _clean_pdf_text,
    _sync_resume_social_links, _sanitize_pdf_data
)


class AurelianTimelineDot(Flowable):
    """
    Renders the elegant hollow circular bronze node dot on the left of each item.
    Centered exactly on the LINEBEFORE vertical timeline line at x=16.0.
    """
    def __init__(self, dot_color=colors.HexColor("#B8935A"), ring_color=colors.white, radius: float = 3.4):
        super().__init__()
        self.dot_color = dot_color
        self.ring_color = ring_color
        self.radius = radius
        self.width = 16
        self.height = 14

    def wrap(self, availWidth, availHeight):
        return (self.width, self.height)

    def draw(self):
        c = self.canv
        c.saveState()
        x = 16.0
        y = 7.0
        # White fill background with bronze outer ring
        c.setFillColor(self.ring_color)
        c.setStrokeColor(self.dot_color)
        c.setLineWidth(1.4)
        c.circle(x, y, self.radius, fill=1, stroke=1)
        c.restoreState()


def _draw_aurelian_sidebar_header(canvas, num_str: str, title: str, bronze_color, hairline_color, x: float, y_top: float, max_w: float, f_bold: str, f_reg: str, title_size: float = 11.5, num_size: float = 8.5) -> float:
    """
    Draws a numbered section header in the sidebar:
    e.g. '01  Contact ──────────'
    Returns vertical height consumed.
    """
    canvas.saveState()

    # Number in bronze
    canvas.setFont(f_bold, num_size)
    canvas.setFillColor(bronze_color)
    canvas.drawString(x, y_top - 9.0, num_str)
    num_w = canvas.stringWidth(num_str, f_bold, num_size)

    # Title in bold / dark ink
    canvas.setFont(f_bold, title_size)
    canvas.setFillColor(colors.HexColor("#0F0F0F"))
    title_x = x + num_w + 6.0
    canvas.drawString(title_x, y_top - 9.0, title)
    title_w = canvas.stringWidth(title, f_bold, title_size)

    # Hairline rule extending to the right edge
    rule_start_x = title_x + title_w + 6.0
    rule_end_x = x + max_w
    if rule_end_x > rule_start_x + 5.0:
        canvas.setStrokeColor(hairline_color)
        canvas.setLineWidth(0.8)
        canvas.line(rule_start_x, y_top - 5.5, rule_end_x, y_top - 5.5)

    canvas.restoreState()
    return max(18.0, title_size + 8.5)


def _draw_aurelian_skill_dots(canvas, name: str, level_pct: int, bronze_color, hairline_color, x: float, y_top: float, max_w: float, font_name: str, font_size: float = 7.8) -> float:
    """
    Draws a skill entry with 5 refined dot ratings on the right.
    Consumes a well-defined vertical row height with zero text collision.
    """
    canvas.saveState()
    canvas.setFont(font_name, font_size)
    canvas.setFillColor(colors.HexColor("#2A2A2A"))

    row_h = font_size + 6.0
    baseline_y = y_top - font_size - 1.0

    dots_total_w = 5 * 7.0
    text_max_w = max_w - dots_total_w - 6.0
    display_name = name
    while canvas.stringWidth(display_name, font_name, font_size) > text_max_w and len(display_name) > 3:
        display_name = display_name[:-1]
    if display_name != name:
        display_name = display_name[:-2] + ".."

    canvas.drawString(x, baseline_y, display_name)

    filled_count = max(1, min(5, round((level_pct / 100.0) * 5)))
    dots_start_x = x + max_w - dots_total_w
    dot_y = baseline_y + (font_size * 0.35)
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
    canvas.line(x, y_top - row_h + 1.0, x + max_w, y_top - row_h + 1.0)

    canvas.restoreState()
    return row_h


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

    f_reg, f_bold, f_italic = _get_font_names(getattr(resume, "font_family", "Times-Roman"))

    summary_placement = getattr(resume, "summary_placement", "right") or "right"
    summary_on_left = (summary_placement == "left")

    # Dynamic Proportional Font Scaling
    font_scale = getattr(resume, "font_size_scale", "standard") or "standard"
    if font_scale == "compact":
        body_size, body_leading, name_size = 7.8, 10.8, 19.0
        side_size, side_leading = 6.8, 9.4
        spacer_h = 3.2
    elif font_scale == "large":
        body_size, body_leading, name_size = 10.0, 14.0, 24.0
        side_size, side_leading = 8.5, 12.0
        spacer_h = 5.8
    elif font_scale == "spacious":
        body_size, body_leading, name_size = 11.2, 16.0, 26.0
        side_size, side_leading = 9.2, 13.0
        spacer_h = 8.5
    else:  # standard
        body_size, body_leading, name_size = 8.8, 12.4, 21.5
        side_size, side_leading = 7.8, 11.0
        spacer_h = 4.8

    MAIN_PAD = 22.0
    body_size, body_leading, _, spacer_h, custom_margin, custom_side_w = resolve_custom_layout_metrics(
        resume,
        base_body_size=body_size,
        base_body_leading=body_leading,
        base_sec_size=body_size + 1.5,
        base_spacer_h=spacer_h,
        base_margin=MAIN_PAD,
        base_side_w=SIDE_W
    )
    if custom_side_w is not None:
        SIDE_W = custom_side_w
        SIDE_MAX_W = SIDE_W - (SIDE_PAD * 2)
    if getattr(resume, "custom_page_margin", None) is not None:
        MAIN_PAD = float(resume.custom_page_margin)
    MAIN_LEFT = SIDE_W + MAIN_PAD
    MAIN_MAX_W = PAGE_W - MAIN_LEFT - MAIN_PAD
    top_m, bot_m = resolve_custom_vertical_margins(resume, base_top_margin=32.0, base_bottom_margin=24.0)
    side_size = resolve_custom_sidebar_font_size(resume, fallback_body_size=body_size)
    side_leading = round(side_size * 1.35, 1)
    name_size = round(body_size * 2.3, 1)
    side_sec_gap = max(2.0, round(spacer_h * 1.5, 1))
    side_item_gap = max(1.0, round(spacer_h * 0.5, 1))

    # Platypus Styles for Right Main Column
    S = getSampleStyleSheet()

    _add(S, ParagraphStyle("AuJobTitle", fontName=f_bold, fontSize=body_size + 1.5, leading=body_leading + 1.8, textColor=ink_primary, spaceAfter=1))
    _add(S, ParagraphStyle("AuCompany", fontName=f_italic, fontSize=body_size + 0.2, leading=body_leading + 0.4, textColor=ink_muted, spaceAfter=2))
    _add(S, ParagraphStyle("AuDate", fontName=f_bold, fontSize=body_size - 1.0, leading=body_leading, textColor=bronze_color, alignment=TA_RIGHT))
    _add(S, ParagraphStyle("AuBody", fontName=f_reg, fontSize=body_size, leading=body_leading + 1.2, textColor=ink_soft, spaceAfter=3))
    _add(S, ParagraphStyle("AuBullet", fontName=f_reg, fontSize=body_size, leading=body_leading + 1.0, textColor=ink_soft, leftIndent=9, firstLineIndent=-7, spaceAfter=2))
    _add(S, ParagraphStyle("AuProjTitle", fontName=f_bold, fontSize=body_size + 1.2, leading=body_leading + 1.5, textColor=ink_primary, spaceAfter=1))
    _add(S, ParagraphStyle("AuProjSub", fontName=f_italic, fontSize=body_size - 0.2, leading=body_leading, textColor=bronze_color, spaceAfter=2))

    # Styles for Left Sidebar
    _add(S, ParagraphStyle("AuEyebrow", fontName=f_bold, fontSize=round(side_size * 0.88, 1), leading=round(side_size * 1.15, 1), textColor=bronze_color, alignment=TA_CENTER, spaceAfter=2))
    _add(S, ParagraphStyle("AuSideName", fontName=f_bold, fontSize=name_size, leading=name_size + 2.5, textColor=ink_primary, alignment=TA_CENTER, spaceAfter=3))
    _add(S, ParagraphStyle("AuSideRole", fontName=f_bold, fontSize=round(side_size * 1.05, 1), leading=round(side_size * 1.35, 1), textColor=ink_muted, alignment=TA_CENTER, spaceAfter=4))
    _add(S, ParagraphStyle("AuSideContact", fontName=f_reg, fontSize=side_size, leading=side_leading, textColor=ink_soft))
    _add(S, ParagraphStyle("AuSideAbout", fontName=f_reg, fontSize=side_size, leading=side_leading, textColor=ink_soft, spaceAfter=3))
    _add(S, ParagraphStyle("AuSideCat", fontName=f_bold, fontSize=round(side_size * 0.95, 1), leading=round(side_size * 1.25, 1), textColor=bronze_color, spaceAfter=2))

    MAIN_LEFT = SIDE_W + MAIN_PAD
    MAIN_MAX_W = PAGE_W - MAIN_LEFT - MAIN_PAD
    top_m, bot_m = resolve_custom_vertical_margins(resume, base_top_margin=32.0, base_bottom_margin=24.0)

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

        # 4. Monogram Watermark removed

        # 5. Candidate Photo with Refined Double Frame
        photo_size, photo_shape, photo_radius = resolve_custom_avatar_metrics(resume, base_size=82.0, default_shape="circle")
        photo_x = (SIDE_W - photo_size) / 2.0
        photo_y = PAGE_H - max(28.0, top_m + 12.0) - photo_size
        radius = photo_size / 2.0
        cx = photo_x + radius
        cy = photo_y + radius

        # Outer delicate ring
        canvas.setStrokeColor(hairline_color)
        canvas.setLineWidth(0.8)
        canvas.circle(cx, cy, radius + 6.0, stroke=1, fill=0)

        # Inner refined bronze ring
        canvas.setStrokeColor(bronze_color)
        canvas.setLineWidth(1.0)
        canvas.circle(cx, cy, radius + 3.0, stroke=1, fill=0)

        has_photo = bool(getattr(resume, "show_photo", True) and info.avatar_url and info.avatar_url.strip())
        img_drawn = False
        if has_photo:
            img_bytes = _load_avatar_image(info.avatar_url)
            if img_bytes:
                img_drawn = _draw_styled_avatar(canvas, img_bytes, photo_x, photo_y, photo_size, shape=photo_shape, radius=photo_radius, border_color=colors.white, border_width=2.0)

        if not img_drawn:
            # Monogram avatar fallback
            canvas.setFillColor(colors.HexColor("#EFEBE4"))
            canvas.circle(cx, cy, radius, fill=1, stroke=0)
            canvas.setStrokeColor(colors.white)
            canvas.setLineWidth(2.0)
            canvas.circle(cx, cy, radius, stroke=1, fill=0)

            canvas.setFillColor(bronze_color)
            canvas.setFont("Times-Italic", max(14, int(photo_size * 0.3)))
            canvas.drawCentredString(cx, cy - (photo_size * 0.1), monogram)

        y = photo_y - 14.0

        # 6. NAME BLOCK (Centered in Left Sidebar - Page 1 Only)
        y -= _draw_sidebar_para(canvas, "CURRICULUM VITAE", S["AuEyebrow"], SIDE_PAD, y, SIDE_MAX_W)
        y -= 1.0

        full_name = info.full_name or "Candidate Name"
        y -= _draw_sidebar_para(canvas, full_name, S["AuSideName"], SIDE_PAD, y, SIDE_MAX_W)
        y -= 1.0

        if resume.target_job_title and resume.target_job_title.strip():
            y -= _draw_sidebar_para(canvas, resume.target_job_title.upper(), S["AuSideRole"], SIDE_PAD, y, SIDE_MAX_W)
            y -= 2.0

        # Elegant centered bronze divider line
        canvas.setStrokeColor(bronze_color)
        canvas.setLineWidth(1.0)
        canvas.line(cx - 16.0, y, cx + 16.0, y)
        y -= side_sec_gap

        # 7. SECTION 01: CONTACT
        au_hdr_title_size = max(8.5, round(side_size * 1.45, 1))
        au_hdr_num_size = max(6.8, round(side_size * 1.08, 1))
        y -= _draw_aurelian_sidebar_header(canvas, "01", "Contact", bronze_color, hairline_color, SIDE_PAD, y, SIDE_MAX_W, f_bold, f_reg, au_hdr_title_size, au_hdr_num_size)
        contacts = []
        if info.phone:     contacts.append(("phone", info.phone))
        if info.email:     contacts.append(("email", info.email))
        if info.location:  contacts.append(("location", info.location))
        if info.linkedin:  contacts.append(("linkedin", info.linkedin.replace("https://www.", "").replace("https://", "")))
        pub_url = get_published_portfolio_url(resume, position="header")
        if pub_url:        contacts.append(("portfolio", f"<a href='{pub_url}'><u>More on My Portfolio</u></a>"))
        elif getattr(resume, "show_portfolio_header", True) and getattr(resume, "show_portfolio_link", True) and info.portfolio: contacts.append(("portfolio", info.portfolio.replace("https://www.", "").replace("https://", "")))
        if info.github:    contacts.append(("github", info.github.replace("https://www.", "").replace("https://", "")))

        for c_type, c_text in contacts:
            if y < 70: break
            # Small bronze bullet dot
            canvas.setFillColor(bronze_color)
            canvas.circle(SIDE_PAD + 2.0, y - 5.5, 1.4, fill=1, stroke=0)
            y -= _draw_sidebar_para(canvas, c_text, S["AuSideContact"], SIDE_PAD + 8.0, y, SIDE_MAX_W - 8.0)
            y -= side_item_gap

        y -= side_sec_gap

        # 8. SECTION 02: PROFILE (Only if summary_on_left is True)
        if resume.show_summary and resume.professional_summary and summary_on_left and y > 150:
            y -= _draw_aurelian_sidebar_header(canvas, "02", "Profile", bronze_color, hairline_color, SIDE_PAD, y, SIDE_MAX_W, f_bold, f_reg, au_hdr_title_size, au_hdr_num_size)
            y -= _draw_sidebar_para(canvas, resume.professional_summary, S["AuSideAbout"], SIDE_PAD, y, SIDE_MAX_W)
            y -= side_sec_gap

        # 9. EXPERTISE (Skills with Dot Ratings)
        if resume.show_skills and resume.skill_categories and y > 60:
            exp_num = "03" if (resume.show_summary and resume.professional_summary and summary_on_left) else "02"
            y -= _draw_aurelian_sidebar_header(canvas, exp_num, "Expertise", bronze_color, hairline_color, SIDE_PAD, y, SIDE_MAX_W, f_bold, f_reg, au_hdr_title_size, au_hdr_num_size)
            y -= 4.0

            completed_all = True
            for cat_idx in range(len(resume.skill_categories)):
                cat = resume.skill_categories[cat_idx]
                if y < 45:
                    completed_all = False
                    rendered_skills_state["cat_idx"] = cat_idx
                    rendered_skills_state["skill_idx"] = 0
                    break

                if cat.category_name and len(resume.skill_categories) > 1:
                    y -= 5.0
                    y -= _draw_sidebar_para(canvas, cat.category_name.upper(), S["AuSideCat"], SIDE_PAD, y, SIDE_MAX_W)
                    y -= 4.0

                for s_idx in range(len(cat.skills)):
                    skill_name = cat.skills[s_idx]
                    if y < 35:
                        completed_all = False
                        rendered_skills_state["cat_idx"] = cat_idx
                        rendered_skills_state["skill_idx"] = s_idx
                        break

                    level = cat.skill_levels.get(skill_name, 80) if cat.skill_levels else 80
                    y -= _draw_aurelian_skill_dots(canvas, skill_name, level, bronze_color, hairline_color, SIDE_PAD, y, SIDE_MAX_W, f_reg, side_size)

            if completed_all:
                rendered_skills_state["cat_idx"] = 9999

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

        # 4. Subtle Top Accent Bar in Sidebar
        canvas.setFillColor(bronze_color)
        canvas.rect(0, PAGE_H - 4.0, SIDE_W, 4.0, fill=1, stroke=0)

        # 5. Monogram Watermark removed

        # 6. Sidebar Page Number at Bottom (NO duplicated candidate name or role!)
        canvas.setFont(f_bold, 7.5)
        canvas.setFillColor(bronze_color)
        canvas.drawCentredString(SIDE_W / 2.0, 16.0, f"CURRICULUM VITAE · PAGE {doc.page}")

        y = PAGE_H - 36.0

        # Remaining Skills Continuation
        cat_start = rendered_skills_state["cat_idx"]
        if cat_start < len(resume.skill_categories):
            y -= _draw_aurelian_sidebar_header(canvas, "03", "Expertise (Cont.)", bronze_color, hairline_color, SIDE_PAD, y, SIDE_MAX_W, f_bold, f_reg, au_hdr_title_size, au_hdr_num_size)
            y -= 4.0
            for c_idx in range(cat_start, len(resume.skill_categories)):
                cat = resume.skill_categories[c_idx]
                if y < 45: break

                s_start = rendered_skills_state["skill_idx"] if c_idx == cat_start else 0
                if cat.category_name and (len(resume.skill_categories) > 1 or s_start > 0):
                    c_title = cat.category_name.upper()
                    if s_start > 0:
                        c_title += " (CONT.)"
                    y -= 5.0
                    y -= _draw_sidebar_para(canvas, c_title, S["AuSideCat"], SIDE_PAD, y, SIDE_MAX_W)
                    y -= 4.0

                for s_idx in range(s_start, len(cat.skills)):
                    if y < 35: break
                    skill_name = cat.skills[s_idx]
                    level = cat.skill_levels.get(skill_name, 80) if cat.skill_levels else 80
                    y -= _draw_aurelian_skill_dots(canvas, skill_name, level, bronze_color, hairline_color, SIDE_PAD, y, SIDE_MAX_W, f_reg, side_size)

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
            ('BOTTOMPADDING', (0, 0), (-1, -1), max(1, round(spacer_h * 0.4, 1))),
            ('TOPPADDING', (0, 0), (-1, -1), max(1, round(spacer_h * 0.8, 1))),
            ('LINEBELOW', (0, 0), (-1, -1), 0.8, hairline_color),
        ]))
        flow.append(h_table)
        flow.append(Spacer(1, spacer_h * 0.8))
        return flow

    def add_summary():
        nonlocal section_counter
        if resume.show_summary and resume.professional_summary and not summary_on_left:
            r_num = romans[min(section_counter - 1, len(romans) - 1)]
            section_counter += 1
            body.extend(make_main_header(r_num, "Professional Summary"))
            body.append(Paragraph(resume.professional_summary, S["AuBody"]))
            body.append(Spacer(1, spacer_h * 0.6))

    # SECTION I: EDUCATION
    section_counter = 1
    romans = ["I.", "II.", "III.", "IV.", "V.", "VI."]

    def add_education():
        nonlocal section_counter
        if resume.show_education and resume.education:
            r_num = romans[min(section_counter - 1, len(romans) - 1)]
            section_counter += 1
            body.extend(make_main_header(r_num, "Education"))

            edu_rows = []
            for edu in resume.education:
                date_str = edu.graduation_year or ""
                if not date_str and (edu.start_date or edu.end_date):
                    date_str = f"{edu.start_date or ''} — {edu.end_date or ''}".strip(" —")

                item_flowables = [
                    Table(
                        [[
                            Paragraph(f"<b>{edu.degree}</b>", S["AuJobTitle"]),
                            Paragraph(date_str, S["AuDate"]),
                        ]],
                        colWidths=[MAIN_MAX_W - 20 - 90, 90],
                        style=[
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                        ]
                    ),
                    Paragraph(f"<i>{edu.institution}</i>", S["AuCompany"]),
                ]
                if edu.details:
                    item_flowables.append(Paragraph(edu.details, S["AuBody"]))

                dot = AurelianTimelineDot(dot_color=bronze_color)
                edu_rows.append([dot, item_flowables])

            edu_table = Table(edu_rows, colWidths=[16, MAIN_MAX_W - 16])
            edu_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (1, -1), 0.8, hairline_color),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 0),
                ("LEFTPADDING", (1, 0), (1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            body.append(edu_table)
            body.append(Spacer(1, spacer_h * 0.5))

    # SECTION II: WORK EXPERIENCE
    def add_experience():
        nonlocal section_counter
        if resume.show_experience and resume.work_experience:
            r_num = romans[min(section_counter - 1, len(romans) - 1)]
            section_counter += 1
            body.extend(make_main_header(r_num, "Experience"))

            exp_rows = []
            for job in resume.work_experience:
                date_str = f"{job.start_date} — {job.end_date}" if job.start_date and job.end_date else (job.start_date or job.end_date or "")

                comp_loc = job.company
                if job.location:
                    comp_loc += f" &middot; {job.location}"

                item_flowables = [
                    Table(
                        [[
                            Paragraph(f"<b>{job.job_title}</b>", S["AuJobTitle"]),
                            Paragraph(date_str, S["AuDate"]),
                        ]],
                        colWidths=[MAIN_MAX_W - 20 - 90, 90],
                        style=[
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('LEFTPADDING', (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING', (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                        ]
                    ),
                    Paragraph(f"<i>{comp_loc}</i>", S["AuCompany"]),
                ]
                if job.bullet_points:
                    for b in job.bullet_points:
                        item_flowables.append(Paragraph(f"• {b.lstrip('•- ')}", S["AuBullet"]))

                dot = AurelianTimelineDot(dot_color=bronze_color)
                exp_rows.append([dot, item_flowables])

            exp_table = Table(exp_rows, colWidths=[16, MAIN_MAX_W - 16])
            exp_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (1, -1), 0.8, hairline_color),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 0),
                ("LEFTPADDING", (1, 0), (1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            body.append(exp_table)
            body.append(Spacer(1, spacer_h * 0.5))

    # SECTION III: KEY PROJECTS
    def add_projects():
        nonlocal section_counter
        if resume.show_projects and resume.projects:
            r_num = romans[min(section_counter - 1, len(romans) - 1)]
            section_counter += 1
            body.extend(make_main_header(r_num, "Key Projects"))

            proj_rows = []
            for proj in resume.projects:
                item_flowables = [
                    Paragraph(f"<b>{proj.name}</b>", S["AuProjTitle"]),
                ]
                if proj.technologies:
                    tech_str = " &middot; ".join(proj.technologies)
                    item_flowables.append(Paragraph(f"<i>Technologies: {tech_str}</i>", S["AuProjSub"]))

                if hasattr(proj, "description_bullets") and proj.description_bullets:
                    for b in proj.description_bullets:
                        item_flowables.append(Paragraph(f"• {b.lstrip('•- ')}", S["AuBullet"]))

                dot = AurelianTimelineDot(dot_color=bronze_color)
                proj_rows.append([dot, item_flowables])

            proj_table = Table(proj_rows, colWidths=[16, MAIN_MAX_W - 16])
            proj_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (1, -1), 0.8, hairline_color),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 0),
                ("LEFTPADDING", (1, 0), (1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]))
            body.append(proj_table)
            body.append(Spacer(1, spacer_h * 0.5))

    # SECTION IV: CERTIFICATIONS & LICENSES
    def add_certifications():
        nonlocal section_counter
        if resume.show_certifications and resume.certifications:
            r_num = romans[min(section_counter - 1, len(romans) - 1)]
            section_counter += 1
            body.extend(make_main_header(r_num, "Certifications & Credentials"))

            cert_rows = []
            for cert in resume.certifications:
                year_str = f" <font color='{bronze_hex}' size='{body_size - 1.2}'>({cert.year})</font>" if cert.year else ""
                item_flowables = [
                    Paragraph(f"<b>{cert.name}</b> — <i>{cert.issuer}</i>{year_str}", S["AuJobTitle"]),
                ]
                dot = AurelianTimelineDot(dot_color=bronze_color)
                cert_rows.append([dot, item_flowables])

            cert_table = Table(cert_rows, colWidths=[16, MAIN_MAX_W - 16])
            cert_table.setStyle(TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBEFORE", (1, 0), (1, -1), 0.8, hairline_color),
                ("LEFTPADDING", (0, 0), (0, -1), 0),
                ("RIGHTPADDING", (0, 0), (0, -1), 0),
                ("LEFTPADDING", (1, 0), (1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            body.append(cert_table)
            body.append(Spacer(1, spacer_h * 0.5))

    # Build sequence
    add_education()
    add_experience()
    add_projects()
    add_certifications()

    # Signature line removed as requested

    footer_flow = render_cv_portfolio_footer(resume, primary_color=bronze_color, font_reg=f_reg, font_bold=f_bold, alignment=TA_LEFT)
    if footer_flow:
        body.extend(footer_flow)

    buf = io.BytesIO()
    top_m = 32 if font_scale == "spacious" else (16 if font_scale == "compact" else 20)
    bot_m = 28 if font_scale == "spacious" else (14 if font_scale == "compact" else 16)
    right_m = 26 if font_scale == "spacious" else (18 if font_scale == "compact" else 22)
    if getattr(resume, "custom_page_margin", None) is not None:
        right_m = max(14.0, float(resume.custom_page_margin))
        top_m = max(14.0, round(float(resume.custom_page_margin) * 0.8, 1))
        bot_m = max(14.0, round(float(resume.custom_page_margin) * 0.8, 1))
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MAIN_LEFT,
        rightMargin=right_m,
        topMargin=top_m,
        bottomMargin=bot_m
    )
    doc.build(body, onFirstPage=on_first_page, onLaterPages=on_later_pages)
    buf.seek(0)
    return buf.getvalue()
