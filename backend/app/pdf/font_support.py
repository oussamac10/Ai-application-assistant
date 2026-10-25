"""Bundled OFL Noto Sans / Noto Sans Arabic font embedding & PDF preview watermarking (S1-04).

Uses PyMuPDF (`fitz`) `insert_htmlbox` + `fitz.Archive` backed by bundled
`NotoSans-Regular.ttf` and `NotoSansArabic-Regular.ttf` so dynamic overlays and
Unicode AcroForm fallbacks embed `Identity-H` Type0 fonts with native HarfBuzz
glyph shaping (Arabic contextual forms + ligatures) and Unicode BiDi RTL alignment.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

FONTS_DIR = Path(__file__).resolve().parent / "fonts"
NOTO_SANS_REGULAR_PATH = FONTS_DIR / "NotoSans-Regular.ttf"
NOTO_SANS_ARABIC_REGULAR_PATH = FONTS_DIR / "NotoSansArabic-Regular.ttf"

DEFAULT_PREVIEW_WATERMARK = "PREVIEW — NOT FOR OFFICIAL SUBMISSION"


def contains_rtl_script(text: str) -> bool:
    """Returns True if `text` contains Arabic, Hebrew, Syriac, or Thaana codepoints."""
    for ch in text:
        cp = ord(ch)
        if 0x0590 <= cp <= 0x08FF or 0xFB1D <= cp <= 0xFDFF or 0xFE70 <= cp <= 0xFEFF:
            return True
    return False


_NON_ARABIC_RUN_RE = re.compile(
    r"([^\u0600-\u06FF\u0750-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\s]+)"
)


def _build_escaped_html_runs(text: str, *, is_rtl: bool) -> str:
    """Escapes `text` safely as HTML and wraps non-Arabic runs inside RTL strings
    in `<span class="lat">` so MuPDF renders Latin/Cyrillic/em-dash glyphs with
    `NotoSans` instead of `.notdef` tofu boxes from `NotoSansArabic`.
    """
    if not is_rtl:
        return html.escape(text, quote=True)
    parts: list[str] = []
    last_end = 0
    for match in _NON_ARABIC_RUN_RE.finditer(text):
        start, end = match.span()
        if start > last_end:
            parts.append(html.escape(text[last_end:start], quote=True))
        parts.append(
            f'<span class="lat">{html.escape(match.group(0), quote=True)}</span>'
        )
        last_end = end
    if last_end < len(text):
        parts.append(html.escape(text[last_end:], quote=True))
    return "".join(parts)


def is_latin1_safe(text: str) -> bool:
    """Returns True when every character in `text` encodes cleanly in WinAnsi / Latin-1."""
    try:
        text.encode("cp1252")
        return True
    except UnicodeEncodeError:
        return False


def draw_unicode_text_in_box(
    page: Any,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    multiline: bool,
    mask_dots: bool = False,
) -> None:
    """Draws Unicode `text` inside `(x, y, width, height)` in PDF points using
    bundled `NotoSans` / `NotoSansArabic` TrueType fonts (`Identity-H` Type0).
    """
    import fitz

    if not text or not text.strip():
        return

    is_rtl = contains_rtl_script(text)

    if multiline:
        base_font_size = 9.5
        min_scale = 0.55
    else:
        if height <= 13.0:
            base_font_size = min(max(height * 0.74, 7.5), 9.0)
        else:
            base_font_size = min(max(height * 0.58, 7.0), 11.0)
        estimated_char_width = base_font_size * 0.52
        max_chars_at_base = max(int((width - 4.0) / max(estimated_char_width, 1.0)), 1)
        if len(text) > max_chars_at_base:
            scaled = base_font_size * (max_chars_at_base / len(text))
            base_font_size = max(scaled, 6.0)
        min_scale = 0.45

    if mask_dots:
        approx_text_w = min(len(text) * base_font_size * 0.56 + 6.0, width)
        if is_rtl:
            mask_rect = fitz.Rect(
                max(x, x + width - approx_text_w),
                y + 1.0,
                x + width,
                y + height,
            )
        else:
            mask_rect = fitz.Rect(
                x,
                y + 1.0,
                min(x + approx_text_w, x + width),
                y + height,
            )
        shape = page.new_shape()
        shape.draw_rect(mask_rect)
        shape.finish(width=0, color=None, fill=(1.0, 1.0, 1.0))
        shape.commit()

    left = x + 2.0
    right = x + max(width - 2.0, 6.0)
    if multiline:
        top = y + 1.0
        bottom = y + max(height - 1.0, base_font_size * 1.45)
    else:
        # Ensure single-line boxes (such as 11.5pt underline boxes) have enough
        # vertical layout box height for Noto Sans ascenders/descenders without
        # clipping, anchored cleanly to the writing baseline.
        needed_h = max(height, base_font_size * 1.55)
        if height <= 13.5:
            bottom = y + height + 1.0
            top = max(0.0, bottom - needed_h)
        else:
            pad_top = max((height - needed_h) / 2.0, 0.5)
            top = y + pad_top
            bottom = max(y + height, top + needed_h)

    box_rect = fitz.Rect(left, top, right, bottom)

    font_stack = (
        "'NotoSansArabic', 'NotoSans', sans-serif"
        if is_rtl
        else "'NotoSans', 'NotoSansArabic', sans-serif"
    )
    align = "right" if is_rtl else "left"
    white_space = "pre-wrap" if multiline else "nowrap"

    # MuPDF's HTML engine natively applies Unicode BiDi + HarfBuzz shaping to RTL
    # runs; omitting CSS `direction: rtl` avoids MuPDF's double-inversion of
    # `text-align: right` so RTL strings align flush against the right edge.
    css = (
        "@font-face { font-family: 'NotoSans'; src: url('NotoSans-Regular.ttf'); }\n"
        "@font-face { font-family: 'NotoSansArabic'; src: url('NotoSansArabic-Regular.ttf'); }\n"
        f"p.val {{ font-family: {font_stack}; font-size: {base_font_size:.2f}pt; "
        f"line-height: 1.15; color: #0f1729; text-align: {align}; "
        f"white-space: {white_space}; margin: 0; padding: 0; }}\n"
        "span.lat { font-family: 'NotoSans', sans-serif; }"
    )
    inner_html = _build_escaped_html_runs(text, is_rtl=is_rtl)
    html_snippet = f'<p class="val">{inner_html}</p>'

    archive = fitz.Archive(str(FONTS_DIR))
    spare_height, _scale = page.insert_htmlbox(
        box_rect,
        html_snippet,
        css=css,
        archive=archive,
        scale_low=min_scale,
    )

    if spare_height < 0 and not multiline:
        # Ultra-wide single-line value fallback: allow wrapping inside expanded box
        wrap_css = css.replace("white-space: nowrap;", "white-space: normal;")
        expanded_rect = fitz.Rect(left, max(0.0, top - 2.0), right, bottom + 6.0)
        page.insert_htmlbox(
            expanded_rect,
            html_snippet,
            css=wrap_css,
            archive=archive,
            scale_low=0.35,
        )


def apply_preview_watermark(
    pdf_path: Path,
    watermark_text: str = DEFAULT_PREVIEW_WATERMARK,
) -> bytes:
    """Stamps a diagonal translucent watermark across every page of `pdf_path`
    and returns the resulting PDF bytes without mutating `FormExport` records.
    """
    import fitz

    doc = fitz.open(pdf_path)
    try:
        font_file = (
            str(NOTO_SANS_REGULAR_PATH) if NOTO_SANS_REGULAR_PATH.is_file() else None
        )
        for page in doc:
            rect = page.rect
            cx = float(rect.width) / 2.0
            cy = float(rect.height) / 2.0
            pivot = fitz.Point(cx, cy)
            # Wide centered banner rotated -38 degrees across the page diagonal
            banner_w = float(rect.width) * 1.15
            banner_h = 90.0
            banner_rect = fitz.Rect(
                cx - banner_w / 2.0,
                cy - banner_h / 2.0,
                cx + banner_w / 2.0,
                cy + banner_h / 2.0,
            )
            page.insert_textbox(
                banner_rect,
                watermark_text,
                fontsize=22.0,
                fontname="notosans-wm" if font_file else "helv",
                fontfile=font_file,
                color=(0.55, 0.12, 0.12),
                fill_opacity=0.18,
                align=fitz.TEXT_ALIGN_CENTER,
                morph=(pivot, fitz.Matrix(-38.0)),
                overlay=True,
            )
        return bytes(doc.tobytes(garbage=1, deflate=True))
    finally:
        doc.close()
