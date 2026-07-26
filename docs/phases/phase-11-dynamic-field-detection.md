# Phase 11 — Dynamic Field Detection

**Branch:** `feature/dynamic-field-detection`
**Base:** `feature/ocr-integration`
**Status:** Initialized. Implementation not yet started.

---

## Goal

Analyze unrecognized uploaded forms — digital PDFs with no template match, and OCR-processed scanned PDFs — and detect candidate form fields from native PDF text and coordinates, OCR text/lines/words/coordinates/confidence, and AcroForm widget metadata. Produce a normalized, persisted, user-reviewable field-detection result. After the user confirms detected fields, generate questions using the existing question-catalog and guided-session workflow.

Phase 11 does not automatically fill arbitrary uploaded PDFs.

---

## Reuse

- `SourceDocument` ownership, expiration, and storage (Phase 9)
- Phase 9 structural analysis result (`document_type`, `next_step`)
- Phase 10 `OCRResult`/`OCRPage` normalized OCR output
- `OCRProvider`/`MockOCRProvider` pattern for the new `FieldDetectionProvider` abstraction
- Existing question catalog, session, and answer workflow (Phases 4–8) — unmodified

## In scope

- `FieldDetectionProvider` protocol
- deterministic `MockFieldDetectionProvider`
- rules-based `LocalFieldDetectionProvider`
- native PDF text + coordinate extraction (PyMuPDF)
- AcroForm widget metadata extraction (name, type, rect, page)
- OCR-result consumption as a detection input source
- label detection and label/input-area association
- field-type classification (text, multiline_text, date, email, phone, address, number, currency, checkbox, radio, select, signature, unknown)
- bounding-box normalization across native/OCR/AcroForm sources
- confidence scoring
- deterministic candidate ordering and IDs
- persisted `FieldDetectionResult` / `DetectedField` / `DetectedFieldOption` + reversible migration
- ownership + expiration checks reused from Phase 9
- idempotent detection API (`POST`/`GET /api/source-documents/{id}/field-detection`)
- field review API (`PATCH`/`DELETE .../fields/{field_id}`) — confirm, edit, reject
- question generation from **confirmed** fields only, via the existing guided workflow
- multilingual field labels/questions (en/de/fr/ar), Arabic RTL preserved
- backend, frontend, migration, and Playwright tests
- ADR 0010

## Out of scope

- automatic filling of arbitrary PDFs
- automatic coordinate stamping into unknown PDFs
- automatic export of unknown forms
- signature/handwriting recognition
- table understanding beyond basic field candidates
- complex legal interpretation
- cloud AI providers
- background workers, Redis, Celery, object storage
- user accounts, payments, admin review dashboards, production monitoring
- Phase 12

---

## Expected user workflow

**Unknown digital PDF:** upload → validate/analyze → native text + positions extracted → detect fields → review candidates → confirm/edit/reject → generate questions → guided session starts.

**Unknown scanned PDF:** upload → classify as scanned → run OCR → OCR text + coordinates stored → detect fields → review candidates → confirm/edit/reject → generate questions.

**Known supported template:** upload → recognized → existing published form definition → existing guided workflow. Dynamic detection does **not** run for a recognized supported template.

---

## Architecture

```text
backend/app/field_detection/
├── __init__.py
├── api/
│   ├── __init__.py
│   └── routes.py
├── providers/
│   ├── __init__.py
│   ├── base.py
│   ├── mock.py
│   └── local.py
├── models.py
├── schemas.py
├── repository.py
├── service.py
├── extraction.py
├── geometry.py
├── labeling.py
├── classification.py
├── normalization.py
├── validation.py
├── constants.py
└── errors.py
```

- `routes.py` — HTTP concerns only
- `service.py` — orchestration, eligibility, idempotency
- `repository.py` — persistence
- `extraction.py` — collects native-text (PyMuPDF), OCR (Phase 10), and AcroForm (PyMuPDF widgets) inputs into one normalized `DetectionDocumentInput`
- `geometry.py` — coordinate normalization and proximity calculations between labels and input areas
- `labeling.py` — label/candidate association (colon suffix, left-of, above)
- `classification.py` — candidate field-type detection from label text and value patterns
- `normalization.py` — provider-independent result shape
- `validation.py` — eligibility and result validation
- `providers/base.py` — `FieldDetectionProvider` protocol
- `providers/mock.py` — deterministic provider for tests
- `providers/local.py` — rules-based local implementation, no cloud calls

