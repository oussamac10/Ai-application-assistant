# Project TODO

## Completed Phases

Archived under `docs/progress/`:

1. Project Foundation
2. Form Definitions and Versioning
3. Temporary Anonymous Sessions
4. Mock Question and Answer Workflow
5. Local AI Integration with Ollama
6. Reusable Question Catalog and Hybrid Resolution
7. Frontend Guided Form Experience
8. PDF Template Mapping and Export
9. Form Upload and Document Analysis
10. OCR Integration
11. Dynamic Form Field Detection
12. User Accounts and Saved Applications
13. Automatic Upload-to-Questions User Flow
14. Azure Document Intelligence Provider
15. Azure Translator Integration
16. Hybrid Document Detection

## Completed Tasks

- Eliminated redundant `getSummary` API calls on every question transition in the guided session flow (`backend/app/answers/schemas.py`, `backend/app/answers/services.py`, `frontend/src/app/application/session/[sessionId]/page.tsx`).
- Fixed answer confirmation and summary display formatting for money amounts (`2000.0 EUR once` -> `2000 EUR`), multiple-choice arrays, and boolean Yes/No values.
- Created `DESIGN.md` and upgraded the entire Next.js frontend to the "Warm Civic Daylight — Paper & Ink" design system, added 36-language universal support (`languages.ts`, `LanguageSelector.tsx`), and categorized manual form selection (`formCatalogMetadata.ts`).

## Current Task

Implement Phase 17: Dynamic Coordinate-Overlay PDF Export for Uploaded Forms ("Export Any Uploaded PDF"), Document Field Location Preview in the Guided Session, and Voice-to-Answer Dictation support.

## Goal

Enable users who upload arbitrary PDFs (with detected field bounding boxes) to generate and download a completed PDF with their confirmed answers overlaid at the detected coordinates using PyMuPDF (`fitz`), while providing a live visual Document Location Preview and optional speech-to-text input during the guided Q&A session.

## Acceptance Criteria

- [x] `backend/app/pdf/dynamic_overlay.py` created to map confirmed `FormField` answers to `DetectedField` bounding boxes (`input_bounding_box`) and render text, checkmarks, and signatures onto the uploaded source PDF via PyMuPDF (`fitz`)
- [x] `PDFExportService.create_export` supports dynamic coordinate-overlay export when a session is backed by a `SourceDocument` with detected field coordinates, while continuing to reject unmapped synthetic dynamic sessions (`dynamic_pdf_export_not_supported`)
- [x] `FormSession.export_supported` reflects export capability for sessions backed by either a predefined `pdf_template_key` or an uploaded `source_document_id`
- [x] `CurrentFieldResponse` exposes optional `page_number`, `input_bounding_box`, `source_document_filename`, and `source_document_page_count` metadata
- [x] Guided Session page (`frontend/src/app/application/session/[sessionId]/page.tsx`) displays a visual Document Location Preview card showing the target page and highlighted field bounding box on the official document
- [x] `FieldRenderer.tsx` includes an accessible Voice Dictation button for text and multiline inputs using the Web Speech API when available
- [x] `validate_pdf_safety` in `backend/app/documents/validation.py` sanitizes active PDF triggers (`/JavaScript`, `/JS`, `/OpenAction`, `/AA`, `/Launch`, `/EmbeddedFiles`) in place instead of rejecting official forms with `unsupported_pdf_feature`
- [x] Pushbutton AcroForm widgets (`Button` / `/Btn` with flag `65536`, e.g., `Drucken` and `Alle Angaben löschen`) are skipped in `backend/app/field_detection/extraction.py` and `backend/app/documents/analyzer.py`
- [x] Route all readable PDF categories (`fillable_pdf`, `digital_pdf`, and `hybrid_pdf` with native text or AcroForm widgets) to `dynamic_field_detection` in `backend/app/documents/service.py`, and route low-text / image-bearing PDFs (`scanned_pdf`, `unknown_pdf` with images) to `ocr_required`
- [x] Improve `PDFAnalyzer` (`backend/app/documents/analyzer.py`) so pushbutton-only `/Widget` annotations do not inflate `acroform_field_count` or misclassify flat PDFs as `fillable_pdf`
- [x] Improve `LocalFieldDetectionProvider` (`backend/app/field_detection/providers/local.py`, `sections.py`, `visual_fields.py`) for real-world AcroForm and flat municipal PDFs: humanize camelCase/Hungarian widget names when nearby text is a bare number (`1.`, `2.`), apply party section context (`Wohnungsgeber`, `Eigentümer`, `Vermieter`, `Mieter`, `Antragsteller`, `Arbeitgeber`) to AcroForm labels, detect text-line fields on non-AcroForm pages of mixed documents, and support label-above-underline spacing on flattened forms
- [x] Enhance `render_dynamic_overlay_pdf` (`backend/app/pdf/dynamic_overlay.py`) to draw checkmarks inside selected option checkboxes/markers for `single_choice` and `multiple_choice` fields and render text above `height == 0` underline regions
- [x] Backend unit/integration tests (`pytest`, `ruff`, `mypy`) and frontend tests (`vitest`, `tsc --noEmit`, `next lint`) pass without regressions

## Planned Steps

- [x] Inspect existing PDF export, field detection, and session schemas/tests
- [x] Create `backend/app/pdf/dynamic_overlay.py` and integrate into `backend/app/pdf/services.py` and `backend/app/sessions/models.py`
- [x] Enrich `CurrentFieldResponse` in `backend/app/answers/schemas.py` and `backend/app/answers/services.py` with field location metadata
- [x] Add Document Location Preview to `frontend/src/app/application/session/[sessionId]/page.tsx` and Voice Dictation button to `frontend/src/features/form-session/components/FieldRenderer.tsx`
- [x] Add comprehensive unit tests for dynamic coordinate-overlay PDF export and run full backend + frontend verification

## Files Expected to Change

- `TODO.md`
- `backend/app/documents/validation.py`
- `backend/app/documents/service.py`
- `backend/app/documents/analyzer.py`
- `backend/app/field_detection/extraction.py`
- `backend/tests/documents/test_documents.py`
- `backend/app/pdf/dynamic_overlay.py`
- `backend/app/pdf/services.py`
- `backend/app/sessions/models.py`
- `backend/app/answers/schemas.py`
- `backend/app/answers/services.py`
- `backend/tests/pdf/test_dynamic_overlay_export.py`
- `frontend/src/features/form-session/services/apiClient.ts`
- `frontend/src/app/application/session/[sessionId]/page.tsx`
- `frontend/src/features/form-session/components/FieldRenderer.tsx`

## Decisions and Assumptions

- `FormVersion.pdf_template_key` remains `None` for dynamically detected versions so `test_question_bridge.py` and `test_dynamic_export_guard.py` invariants are preserved.
- Coordinate overlay only renders fields that have an explicit `input_bounding_box` from field detection (never guessing coordinates when no input box exists).
- OCR-sourced bounding boxes (`source == "ocr"`) are scaled from `OCRPage` pixel dimensions to PDF page point dimensions (`fitz.Page.rect`).

## Blockers

- None

## Verification

- [x] Backend tests pass (`pytest` — 31 passed)
- [x] Backend linting and type checking pass (`ruff check`, `ruff format --check`, `mypy`)
- [x] Frontend tests pass (`vitest` — 28 passed test files, 240 passed tests)
- [x] Frontend linting and type checking pass (`next lint`, `tsc --noEmit`)
