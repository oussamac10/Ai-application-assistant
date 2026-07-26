# ADR 0009 — Local OCR Provider

**Status:** Accepted
**Phase:** 10 — OCR Integration
**Date:** 2026-07-26

---

## Context

Phase 9 classifies uploaded PDFs and marks scanned/image-based documents with `next_step: ocr_required`, but performs no OCR itself. Phase 10 must turn those documents into normalized, page-level text so that Phase 11 (dynamic field detection) has something to work with. The requirements from the domain rules are:

1. OCR must run locally — no cloud OCR provider, no third party ever sees document contents.
2. OCR output is text and geometry only — it must never carry field-semantic information (label/value pairing, form-field inference). That is explicitly Phase 11's job.
3. Automated tests must never call a live/paid provider, so a deterministic mock implementation is required alongside the real one.
4. Confidence values may only be stored when they come from a provider with documented confidence semantics — never invented by an LLM.
5. Ownership, expiration, and privacy guarantees already built for `SourceDocument` in Phase 9 must be reused, not reimplemented.

---

## Decisions

### 1. `OCRProvider` protocol, mirroring `AIProvider`

`app/ocr/providers/base.py` defines a `Protocol` with one method, `extract_page(image_path, page_number, language) -> OCRPageResult`, plus frozen dataclasses (`BoundingBox`, `OCRWord`, `OCRLine`, `OCRPageResult`). Business logic (`OCRService`) depends only on this protocol, never on a concrete provider class — the same pattern used for `AIProvider`.

Two implementations exist:

- `MockOCRProvider` — fully deterministic, derives its output from the page number and requested language. Used in all automated tests and as the default (`OCR_PROVIDER=mock`) for local development.
- `LocalOCRProvider` — wraps `pytesseract` (a `tesseract-ocr` binary wrapper). Only exercised when `OCR_PROVIDER=local`, which requires the `tesseract-ocr` system package and language data (installed in the Docker image; not required for the mock-only automated test suite).

### 2. Page rendering is a separate, replaceable step

`app/ocr/renderer.py` defines a `PageRenderer` protocol (`render_pages`, `cleanup`) and `PDFPageRenderer`, a PyMuPDF-backed implementation. Rendering is injected into `OCRService` the same way the provider is, so tests can substitute a fake renderer without needing tesseract, and the real renderer can be exercised in tests using PyMuPDF alone (no tesseract dependency) paired with `MockOCRProvider`.

PyMuPDF applies each page's own rotation via its rendering matrix, so OCR always sees pages in reading orientation regardless of how the source PDF stored them.

### 3. Coordinates live in rendered-image pixel space

Every `BoundingBox` — line and word — is in the pixel space of the image `PDFPageRenderer` produced at `OCR_RENDER_DPI` (default 300 DPI), not PDF point space. This is documented directly in the provider/renderer docstrings and is expected to be a common Phase 11 gotcha, so it's called out here explicitly: any code that maps OCR coordinates back onto the original PDF must account for the DPI-to-point conversion.

### 4. `OCRResult` is one row per document; `OCRPage` is normalized per-page output

`OCRResult` (parent) holds status (`pending|processing|completed|failed|expired|deleted`), the provider used, requested language, and expiration. `OCRPage` (child, one row per page) holds text, average confidence, and a JSON blob of lines/words with bounding boxes — mirroring the provider-independent dataclasses exactly, so persistence is a straight serialization of what the provider returned.

A unique constraint on `OCRResult.source_document_id` means OCR is 1:1 with a document, not append-only history.

### 5. OCR requests are idempotent per document

`OCRService.request_ocr` is idempotent: a second request for a document that already has a `completed` result returns that result without re-running OCR. A request while a prior run is still `processing` raises `OCRAlreadyProcessingError` (409) rather than starting a concurrent run. A prior `failed`/`expired`/`deleted` result is overwritten by a fresh attempt.

### 6. Eligibility reuses Phase 9's analysis, does not re-derive it

`OCRService` calls `SourceDocumentService.get_document()` for ownership-token verification and expiration checks — the exact same code path Phase 9's own retrieval endpoint uses. Eligibility for OCR itself (`ocr_not_required` if the document analysis didn't flag it, `unsupported_language` if the requested language isn't one of the four supported) is a thin additional check layered on top, not a parallel reimplementation.

### 7. Rendered images are temporary and cleaned up unconditionally

Each OCR run renders pages into `OCR_RENDER_STORAGE_PATH/{ocr_result_id}/`. The renderer's `cleanup()` runs in a `finally` block regardless of success or failure, and the now-empty per-run directory is removed immediately after. The cleanup command (`cleanup_expired_exports`) additionally sweeps any directory older than `OCR_TIMEOUT_SECONDS` as a safety net for crashed runs that never reached the `finally` block.

### 8. Supported OCR languages are a fixed, small set

`SUPPORTED_OCR_LANGUAGES` in `app/ocr/constants.py` maps the four application language codes (`en`, `de`, `fr`, `ar`) to their Tesseract language codes (`eng`, `deu`, `fra`, `ara`). Requesting OCR in any other language is rejected with `unsupported_language` before any rendering happens. This keeps the Docker image's installed language-data footprint bounded and matches the languages the rest of the product already supports.

---

## Consequences

### Positive

- The provider/renderer split means the full request → render → extract → persist pipeline is tested end-to-end using real PDF rendering (PyMuPDF) and a deterministic provider (mock), without requiring tesseract in the test environment.
- Swapping in a different OCR engine later only requires a new `OCRProvider` implementation; `OCRService`, the API, and persistence are unaffected.
- Idempotency and the `processing` guard prevent duplicate work and races from a user double-clicking "Start OCR".

### Negative / Trade-offs

- `LocalOCRProvider` itself is only exercised by the automated suite through its request/response contract (via `MockOCRProvider`) and manual verification with a Dockerized tesseract install — there is no CI environment in this phase that runs OCR against the real tesseract binary.
- Coordinate space (pixel, not point) requires every downstream consumer to know the rendering DPI; if `OCR_RENDER_DPI` changes after data has been persisted, old `OCRPage` rows and new ones will disagree on scale unless the DPI used is also persisted per-run (currently it is not — a candidate follow-up for Phase 11 if coordinate math becomes load-bearing there).

---

## Related

- [backend/app/ocr/](../../backend/app/ocr/)
- [backend/tests/ocr/](../../backend/tests/ocr/)
- [docs/ocr.md](../ocr.md)
- [ADR 0008 — Structural PDF Document Analysis](0008-structural-pdf-document-analysis.md)
- [ADR 0004 — Local Ollama Provider](0004-local-ollama-provider.md) (same provider-abstraction pattern)