Frontend:

```text
frontend/src/features/field-detection/
├── components/
├── hooks/
├── services/
├── types/
└── validation/
```

### Native text and AcroForm extraction uses PyMuPDF, not the Phase 9 analyzer

Phase 9's `PDFAnalyzer` (pypdf-based) only counts AcroForm widgets and native-text characters — it does not expose widget rectangles or word-level coordinates. Phase 11 needs real geometry, so `extraction.py` opens the document independently via PyMuPDF (`page.get_text("words")` for native text tokens with bounding boxes, `page.widgets()` for AcroForm field name/type/rect/page). This does not change or duplicate Phase 9's classification logic — it is a second, geometry-focused read of the same file for documents Phase 9 already routed to `dynamic_field_detection`.

### Provider interface

```python
class FieldDetectionProvider(Protocol):
    provider_name: str
    provider_version: str

    def detect(self, document: DetectionDocumentInput) -> DetectionResult: ...
```

`MockFieldDetectionProvider` requirements: deterministic output, no external dependency, configurable candidates/empty result/low-confidence result/failure, stable coordinates and confidence values.

`LocalFieldDetectionProvider` signals: AcroForm widget names/rects, text followed by a colon, labels left of or above empty areas, underline/box-like regions, common semantic name patterns, nearby OCR words, known value patterns (email, date, phone, postal code, amount), checkbox/radio widget metadata, repeated alignment patterns. No cloud requests.

---

## Input normalization

```json
{
  "pageNumber": 1,
  "width": 2480,
  "height": 3508,
  "source": "ocr",
  "tokens": [
    {
      "text": "Full name",
      "confidence": 96.2,
      "boundingBox": { "x": 120, "y": 220, "width": 310, "height": 60 }
    }
  ]
}
```

Requirements: preserve page order and source coordinates; record whether a token came from native text, OCR, or AcroForm; explicit coordinate origin/units; handle page rotation; drop empty tokens; preserve OCR confidence; never merge unrelated text; never expose internal storage paths.

## Candidate field schema

```json
{
  "fieldId": "candidate-public-id",
  "pageNumber": 1,
  "label": "Full name",
  "normalizedName": "full_name",
  "fieldType": "text",
  "required": null,
  "multiple": false,
  "confidence": 0.93,
  "source": "ocr",
  "labelBoundingBox": { "x": 120, "y": 220, "width": 310, "height": 60 },
  "inputBoundingBox": { "x": 470, "y": 215, "width": 900, "height": 70 },
  "options": [],
  "existingValue": null,
  "status": "pending_review"
}
```

Field types: `text | multiline_text | date | email | phone | address | number | currency | checkbox | radio | select | signature | unknown`.

Requirements: deterministic candidate IDs and ordering (page, then vertical, then horizontal position); confidence normalized to 0–1; safe handling of missing input rectangles; low-confidence candidates classify as `unknown` rather than inventing a type; preserve the original label; generate a safe normalized field name; deduplicate; detected existing values are never automatically treated as user answers.

## Persistence

`FieldDetectionResult` (one active result per document + analysis version): `id, public_id, source_document_id, ocr_result_id, status, provider_name, provider_version, analysis_version, source_type, field_count, average_confidence, error_code, started_at, completed_at, expires_at, created_at, updated_at`.

`DetectedField`: `id, public_id, detection_result_id, page_number, display_order, label, normalized_name, field_type, required, multiple, confidence, source, label_bounding_box, input_bounding_box, existing_value, review_status, created_at, updated_at`. Review statuses: `pending_review | confirmed | edited | rejected`.

Requirements: repeated `POST` requests are idempotent; completed results are reused; failed results may be retried; no ownership tokens stored; no internal paths exposed; expiration follows the source document; migration is reversible.

## Eligibility

May run only when: document exists, ownership token valid, not expired, analysis completed, document is **not** a recognized supported template, next step is `dynamic_field_detection` or OCR completed successfully, required native-text/OCR/coordinate data exists, source file still present when native extraction needs it, page count within configured limits.

