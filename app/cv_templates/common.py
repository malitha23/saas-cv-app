"""
Shared Common Utilities for PDF CV and Cover Letter Templates.
Contains styling helpers, color converters, fonts, avatar loading,
skill progress bar rendering, and watermark logic.
"""

import io
import os
import ssl
import base64
import socket
import ipaddress
import unicodedata
import urllib.request
import urllib.parse
from typing import Optional, List, Any, Dict, Tuple

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Paragraph, Spacer, HRFlowable, Table, TableStyle, SimpleDocTemplate, KeepTogether, Image as RLImage
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.schemas import TailoredResume


# ─────────────────────────────────────────────────────────────────────────────
# UNICODE / TRUE-TYPE FONT INITIALIZATION & ENCODING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_FONTS_INITIALIZED = False
_VALID_UNICODE_GLYPHS = set()


def _init_pdf_fonts():
    """
    Register Unicode-capable TrueType fonts (Roboto) so special Latin and international
    characters (such as Welsh 'ŵ', Slavic 'č', Turkish 'ş', smart punctuation, etc.)
    render natively and crisply in PDFs without missing-glyph black boxes (■) or loss of accents.
    """
    global _FONTS_INITIALIZED, _VALID_UNICODE_GLYPHS
    if _FONTS_INITIALIZED:
        return
    _FONTS_INITIALIZED = True

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonts_dir = os.path.join(base_dir, "fonts")

    reg_roboto = os.path.join(fonts_dir, "Roboto-Regular.ttf")
    bold_roboto = os.path.join(fonts_dir, "Roboto-Bold.ttf")
    ital_roboto = os.path.join(fonts_dir, "Roboto-Italic.ttf")

    # 1. Register Roboto for Helvetica / default sans-serif font family
    if os.path.exists(reg_roboto):
        try:
            r_font = TTFont("Helvetica", reg_roboto)
            pdfmetrics.registerFont(r_font)
            _VALID_UNICODE_GLYPHS.update(r_font.face.charToGlyph.keys())

            if os.path.exists(bold_roboto):
                b_font = TTFont("Helvetica-Bold", bold_roboto)
                pdfmetrics.registerFont(b_font)
                _VALID_UNICODE_GLYPHS.update(b_font.face.charToGlyph.keys())
            if os.path.exists(ital_roboto):
                i_font = TTFont("Helvetica-Oblique", ital_roboto)
                pdfmetrics.registerFont(i_font)
                _VALID_UNICODE_GLYPHS.update(i_font.face.charToGlyph.keys())

            pdfmetrics.registerFontFamily(
                "Helvetica",
                normal="Helvetica",
                bold="Helvetica-Bold" if os.path.exists(bold_roboto) else "Helvetica",
                italic="Helvetica-Oblique" if os.path.exists(ital_roboto) else "Helvetica",
            )
        except Exception as e:
            print(f"[pdf_generator] Roboto font registration warning: {e}")

    # 2. Register Windows Times-Roman & Courier if available
    win_fonts = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")
    if os.path.isdir(win_fonts):
        t_reg = os.path.join(win_fonts, "times.ttf")
        t_bd = os.path.join(win_fonts, "timesbd.ttf")
        t_it = os.path.join(win_fonts, "timesi.ttf")
        if os.path.exists(t_reg):
            try:
                t_font = TTFont("Times-Roman", t_reg)
                pdfmetrics.registerFont(t_font)
                _VALID_UNICODE_GLYPHS.update(t_font.face.charToGlyph.keys())
                if os.path.exists(t_bd):
                    pdfmetrics.registerFont(TTFont("Times-Bold", t_bd))
                if os.path.exists(t_it):
                    pdfmetrics.registerFont(TTFont("Times-Italic", t_it))
                pdfmetrics.registerFontFamily("Times-Roman", normal="Times-Roman", bold="Times-Bold", italic="Times-Italic")
            except Exception:
                pass

        c_reg = os.path.join(win_fonts, "cour.ttf")
        c_bd = os.path.join(win_fonts, "courbd.ttf")
        c_it = os.path.join(win_fonts, "couri.ttf")
        if os.path.exists(c_reg):
            try:
                c_font = TTFont("Courier", c_reg)
                pdfmetrics.registerFont(c_font)
                _VALID_UNICODE_GLYPHS.update(c_font.face.charToGlyph.keys())
                if os.path.exists(c_bd):
                    pdfmetrics.registerFont(TTFont("Courier-Bold", c_bd))
                if os.path.exists(c_it):
                    pdfmetrics.registerFont(TTFont("Courier-Oblique", c_it))
                pdfmetrics.registerFontFamily("Courier", normal="Courier", bold="Courier-Bold", italic="Courier-Oblique")
            except Exception:
                pass


