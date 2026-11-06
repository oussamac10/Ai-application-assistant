from __future__ import annotations

import html

import fitz
from reportlab.graphics import renderSVG
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing

from app.pdf.font_support import FONTS_DIR


def generate_qr_svg(url: str, size: int = 300) -> str:
    """Generates an SVG string representation of a QR code targeting `url`."""
    drawing = Drawing(size, size)
    widget = qr.QrCodeWidget(url)
    widget.barWidth = size
    widget.barHeight = size
    widget.qrVersion = 1  # will auto-expand if URL is longer
    drawing.add(widget)
    return str(renderSVG.drawToString(drawing))


def generate_qr_png(url: str, size: int = 300) -> bytes:
    """Generates 300 DPI PNG bytes of a QR code targeting `url`."""
    svg_str = generate_qr_svg(url, size=size)
    svg_doc = fitz.open(stream=svg_str.encode("utf-8"), filetype="svg")
    page = svg_doc[0]
    pix = page.get_pixmap(dpi=300)
    return bytes(pix.tobytes("png"))


def generate_counter_poster_pdf(
    *,
    form_name: str,
    target_url: str,
    org_name: str | None = None,
    org_logo_bytes: bytes | None = None,
    is_verified_government: bool = False,
    instructions: str | None = None,
) -> bytes:
    """Generates an official A4 printable counter display poster in PDF format.

    Equipped with a large, scannable QR code and 8-language callout so citizens
    at physical counters or waiting rooms can scan with their smartphone camera
    and complete the document in their native language for free.
    """
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # Standard A4 portrait in points

    # 1. Background and Framing
    # Draw soft top decorative header band
    header_rect = fitz.Rect(0, 0, 595, 120)
    page.draw_rect(header_rect, color=None, fill=(0.96, 0.97, 0.99))  # Slate 50
    page.draw_line(
        fitz.Point(0, 120), fitz.Point(595, 120), color=(0.88, 0.91, 0.94), width=1
    )

    # Draw bottom footer band
    footer_rect = fitz.Rect(0, 770, 595, 842)
    page.draw_rect(footer_rect, color=None, fill=(0.96, 0.97, 0.99))
    page.draw_line(
        fitz.Point(0, 770), fitz.Point(595, 770), color=(0.88, 0.91, 0.94), width=1
    )

    # 2. Draw Authority Logo if provided
    logo_offset_x = 45.0
    if org_logo_bytes:
        try:
            logo_rect = fitz.Rect(45, 30, 105, 90)
            page.insert_image(logo_rect, stream=org_logo_bytes, keep_proportion=True)
            logo_offset_x = 118.0
        except Exception:
            logo_offset_x = 45.0

    # 3. Insert Header Text (Authority & Badge) via HTML box
    archive = fitz.Archive(str(FONTS_DIR))
    css = """
    @font-face { font-family: 'NotoSans'; src: url('NotoSans-Regular.ttf'); }
    @font-face { font-family: 'NotoSansArabic'; src: url('NotoSansArabic-Regular.ttf'); }
    body { font-family: 'NotoSans', 'NotoSansArabic', sans-serif; margin: 0; color: #0f172a; }
    .org-title { font-size: 16pt; font-weight: bold; color: #0f172a; line-height: 1.2; }
    .badge { display: inline-block; font-size: 8.5pt; font-weight: bold; color: #065f46; background-color: #d1fae5; border: 1px solid #a7f3d0; padding: 2px 8px; border-radius: 9999px; margin-top: 4px; }
    .form-heading { font-size: 21pt; font-weight: bold; color: #1e3a8a; line-height: 1.2; text-align: center; }
    .subtext { font-size: 11pt; color: #475569; text-align: center; line-height: 1.4; margin-top: 6px; }
    .url-label { font-size: 10pt; font-family: monospace; font-weight: bold; color: #2563eb; text-align: center; }
    .lang-item { font-size: 9pt; color: #334155; line-height: 1.35; margin-bottom: 5px; }
    .lang-name { font-weight: bold; color: #0f172a; }
    .arabic { font-family: 'NotoSansArabic', 'NotoSans', sans-serif; direction: rtl; text-align: right; }
    .footer-text { font-size: 8.5pt; font-weight: bold; color: #475569; text-align: center; line-height: 1.4; }
    """

    display_org = org_name or "Official Municipal Citizen Service"
    badge_html = (
        '<div class="badge">✓ Offiziell verifizierte Behörde / Verified Official Authority</div>'
        if is_verified_government
        else '<div class="badge" style="color: #1e40af; background-color: #dbeafe; border-color: #bfdbfe;">Öffentlicher Bürgerservice / Official Public Portal</div>'
    )
    header_html = f"""
    <div>
        <div class="org-title">{html.escape(display_org)}</div>
        {badge_html}
    </div>
    """
    page.insert_htmlbox(
        fitz.Rect(logo_offset_x, 32, 550, 110),
        header_html,
        css=css,
        archive=archive,
    )

    # 4. Form Title & Instructions (Center block)
    form_intro_html = f"""
    <div>
        <div class="form-heading">{html.escape(form_name)}</div>
        <div class="subtext">
            Digitale & mehrsprachige Antragsstellung direkt auf Ihrem Smartphone.<br/>
            Digital & multilingual application assistance right on your smartphone.
        </div>
    </div>
    """
    page.insert_htmlbox(
        fitz.Rect(45, 140, 550, 225),
        form_intro_html,
        css=css,
        archive=archive,
    )

    # 5. Central QR Code Card
    qr_card_rect = fitz.Rect(185, 230, 410, 475)
    page.draw_rect(
        qr_card_rect,
        color=(0.85, 0.88, 0.92),
        fill=(1.0, 1.0, 1.0),
        radius=0.06,
        width=1.5,
    )

    # Draw QR code inside the card
    qr_png = generate_qr_png(target_url, size=280)
    qr_image_rect = fitz.Rect(205, 245, 390, 430)
    page.insert_image(qr_image_rect, stream=qr_png)

    # Direct short URL display below QR
    short_url_display = target_url.replace("https://", "").replace("http://", "")
    page.insert_htmlbox(
        fitz.Rect(190, 442, 405, 468),
        f'<div class="url-label">{html.escape(short_url_display)}</div>',
        css=css,
        archive=archive,
    )

    # 6. Multilingual Call-to-Action Grid (8 Launch Locales)
    col1_html = """
    <div>
        <div class="lang-item"><span class="lang-name">🇩🇪 Deutsch:</span> Scannen Sie den QR-Code, um das Formular auf Ihrem Smartphone auszufüllen.</div>
        <div class="lang-item"><span class="lang-name">🇬🇧 English:</span> Scan the QR code with your camera to fill out this form in your language.</div>
        <div class="lang-item"><span class="lang-name">🇫🇷 Français:</span> Scannez le code QR pour remplir ce formulaire dans votre langue maternelle.</div>
        <div class="lang-item"><span class="lang-name">🇪🇸 Español:</span> Escanee el código QR para completar este formulario en su idioma nativo.</div>
    </div>
    """
    col2_html = """
    <div>
        <div class="lang-item"><span class="lang-name">🇹🇷 Türkçe:</span> Bu formu kendi dilinizde doldurmak için QR kodunu kameranızla tarayın.</div>
        <div class="lang-item"><span class="lang-name">🇺🇦 Українська:</span> Відскануйте QR-код, щоб заповнити форму рідною мовою.</div>
        <div class="lang-item arabic"><span class="lang-name">🇸🇦 العربية:</span> امسح رمز الاستجابة السريعة بكاميرا هاتفك لملء هذا النموذج بلغتك الأم.</div>
        <div class="lang-item"><span class="lang-name">🇷🇺 Русский:</span> Отсканируйте QR-код камерой, чтобы заполнить форму на родном языке.</div>
    </div>
    """
    page.insert_htmlbox(
        fitz.Rect(45, 490, 290, 750), col1_html, css=css, archive=archive
    )
    page.insert_htmlbox(
        fitz.Rect(305, 490, 550, 750), col2_html, css=css, archive=archive
    )

    # 7. Footer Guarantee
    footer_html = """
    <div class="footer-text">
        🔒 100% Kostenlos für Bürger & Antragsteller (Free for Citizens) • Keine App erforderlich (No app required)<br/>
        DSGVO-konform verschlüsselt • Generiert ein offizielles behördliches PDF zur Abgabe
    </div>
    """
    page.insert_htmlbox(
        fitz.Rect(45, 785, 550, 830), footer_html, css=css, archive=archive
    )

    return bytes(doc.tobytes())