Rejected safely when: supported template should use the mapped workflow (`supported_template_detected`), OCR required but not complete (`ocr_not_complete`), OCR failed, document expired/deleted, ownership token invalid, source data missing, document dangerous/malformed.

## API

```http
POST   /api/source-documents/{document_id}/field-detection
GET    /api/source-documents/{document_id}/field-detection
PATCH  /api/source-documents/{document_id}/field-detection/fields/{field_id}
DELETE /api/source-documents/{document_id}/field-detection/fields/{field_id}
```

All authenticated via `X-Document-Token` — never in the URL. `DELETE` marks a candidate `rejected`, it does not destroy the row. `PATCH` allows correcting: label, normalized name, field type, required state, input bounding box, options, review status.

Error codes: `field_detection_not_required`, `field_detection_not_ready`, `field_detection_not_found`, `field_detection_already_processing`, `field_detection_failed`, `field_detection_invalid_result`, `ocr_required`, `ocr_not_complete`, `document_expired`, `document_not_found`, `invalid_ownership_token`, `supported_template_detected`.

## Question generation

Only **confirmed** fields generate questions — never `pending_review` or `rejected` ones. Mapping: `text→text`, `multiline_text→textarea`, `date→date`, `email→email`, `phone→phone`, `address→address`, `number→numeric`, `currency→money`, `checkbox→boolean`, `radio/select→choice`, `unknown→generic text (post-confirmation only)`.

Implementation approach: confirmed `DetectedField` rows are materialized into a synthetic `FormTemplate` + `FormVersion` (`status="published"`) + `FormField` rows (reusing the exact schema Phases 2/7/8 already consume), keyed to the source document (e.g. `dynamic-doc-{document_public_id}`). The existing, unmodified `SessionService.create_session(form_version_id=...)` then starts a real guided session — Phase 11 does not introduce a parallel session/answer state machine. Output language stays separate from interface language, per the existing language model. Deterministic fallback questions are used when AI-based phrasing is unavailable; no cloud AI is required.

---

## Files Expected to Change

- `backend/app/field_detection/**` (new)
- `backend/migrations/versions/*` (new)
- `backend/migrations/env.py`
- `backend/app/main.py` (router + exception handlers)
- `backend/app/core/config.py`, `.env.example`
- `frontend/src/features/field-detection/**` (new)
- `frontend/messages/{en,de,fr,ar}.json`
- `frontend/e2e/dynamic-field-detection-flow.spec.ts` (new)
- `docs/field-detection.md`, `docs/decisions/0010-dynamic-field-detection.md` (new)
- `README.md`, `docs/architecture.md`, `docs/workflow.md`, `docs/testing.md`, `docs/security.md`, `docs/privacy.md`, `docs/document-upload-analysis.md`, `docs/ocr.md`, `docs/claude/architecture-map.md`

This list is an initial estimate and may be updated during implementation.

## Decisions and Assumptions

- Native-text and AcroForm geometry extraction uses PyMuPDF, independent of the Phase 9 `PDFAnalyzer` (which only counts, doesn't locate).
- Detected fields never auto-fill or auto-export; user review is mandatory before any question is generated.
- Confirmed fields become a real, temporary, published `FormVersion` so the entire existing session/answer/PDF pipeline works unmodified.
- Coordinate space matches ADR 0009: OCR-derived candidates stay in the rendered-image pixel space at `OCR_RENDER_DPI`; native/AcroForm candidates stay in PDF point space. The two are never silently mixed — `source` on every candidate records which space its coordinates are in.
- Supported languages for generated question labels remain en/de/fr/ar, matching the rest of the product.

## Known Deferred Items (carried from Phase 10)

- Full Playwright regression result: **15 of 16 passed** (`guided-flow.spec.ts` needs a published Basic Registration v1 form fixture seeded in the local test database — unrelated to OCR or Phase 11, must be resolved or re-verified before claiming a full pass)
- Full repository Ruff formatting still includes pre-existing issues under `app/documents/`, predating Phase 10 and intentionally left unchanged

---

## Related

- [ADR 0008 — Structural PDF Document Analysis](decisions/0008-structural-pdf-document-analysis.md)
- [ADR 0009 — Local OCR Provider](decisions/0009-local-ocr-provider.md)
- [docs/progress/phase-10-ocr-integration.md](progress/phase-10-ocr-integration.md)