# Initialize font metrics on module load
try:
    _init_pdf_fonts()
except Exception:
    pass


# Explicit fallback map for Unicode characters that don't decompose cleanly into ASCII/Latin-1
_CHAR_FALLBACK_MAP = {
    '\u0142': 'l', '\u0141': 'L',   # ł, Ł
    '\u0111': 'd', '\u0110': 'D',   # đ, Đ
    '\u0127': 'h', '\u0126': 'H',   # ħ, Ħ
    '\u0131': 'i', '\u0130': 'I',   # Turkish dotless i, dotted I
    '\u0153': 'oe', '\u0152': 'OE', # œ, Œ
    '\u00e6': 'ae', '\u00c6': 'AE', # æ, Æ
    '\u015f': 's', '\u015e': 'S',   # ş, Ş
    '\u0219': 's', '\u0218': 'S',   # ș, Ș
    '\u021b': 't', '\u021a': 'T',   # ț, Ț
    '\u011f': 'g', '\u011e': 'G',   # ğ, Ğ
    '\u200b': '',                   # zero-width space
    '\u200e': '',                   # LTR mark
    '\u200f': '',                   # RTL mark
    '\ufeff': '',                   # BOM
    '\u2028': '\n',                 # line separator
    '\u2029': '\n',                 # paragraph separator
    '–': '–',                       # en-dash (0x96 in cp1252)
    '—': '—',                       # em-dash (0x97 in cp1252)
    '‘': "'", '’': "'",             # curly single quotes
    '“': '"', '”': '"',             # curly double quotes
    '•': '•',                       # bullet (0x95 in cp1252)
}


def _clean_pdf_text(text: Optional[str]) -> str:
    """
    Sanitize text for ReportLab PDF rendering.
    Preserves all valid Unicode characters supported by registered TrueType fonts
    (e.g., Welsh 'ŵ', Slavic 'č', Turkish 'ş', smart punctuation, etc.).
    Only strips truly unsupported characters or control marks to guarantee zero '■' boxes.
    """
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)

    _init_pdf_fonts()

    out = []
    for ch in text:
        code = ord(ch)

        # 1. If character is natively supported in the registered Unicode font, PRESERVE IT!
        if _VALID_UNICODE_GLYPHS and code in _VALID_UNICODE_GLYPHS:
            out.append(ch)
            continue

        # 2. Check explicit fallback map
        if ch in _CHAR_FALLBACK_MAP:
            out.append(_CHAR_FALLBACK_MAP[ch])
            continue

        # 3. Quick check: is character natively valid in cp1252?
        try:
            ch.encode("cp1252")
            out.append(ch)
            continue
        except UnicodeEncodeError:
            pass

        # 4. Unicode NFKD decomposition for characters not in font glyph set
        decomposed = unicodedata.normalize("NFKD", ch)
        stripped = "".join(
            c for c in decomposed
            if not unicodedata.combining(c) and (not _VALID_UNICODE_GLYPHS or ord(c) in _VALID_UNICODE_GLYPHS)
        )

        if stripped:
            out.append(stripped)
        else:
            ascii_repr = ch.encode("ascii", "replace").decode("ascii")
            if ascii_repr != "?":
                out.append(ascii_repr)
            else:
                out.append(" ")

    return "".join(out)


