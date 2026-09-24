"""
Cover Letter PDF Generator:
- Professional letterhead layout
- Supports handwritten script, draw, and upload signatures
- Dynamic letterhead styles (modern_banner, classic_corporate, minimal_clean)
- Official watermark badge support for free evaluation tiers
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
