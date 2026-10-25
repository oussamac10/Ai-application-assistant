# Phase 17 — Dynamic Coordinate-Overlay PDF Export, Document Location Preview & Voice Dictation

## Goal

Enable users who upload arbitrary PDFs (with detected field bounding boxes) to generate and download a completed PDF with their confirmed answers overlaid at the detected coordinates using PyMuPDF (`fitz`), while providing a live visual Document Location Preview and optional speech-to-text input during the guided Q&A session.

## Completed Acceptance Criteria

- [x] `backend/app/pdf/dynamic_overlay.py` created to map confirmed `FormField` answers to `DetectedField` bounding boxes (`input_bounding_box`) and render text, checkmarks, and vector signatures onto the uploaded source PDF via PyMuPDF (`fitz`)
- [x] `PDFExportService.create_export` supports dynamic coordinate-overlay export when a session is backed by a `SourceDocument` with detected field coordinates, while continuing to reject unmapped synthetic dynamic sessions (`dynamic_pdf_export_not_supported`)
- [x] `FormSession.export_supported` reflects export capability for sessions backed by either a predefined `pdf_template_key` or an uploaded `source_document_id`
- [x] `CurrentFieldResponse` exposes optional `page_number`, `input_bounding_box`, `source_document_filename`, and `source_document_page_count` metadata
- [x] Guided Session page (`frontend/src/app/application/session/[sessionId]/page.tsx`) displays a visual Document Location Preview card showing the target page and highlighted field bounding box on the official document, plus a live SVG preview of drawn signatures on the confirmation card
- [x] `FieldRenderer.tsx` includes an accessible Voice Dictation button for text and multiline inputs using the Web Speech API when available
- [x] `validate_pdf_safety` in `backend/app/documents/validation.py` sanitizes active PDF triggers (`/JavaScript`, `/JS`, `/OpenAction`, `/AA`, `/Launch`, `/EmbeddedFiles`) in place instead of rejecting official forms with `unsupported_pdf_feature`
- [x] Pushbutton AcroForm widgets (`Button` / `/Btn` with flag `65536`) are skipped in `backend/app/field_detection/extraction.py` and `backend/app/documents/analyzer.py` and removed on exported copies
- [x] Route all readable PDF categories (`fillable_pdf`, `digital_pdf`, and `hybrid_pdf` with native text or AcroForm widgets) to `dynamic_field_detection` in `backend/app/documents/service.py`
- [x] Populate `input_bounding_box` for blank-run and sibling fields in `_detect_normal_fields`, inline blank gaps in `_detect_inline_blank_fields`, standalone option groups, and split `Ort, Datum, Unterschrift` lines in `_detect_from_acroform`
- [x] Fix `AnswerService.submit_clarification` so non-money clarifications combine address parts or replace gibberish inputs cleanly instead of serializing a raw Python `dict`
