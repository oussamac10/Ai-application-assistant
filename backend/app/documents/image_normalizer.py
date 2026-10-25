"""Smartphone camera & image upload normalization (Phase S1-02).

Validates real image magic bytes (JPEG, PNG, WebP), enforces pixel-count
caps against decompression bombs, applies EXIF orientation transposition,
strips 100% of EXIF/GPS/camera metadata, and wraps the clean RGB raster
onto a single ISO A4 PDF page so OCR, coordinate detection, and overlay
export share one identical coordinate space.
"""

from __future__ import annotations

import io
import os

import fitz
from PIL import Image, ImageOps, UnidentifiedImageError

from app.documents.errors import DocumentValidationError

A4_PORTRAIT_PT: tuple[float, float] = (595.0, 842.0)
A4_LANDSCAPE_PT: tuple[float, float] = (842.0, 595.0)

ALLOWED_UPLOAD_EXTENSIONS: frozenset[str] = frozenset(
    {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
)
ALLOWED_UPLOAD_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/jpg",
        "image/png",
        "image/webp",
    }
)


def is_candidate_upload_type(filename: str, content_type: str) -> bool:
    """Fast pre-stream check on declared MIME or filename extension.

    Real file format is ALWAYS verified via magic bytes after streaming.
    """
    normalized_ct = (content_type or "").split(";", 1)[0].strip().lower()
    lower_name = (filename or "").strip().lower()
    has_allowed_ext = any(lower_name.endswith(ext) for ext in ALLOWED_UPLOAD_EXTENSIONS)
    if has_allowed_ext:
        return True
    return normalized_ct in ALLOWED_UPLOAD_CONTENT_TYPES


def detect_upload_media_kind(filepath: str) -> str:
    """Inspects file magic bytes to classify PDF vs supported camera image."""
    try:
        with open(filepath, "rb") as f:
            header = f.read(16)
    except OSError as exc:
        raise DocumentValidationError(
            "Could not read uploaded file.", "malformed_pdf"
        ) from exc

    if header.startswith(b"%PDF"):
        return "application/pdf"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return "image/webp"

    raise DocumentValidationError(
        "Unsupported file format. Only PDF, JPG, PNG, and WebP files are supported.",
        "invalid_file_type",
    )


def normalize_image_file_to_a4_pdf(
    filepath: str,
    max_pixels: int,
    source_media_type: str,
) -> None:
    """Normalizes a JPEG/PNG/WebP file in place into a metadata-free A4 PDF."""
    previous_max_pixels = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        with Image.open(filepath) as raw_img:
            width, height = raw_img.size
            if width <= 0 or height <= 0:
                raise DocumentValidationError(
                    "Uploaded image has invalid dimensions.",
                    "malformed_pdf",
                )
            if width * height > max_pixels:
                raise DocumentValidationError(
                    "Image pixel dimensions exceed the maximum allowed limit.",
                    "image_too_large",
                )

            upright = ImageOps.exif_transpose(raw_img)
            clean_rgb = _strip_metadata_and_composite_white(upright)
    except DocumentValidationError:
        raise
    except Image.DecompressionBombError as exc:
        raise DocumentValidationError(
            "Image pixel dimensions exceed the maximum allowed limit.",
            "image_too_large",
        ) from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise DocumentValidationError(
            "Uploaded image could not be decoded.",
            "malformed_pdf",
        ) from exc
    finally:
        Image.MAX_IMAGE_PIXELS = previous_max_pixels

    img_w, img_h = clean_rgb.size
    page_w, page_h = A4_PORTRAIT_PT if img_h >= img_w else A4_LANDSCAPE_PT

    encoded_buf = io.BytesIO()
    if source_media_type == "image/jpeg" or (img_w * img_h > 2_000_000):
        clean_rgb.save(encoded_buf, format="JPEG", quality=92, optimize=True)
    else:
        clean_rgb.save(encoded_buf, format="PNG", optimize=True)
    clean_image_bytes = encoded_buf.getvalue()

    tmp_pdf_path = f"{filepath}.normalized.pdf"
    pdf_doc = fitz.open()
    try:
        page = pdf_doc.new_page(width=page_w, height=page_h)
        page.draw_rect(
            fitz.Rect(0, 0, page_w, page_h),
            color=(1.0, 1.0, 1.0),
            fill=(1.0, 1.0, 1.0),
        )
        page.insert_image(
            fitz.Rect(0, 0, page_w, page_h),
            stream=clean_image_bytes,
            keep_proportion=True,
        )
        pdf_doc.set_metadata({})
        pdf_doc.save(tmp_pdf_path, garbage=2, deflate=True)
    finally:
        pdf_doc.close()

    os.replace(tmp_pdf_path, filepath)


def _strip_metadata_and_composite_white(img: Image.Image) -> Image.Image:
    """Returns a fresh RGB Image built from raw pixel bytes with zero EXIF/GPS/ICC tags."""
    has_alpha = img.mode in ("RGBA", "LA") or (
        img.mode == "P" and "transparency" in img.info
    )
    if has_alpha:
        rgba = img.convert("RGBA")
        white_bg = Image.new("RGB", rgba.size, (255, 255, 255))
        white_bg.paste(rgba, mask=rgba.getchannel("A"))
        return white_bg

    rgb = img.convert("RGB")
    return Image.frombytes("RGB", rgb.size, rgb.tobytes())
