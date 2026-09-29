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


# ─────────────────────────────────────────────────────────────────────────────
# UNICODE / ENCODING SANITIZATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

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
    Sanitize text for ReportLab standard PostScript fonts (WinAnsi / cp1252).
    Converts unsupported Unicode characters (like Welsh 'ŵ', Slavic 'č', etc.)
    into their ASCII/Latin-1 compatible equivalents using NFKD decomposition
    and a fallback character map. Prevents missing-glyph black boxes (■ / tofu).
    """
    if not text:
        return ""
    if not isinstance(text, str):
        text = str(text)

    out = []
    for ch in text:
        # 1. Quick check: is character natively valid in cp1252 (WinAnsi)?
        try:
            ch.encode("cp1252")
            out.append(ch)
            continue
        except UnicodeEncodeError:
            pass

        # 2. Check explicit fallback map
        if ch in _CHAR_FALLBACK_MAP:
            out.append(_CHAR_FALLBACK_MAP[ch])
            continue

        # 3. Unicode NFKD decomposition (e.g. 'ŵ' -> 'w' + combining circumflex)
        decomposed = unicodedata.normalize("NFKD", ch)
        stripped = "".join(c for c in decomposed if not unicodedata.combining(c))

        # 4. Check if stripped version is cp1252 safe
        cleaned = ""
        for sc in stripped:
            try:
                sc.encode("cp1252")
                cleaned += sc
            except UnicodeEncodeError:
                pass

        if cleaned:
            out.append(cleaned)
        else:
            # Safe ascii fallback
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
    font_name: str = "Helvetica"
) -> float:
    """
    Draws a skill progress bar cleanly bounded within [y_top - 16.0, y_top].
    - Text baseline: y_top - 7.5 (safely below y_top)
    - Progress bar: y_top - 10.5 down to y_top - 14.0 (3.5pt bar height)
    - Returns exact height consumed: 16.0pt
    """
    pct = max(10, min(100, int(level)))
    slot_h = 16.0

    fn_bold = f"{font_name}-Bold" if "Bold" not in font_name and font_name != "Times-Roman" else ("Times-Bold" if font_name == "Times-Roman" else font_name)
    fn_reg = font_name.replace("-Bold", "")

    # 1. Text sits safely below y_top
    text_y = y_top - 7.5
    canvas.setFont(fn_bold, 7.5)
    canvas.setFillColor(text_color)
    safe_name = _clean_pdf_text(skill_name)[:24]
    canvas.drawString(x, text_y, safe_name)

    canvas.setFont(fn_reg, 7.0)
    canvas.setFillColor(pct_color)
    canvas.drawRightString(x + w, text_y, f"{pct}%")

    # 2. Bar sits safely below text
    bar_top = y_top - 10.5
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