def _sanitize_pdf_data(obj):
    """
    Recursively cleans all strings in a data object (Pydantic model, dict, list, or primitive)
    to ensure all text renders cleanly in ReportLab without missing-glyph black boxes (■).
    """
    if obj is None:
        return None
    if isinstance(obj, str):
        return _clean_pdf_text(obj)
    elif isinstance(obj, list):
        for i in range(len(obj)):
            obj[i] = _sanitize_pdf_data(obj[i])
        return obj
    elif isinstance(obj, dict):
        for k, v in list(obj.items()):
            obj[k] = _sanitize_pdf_data(v)
        return obj
    elif hasattr(obj, "__dict__"):
        for k, v in list(obj.__dict__.items()):
            if not k.startswith("_"):
                try:
                    setattr(obj, k, _sanitize_pdf_data(v))
                except Exception:
                    pass
        return obj
    return obj



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
    if not text or not str(text).strip():
        return 0.0
    cleaned_text = _clean_pdf_text(text)
    p = Paragraph(cleaned_text, style)
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
    font_name: str = "Helvetica",
    font_size: float = 7.5
) -> float:
    """
    Draws a skill progress bar cleanly bounded within [y_top - slot_h, y_top].
    Scales dynamically with user-selected font size.
    """
    pct = max(10, min(100, int(level)))
    slot_h = max(15.0, font_size + 8.5)

    fn_bold = f"{font_name}-Bold" if "Bold" not in font_name and font_name != "Times-Roman" else ("Times-Bold" if font_name == "Times-Roman" else font_name)
    fn_reg = font_name.replace("-Bold", "")

    # 1. Text sits safely below y_top
    text_y = y_top - font_size
    canvas.setFont(fn_bold, font_size)
    canvas.setFillColor(text_color)
    safe_name = _clean_pdf_text(skill_name)[:24]
    canvas.drawString(x, text_y, safe_name)

    canvas.setFont(fn_reg, max(6.0, font_size - 0.5))
    canvas.setFillColor(pct_color)
    canvas.drawRightString(x + w, text_y, f"{pct}%")

    # 2. Bar sits safely below text
    bar_top = text_y - 3.0
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


# ─────────────────────────────────────────────────────────────────────────────
# PUBLISHED PORTFOLIO CV LINK & FOOTER INTEGRATION
# ─────────────────────────────────────────────────────────────────────────────

def get_published_portfolio_url(resume: TailoredResume, position: Optional[str] = None) -> Optional[str]:
    """
    Returns the public web portfolio URL for the candidate's CV if enabled.
    Returns None if:
    - User has disabled show_portfolio_link (getattr(resume, 'show_portfolio_link', True) is False)
    - position == 'header' and show_portfolio_header is False
    - position == 'footer' and show_portfolio_footer is False
    - No candidate information or identifier exists to construct a portfolio URL
    """
    if not getattr(resume, "show_portfolio_link", True):
        return None

    if position == "header" and not getattr(resume, "show_portfolio_header", True):
        return None
    if position == "footer" and not getattr(resume, "show_portfolio_footer", True):
        return None

    info = getattr(resume, "personal_info", None)
    if not info:
        return None

    import re
    # Base URL for default DreemFolio public path
    base_url = os.getenv("APP_BASE_URL", "https://www.dreemfolio.com").rstrip("/")

    # 1. Custom domain if candidate has one configured
    if getattr(info, "custom_domain", None) and info.custom_domain.strip():
        cd = info.custom_domain.strip()
        if not cd.startswith("http://") and not cd.startswith("https://"):
            return f"https://{cd}"
        return cd

    # 2. Explicitly assigned portfolio_url on resume
    p_url = getattr(resume, "portfolio_url", None)
    if p_url and isinstance(p_url, str) and p_url.strip():
        clean_u = p_url.strip()
        if clean_u.startswith("http://") or clean_u.startswith("https://"):
            return clean_u
        return f"{base_url}/{clean_u.lstrip('/')}"

    # 3. Explicitly assigned portfolio_slug on resume
    p_slug = getattr(resume, "portfolio_slug", None)
    if p_slug and isinstance(p_slug, str) and p_slug.strip():
        clean_slug = p_slug.strip().lstrip("/").replace("p/", "")
        return f"{base_url}/p/{clean_slug}"

    # 4. Check personal_info.portfolio if defined
    cand_p = getattr(info, "portfolio", None)
    if cand_p and isinstance(cand_p, str) and cand_p.strip():
        clean_cp = cand_p.strip()
        if clean_cp.startswith("http://") or clean_cp.startswith("https://"):
            return clean_cp
        if clean_cp.startswith("/p/"):
            return f"{base_url}{clean_cp}"
        return f"https://{clean_cp}"

    # 5. Database lookup for Prebuilt Candidate Profile by email or full name
    cand_email = getattr(info, "email", None)
    cand_name = getattr(info, "full_name", None)
    try:
        from app.database import SessionLocal
        from app.models import PrebuiltCandidateProfile
        from sqlalchemy import select, func
        with SessionLocal() as db_session:
            profile = None
            if cand_email and cand_email.strip():
                profile = db_session.scalar(
                    select(PrebuiltCandidateProfile).where(
                        func.lower(PrebuiltCandidateProfile.candidate_email) == cand_email.strip().lower()
                    ).order_by(PrebuiltCandidateProfile.id.desc())
                )
            if not profile and cand_name and cand_name.strip():
                profile = db_session.scalar(
                    select(PrebuiltCandidateProfile).where(
                        func.lower(PrebuiltCandidateProfile.candidate_name) == cand_name.strip().lower()
                    ).order_by(PrebuiltCandidateProfile.id.desc())
                )
            if profile and profile.portfolio_slug:
                return f"{base_url}/p/{profile.portfolio_slug}"
    except Exception:
        pass

    # 6. Fallback: Clean slug generated from candidate full name
    if cand_name and cand_name.strip():
        name_slug = re.sub(r'[^a-zA-Z0-9]', '-', cand_name.lower()).strip('-')
        name_slug = re.sub(r'-+', '-', name_slug)
        if name_slug:
            return f"{base_url}/p/{name_slug}"

    return None


