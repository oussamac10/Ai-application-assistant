"""PDF Field Extractor and Geometry Parser.

Provides high-fidelity extraction of AcroForm widgets, layout prompts,
and page text geometry for administrative PDF documents.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import fitz  # PyMuPDF
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.forms.models import (
    FormField,
    FormFieldOption,
    FormFieldOptionTranslation,
    FormFieldTranslation,
)
from app.forms.pdf_structure_detector import structure_pdf_page_fields

logger = logging.getLogger(__name__)

# Common government form semantic field patterns for Profile Vault mapping
KEY_PATTERNS: list[tuple[re.Pattern[str], str, str, str]] = [
    (
        re.compile(r"vorname|first_?name|given_?name", re.IGNORECASE),
        "First Name",
        "string",
        "personal.first_name",
    ),
    (
        re.compile(r"nachname|familienname|last_?name|surname|name\b", re.IGNORECASE),
        "Last Name",
        "string",
        "personal.last_name",
    ),
    (
        re.compile(r"geburtsdatum|date_?of_?birth|dob", re.IGNORECASE),
        "Date of Birth",
        "date",
        "personal.date_of_birth",
    ),
    (
        re.compile(r"geburtsort|place_?of_?birth", re.IGNORECASE),
        "Place of Birth",
        "string",
        "personal.place_of_birth",
    ),
    (
        re.compile(r"staatsangeh[oö]rigkeit|nationality|citizenship", re.IGNORECASE),
        "Nationality",
        "country",
        "personal.nationality",
    ),
    (
        re.compile(r"familienstand|marital_?status", re.IGNORECASE),
        "Marital Status",
        "choice",
        "personal.marital_status",
    ),
    (
        re.compile(r"geschlecht|gender|sex", re.IGNORECASE),
        "Gender",
        "choice",
        "personal.gender",
    ),
    (
        re.compile(r"e[-_]?mail|elektronische_?post", re.IGNORECASE),
        "Email Address",
        "email",
        "contact.email",
    ),
    (
        re.compile(r"telefon|phone|mobil|rufnummer", re.IGNORECASE),
        "Phone Number",
        "phone",
        "contact.phone",
    ),
    (
        re.compile(r"anschrift|adresse|address", re.IGNORECASE),
        "Current Address",
        "string",
        "residence.street_and_number",
    ),
    (
        re.compile(r"stra[ßs]e|street", re.IGNORECASE),
        "Street Address",
        "string",
        "address.street",
    ),
    (
        re.compile(r"hausnummer|house_?num", re.IGNORECASE),
        "House / Building Number",
        "string",
        "address.house_number",
    ),
    (
        re.compile(r"postleitzahl|plz|postal_?code|zip", re.IGNORECASE),
        "Postal / ZIP Code",
        "string",
        "address.postal_code",
    ),
    (
        re.compile(r"ort|stadt|city|wohnort", re.IGNORECASE),
        "City / Town",
        "string",
        "address.city",
    ),
    (
        re.compile(r"land|country", re.IGNORECASE),
        "Country",
        "country",
        "address.country",
    ),
    (re.compile(r"iban", re.IGNORECASE), "IBAN / Bank Account", "iban", "finance.iban"),
    (
        re.compile(r"einzugsdatum|move_?in", re.IGNORECASE),
        "Move-in Date",
        "date",
        "residence.move_in_date",
    ),
    (
        re.compile(r"auszugsdatum|move_?out", re.IGNORECASE),
        "Move-out Date",
        "date",
        "residence.move_out_date",
    ),
    (
        re.compile(r"wohnungsgeber|vermieter|landlord", re.IGNORECASE),
        "Landlord / Housing Provider",
        "string",
        "landlord.name",
    ),
    (
        re.compile(r"unterschrift|signature", re.IGNORECASE),
        "Signature",
        "signature",
        "signature.applicant",
    ),
]


def clean_label_text(text: str) -> str:
    """Strips leading/trailing colons, asterisks, hyphens, and redundant whitespace."""
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r"[\s\:\*\-\_]+$", "", t)
    t = re.sub(r"^[\s\:\*\-\_]+", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def extract_nearby_text_for_widget(page: fitz.Page, rect: fitz.Rect, ftype: str) -> str:
    """Extracts adjacent printed text on the PDF page near the widget rectangle."""
    words = page.get_text("words")
    if not words:
        return ""

    if ftype in ("boolean", "choice"):
        # For checkboxes or radio buttons, label is almost always directly to the right on the same line
        same_line_right = [
            w[4]
            for w in words
            if abs(w[1] - rect.y0) < 14 and rect.x1 <= w[0] < rect.x1 + 420
        ]
        if same_line_right:
            return " ".join(same_line_right)

        # Fallback: text immediately above
        above = [
            w[4]
            for w in words
            if 0 <= rect.y0 - w[3] < 22 and abs(w[0] - rect.x0) < 150
        ]
        if above:
            return " ".join(above)
    else:
        # For text inputs, text is typically directly above the input box
        above = [
            w[4]
            for w in words
            if 0 <= rect.y0 - w[3] < 28 and rect.x0 - 50 <= w[0] <= rect.x1 + 50
        ]
        if above:
            return " ".join(above)

        # Or text on the left of the input box
        left = [
            w[4]
            for w in words
            if abs(w[1] - rect.y0) < 14 and rect.x0 - 260 <= w[0] < rect.x0
        ]
        if left:
            return " ".join(left)

    return ""


def extract_widget_metadata(
    page: fitz.Page, widget: fitz.Widget
) -> tuple[str, str, str | None, str] | None:
    """Extracts (label, field_type, question_key, requiredness) for an AcroForm widget.

    Returns None if the widget is a non-input pushbutton (Print, Reset, Submit).
    """
    ftype_raw = (widget.field_type_string or "text").lower()
    field_name = widget.field_name or ""

    # Skip pushbuttons (Print, Reset, Clear, Submit)
    if ftype_raw == "button" or field_name.lower().startswith(("bt", "btn", "button")):
        return None

    # Determine baseline field type
    if (
        "check" in ftype_raw
        or "radio" in ftype_raw
        or field_name.lower().startswith(("chk", "rad"))
    ):
        field_type = "boolean"
    elif "signature" in ftype_raw or "sig" in field_name.lower():
        field_type = "signature"
    elif "choice" in ftype_raw:
        field_type = "choice"
    else:
        field_type = "string"

    # 1. Prefer explicit PDF Alternate Field Name / Label (/TU)
    explicit_label = clean_label_text(
        getattr(widget, "field_label", None)
        or getattr(widget, "field_alt_text", None)
        or ""
    )

    # 2. If no explicit label or it's just the raw variable name, inspect adjacent visual text
    visual_label = ""
    if not explicit_label or explicit_label.lower() == field_name.lower():
        visual_label = clean_label_text(
            extract_nearby_text_for_widget(page, widget.rect, field_type)
        )

    if explicit_label and explicit_label.lower() != field_name.lower():
        detected_label = explicit_label
    elif visual_label:
        detected_label = visual_label
    else:
        # Strip common programmer prefixes (chk, txt, rad) and split camelCase
        name_clean = re.sub(r"^(chk|txt|btn|rad)_?", "", field_name, flags=re.I)
        name_clean = re.sub(r"([a-z])([A-Z])", r"\1 \2", name_clean)
        name_clean = re.sub(r"[_\-]+", " ", name_clean).strip()
        detected_label = name_clean.title() if name_clean else field_name

    # Refine field type for string fields
    if field_type == "string":
        if re.search(r"datum|date|am_?$", detected_label, re.I) or re.search(
            r"datum|date", field_name, re.I
        ):
            field_type = "date"
        elif (
            re.search(r"e[-_]?mail", detected_label, re.I)
            or "mail" in field_name.lower()
        ):
            field_type = "email"
        elif (
            re.search(r"telefon|phone|mobil", detected_label, re.I)
            or "phone" in field_name.lower()
        ):
            field_type = "phone"
        elif re.search(r"iban", detected_label, re.I) or "iban" in field_name.lower():
            field_type = "iban"
        elif re.search(r"unterschrift|signature", detected_label, re.I):
            field_type = "signature"

    # Question key mapping (for Profile Vault prefill)
    question_key: str | None = None
    for pattern, _, expected_type, qkey in KEY_PATTERNS:
        # Only map question key if field types are compatible (e.g. string with string, date with date)
        if field_type == expected_type and (
            pattern.search(detected_label) or pattern.search(field_name)
        ):
            question_key = qkey
            break

    requiredness = (
        "optional" if field_type in ("email", "phone", "iban") else "required"
    )

    return detected_label, field_type, question_key, requiredness


def infer_field_metadata(
    raw_name: str, field_type_str: str
) -> tuple[str, str, str | None, str]:
    """Infers (clean_label, field_type, question_key, requiredness) from prompt text or field name."""
    clean_label = clean_label_text(raw_name)
    ftype = "string"
    if "check" in field_type_str.lower() or "radio" in field_type_str.lower():
        ftype = "boolean"
    elif "choice" in field_type_str.lower():
        ftype = "choice"
    elif "signature" in field_type_str.lower():
        ftype = "signature"

    # Check for question key and type refinements
    qkey: str | None = None
    for pattern, _, expected_type, key in KEY_PATTERNS:
        if pattern.search(clean_label):
            if ftype == "string":
                ftype = expected_type
            qkey = key
            break

    # If raw_name is just an ASCII identifier without spaces (e.g. first_name), humanize it
    if re.match(r"^[a-zA-Z0-9_\-]+$", clean_label):
        clean_label = re.sub(r"[_\-]+", " ", clean_label).strip()
        if clean_label:
            clean_label = clean_label[0].upper() + clean_label[1:]

    req = "optional" if ftype in ("email", "phone", "iban") else "required"
    return clean_label or "Feld", ftype, qkey, req


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-") or "form"


def extract_fields_from_pdf_layout(doc: fitz.Document) -> list[dict[str, Any]]:
    """Extracts field prompts and bounding boxes from flat PDF text and drawn rectangles.

    Guarantees 100% fidelity to the actual document: never invents missing fields.
    """
    fields: list[dict[str, Any]] = []
    for page_idx, page in enumerate(doc):
        # 1. Collect drawn vector rectangles (input boxes)
        drawings = page.get_drawings()
        rect_boxes: list[fitz.Rect] = []
        for d in drawings:
            r = d.get("rect")
            if (
                r
                and r.width > 40
                and 10 < r.height < 180
                and r.width < page.rect.width * 0.98
            ):
                rect_boxes.append(r)

        # 2. Inspect text blocks (or fallback to OCR for scanned documents / raster images)
        blocks = page.get_text("blocks")
        if not blocks:
            try:
                tp = page.get_textpage_ocr(language="eng+deu+fra+spa", dpi=150)
                blocks = tp.extractBLOCKS()
            except Exception as e:
                logger.warning("OCR fallback on page %d failed: %s", page_idx, e)
                blocks = []
        for b in blocks:
            if b[6] != 0:  # text block only
                continue
            text = b[4].strip()
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            for line in lines:
                is_prompt = (
                    line.endswith(":")
                    or line.endswith("*")
                    or line.endswith("*:")
                    or any(p[0].search(line) for p in KEY_PATTERNS)
                )
                if not is_prompt or len(line) > 90:
                    continue

                label, ftype, qkey, req = infer_field_metadata(line, "text")
                bx0, by0, bx1, by1 = b[0], b[1], b[2], b[3]

                # Match nearest drawn box below or to the right
                matched_box: fitz.Rect | None = None
                min_dist = float("inf")
                for r in rect_boxes:
                    if r.y0 >= by0 and (r.y0 - by1) < 55 and abs(r.x0 - bx0) < 140:
                        dist = r.y0 - by1
                        if dist < min_dist:
                            min_dist = dist
                            matched_box = r
                    elif abs(r.y0 - by0) < 25 and r.x0 >= bx0 and (r.x0 - bx1) < 70:
                        dist = r.x0 - bx1
                        if dist < min_dist:
                            min_dist = dist
                            matched_box = r

                if matched_box:
                    bbox = [
                        round(float(matched_box.x0), 1),
                        round(float(matched_box.y0), 1),
                        round(float(matched_box.x1), 1),
                        round(float(matched_box.y1), 1),
                    ]
                else:
                    bbox = [
                        round(float(bx0), 1),
                        round(float(by1 + 2), 1),
                        round(float(min(page.rect.width - 50, bx0 + 380)), 1),
                        round(float(by1 + 26), 1),
                    ]

                clean_lbl = line.rstrip(":* ").strip()
                fkey = slugify(clean_lbl) or f"field_{len(fields) + 1}"
                existing_keys = {f["key"] for f in fields}
                if fkey in existing_keys:
                    fkey = f"{fkey}_{len(fields) + 1}"

                fields.append(
                    {
                        "key": fkey,
                        "label": clean_lbl,
                        "field_type": ftype,
                        "question_key": qkey,
                        "requiredness": req,
                        "options": [],
                        "bbox": bbox,
                        "page": page_idx + 1,
                    }
                )
    return fields


def extract_fields_from_pdf_bytes(pdf_bytes: bytes) -> list[dict[str, Any]]:
    """Extracts candidate fields from interactive AcroForms or layout text, structured per table row and choice group."""
    extracted_fields: list[dict[str, Any]] = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_idx, page in enumerate(doc):
            raw_page_fields: list[dict[str, Any]] = []
            for widget in page.widgets():
                if not widget.field_name:
                    continue
                meta = extract_widget_metadata(page, widget)
                if not meta:
                    continue  # e.g. pushbuttons like Print or Reset
                label, ftype, qkey, req = meta

                options: list[str] = []
                if hasattr(widget, "choice_values") and widget.choice_values:
                    options = list(widget.choice_values)

                rect = widget.rect
                bbox = [
                    round(float(rect.x0), 1),
                    round(float(rect.y0), 1),
                    round(float(rect.x1), 1),
                    round(float(rect.y1), 1),
                ]

                raw_page_fields.append(
                    {
                        "key": slugify(widget.field_name),
                        "label": label,
                        "field_type": ftype,
                        "question_key": qkey,
                        "requiredness": req,
                        "options": options,
                        "bbox": bbox,
                        "page": page_idx + 1,
                        "is_radio": widget.field_type
                        == fitz.PDF_WIDGET_TYPE_RADIOBUTTON,
                        "raw_field_name": widget.field_name,
                    }
                )
            extracted_fields.extend(
                structure_pdf_page_fields(
                    page, raw_page_fields, page_idx + 1, infer_field_metadata
                )
            )
        doc.close()
    except Exception as e:
        logger.warning("PyMuPDF widget extraction encountered an error: %s", e)

    # Fallback: if no interactive AcroForm widgets found, extract layout-based fields from text and drawn boxes
    if not extracted_fields:
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            raw_layout = extract_fields_from_pdf_layout(doc)
            by_page: dict[int, list[dict[str, Any]]] = {}
            for item in raw_layout:
                by_page.setdefault(int(item.get("page", 1)), []).append(item)
            for page_idx, page in enumerate(doc):
                p_num = page_idx + 1
                p_items = by_page.get(p_num, [])
                if p_items:
                    extracted_fields.extend(
                        structure_pdf_page_fields(
                            page, p_items, p_num, infer_field_metadata
                        )
                    )
            doc.close()
        except Exception as e:
            logger.warning("PyMuPDF layout-based field extraction error: %s", e)

    return extracted_fields


def insert_extracted_fields(
    db: Session,
    version_id: str,
    extracted_fields: list[dict[str, Any]],
    source_language: str = "de",
) -> None:
    """Inserts extracted fields into database with unique keys and source translation."""
    current_max_pos = (
        db.query(func.max(FormField.position))
        .filter(FormField.form_version_id == version_id)
        .scalar()
        or 0
    )
    existing_keys = {
        f.key
        for f in db.query(FormField.key)
        .filter(FormField.form_version_id == version_id)
        .all()
    }

    for idx, f in enumerate(extracted_fields):
        base_key = f["key"]
        candidate_key = base_key
        suffix = 2
        while candidate_key in existing_keys:
            candidate_key = f"{base_key}_{suffix}"
            suffix += 1
        existing_keys.add(candidate_key)

        cfg: dict[str, Any] = {"bbox": f.get("bbox"), "page": f.get("page", 1)}
        if f.get("table"):
            cfg["table"] = f["table"]
        if f.get("option_boxes"):
            cfg["option_boxes"] = f["option_boxes"]
        if f.get("learned_pattern_id"):
            cfg["learned_pattern_id"] = f["learned_pattern_id"]
        if f.get("learned_confidence") is not None:
            cfg["learned_confidence"] = f["learned_confidence"]

        form_field = FormField(
            form_version_id=version_id,
            key=candidate_key,
            field_type=f["field_type"],
            required=f["requiredness"] == "required",
            requiredness=f["requiredness"],
            position=current_max_pos + idx + 1,
            question_key=f["question_key"],
            configuration=cfg,
        )
        db.add(form_field)
        db.flush()

        # Translation for source language (e.g. de) + any learned language rows
        learned_tr: dict[str, Any] = f.get("learned_translations") or {}
        src_learned = (
            learned_tr.get(source_language) if isinstance(learned_tr, dict) else None
        )
        trans = FormFieldTranslation(
            form_field_id=form_field.id,
            language=source_language,
            label=f["label"],
            help_text=(src_learned or {}).get("help_text")
            if isinstance(src_learned, dict)
            else None,
            placeholder=(src_learned or {}).get("placeholder")
            if isinstance(src_learned, dict)
            else None,
        )
        db.add(trans)
        if isinstance(learned_tr, dict):
            for lang_code, tr_data in learned_tr.items():
                if lang_code == source_language or not isinstance(tr_data, dict):
                    continue
                lbl = str(tr_data.get("label") or "").strip()
                if not lbl:
                    continue
                db.add(
                    FormFieldTranslation(
                        form_field_id=form_field.id,
                        language=str(lang_code),
                        label=lbl,
                        help_text=tr_data.get("help_text"),
                        placeholder=tr_data.get("placeholder"),
                    )
                )

        # Options + localized option labels if choice field
        for opt_idx, opt_item in enumerate(f.get("options", [])):
            if isinstance(opt_item, dict):
                opt_val = str(opt_item.get("value") or "").strip()
                if not opt_val:
                    continue
                opt_tr_map: dict[str, str] = {}
                if isinstance(opt_item.get("translations"), dict):
                    opt_tr_map = {
                        str(k): str(v) for k, v in opt_item["translations"].items() if v
                    }
                elif opt_item.get("label"):
                    opt_tr_map = {source_language: str(opt_item["label"])}
            else:
                opt_val = str(opt_item).strip()
                if not opt_val:
                    continue
                opt_tr_map = {source_language: opt_val}

            opt = FormFieldOption(
                form_field_id=form_field.id,
                value=opt_val,
                position=opt_idx + 1,
            )
            db.add(opt)
            db.flush()

            if source_language not in opt_tr_map:
                opt_tr_map[source_language] = opt_val
            for o_lang, o_lbl in opt_tr_map.items():
                db.add(
                    FormFieldOptionTranslation(
                        form_field_option_id=opt.id,
                        language=o_lang,
                        label=o_lbl,
                    )
                )


def get_pdf_page_dimensions(pdf_bytes: bytes) -> tuple[int, list[dict[str, Any]]]:
    """Reads page count and width/height dimensions for each page in the PDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)
        page_dimensions = [
            {
                "page": idx + 1,
                "width": round(float(p.rect.width), 1),
                "height": round(float(p.rect.height), 1),
            }
            for idx, p in enumerate(doc)
        ]
        doc.close()
        return page_count, page_dimensions
    except Exception as e:
        logger.warning("Could not read PDF page dimensions: %s", e)
        return 1, []


def render_pdf_page_png(pdf_bytes: bytes, page_number: int, dpi: int = 150) -> bytes:
    """Renders a specific page of a PDF document to a PNG image byte string."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if page_number < 1 or page_number > len(doc):
        doc.close()
        raise ValueError(
            f"Invalid page number {page_number}. Document has {len(doc)} pages."
        )

    page = doc[page_number - 1]
    pix = page.get_pixmap(dpi=dpi)
    png_bytes: bytes = bytes(pix.tobytes("png"))
    doc.close()
    return png_bytes