def render_cv_portfolio_footer(
    resume: TailoredResume,
    primary_color=None,
    font_reg: str = "Helvetica",
    font_bold: str = "Helvetica-Bold",
    font_size: float = 8.0,
    leading: float = 10.5,
    alignment: int = TA_CENTER,
    spacer_before: float = 12.0,
) -> List[Any]:
    """
    Renders an ATS-friendly, elegant footer banner flowable with the published portfolio link.
    Returns a list of Flowables (Spacer, KeepTogether[HRFlowable, Paragraph]) or empty list if not published / hidden.
    """
    pub_url = get_published_portfolio_url(resume, position="footer")
    if not pub_url:
        return []

    if primary_color is None:
        primary_color = colors.HexColor("#2563EB")
    elif isinstance(primary_color, str):
        primary_color = colors.HexColor(primary_color)

    color_hex = primary_color.hexval() if hasattr(primary_color, "hexval") else "#2563EB"

    style = ParagraphStyle(
        f"CvPortfolioFooter_{id(resume)}",
        fontName=font_reg,
        fontSize=font_size,
        leading=leading,
        alignment=alignment,
        textColor=colors.HexColor("#475569"),
        spaceAfter=0,
    )

    return [
        Spacer(1, spacer_before),
        KeepTogether([
            HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#CBD5E1"), spaceBefore=4.0, spaceAfter=4.5),
            Paragraph(
                f"<b>More on My Portfolio:</b> <a href='{pub_url}'><u><font color='{color_hex}'>{pub_url}</font></u></a> &nbsp;<font color='#94A3B8'>•</font>&nbsp; <font color='#64748B'>Interactive Projects & Verified Credentials</font>",
                style
            )
        ])
    ]


def resolve_custom_layout_metrics(
    resume: TailoredResume,
    base_body_size: float,
    base_body_leading: float,
    base_sec_size: float,
    base_spacer_h: float,
    base_margin: float,
    base_side_w: Optional[float] = None,
) -> Tuple[float, float, float, float, float, Optional[float]]:
    """
    Applies custom layout sliders (font size, section spacing, page margin, sidebar width)
    if set on the resume. When the custom attributes are None, preserves the template's
    built-in styling metrics completely untouched.

    Returns:
        (body_size, body_leading, sec_size, spacer_h, margin, side_w)
    """
    body_size = base_body_size
    body_leading = base_body_leading
    sec_size = base_sec_size
    spacer_h = base_spacer_h
    margin = base_margin
    side_w = base_side_w

    # 1. Custom Font Size
    c_font = getattr(resume, "custom_font_size", None)
    if c_font is not None:
        try:
            val = float(c_font)
            if 6.0 <= val <= 16.0:
                scale = val / (base_body_size if base_body_size > 0 else 9.0)
                body_size = round(val, 2)
                body_leading = round(base_body_leading * scale, 1)
                sec_size = round(base_sec_size * scale, 1)
        except (ValueError, TypeError):
            pass

    # 2. Custom Section Spacing / Margin
    c_space = getattr(resume, "custom_section_spacing", None)
    if c_space is not None:
        try:
            val = float(c_space)
            if 0.5 <= val <= 30.0:
                spacer_h = round(val, 2)
        except (ValueError, TypeError):
            pass

    # 3. Custom Page Margin / Padding
    c_margin = getattr(resume, "custom_page_margin", None)
    if c_margin is not None:
        try:
            val = float(c_margin)
            if 10.0 <= val <= 60.0:
                margin = round(val, 2)
        except (ValueError, TypeError):
            pass

    # 4. Custom Sidebar Column Width
    c_side = getattr(resume, "custom_sidebar_width", None)
    if side_w is not None and c_side is not None:
        try:
            val = float(c_side)
            if 120.0 <= val <= 260.0:
                side_w = round(val, 2)
        except (ValueError, TypeError):
            pass

    return (body_size, body_leading, sec_size, spacer_h, margin, side_w)

