# Current Phase

## Phase

Phase 11 - Dynamic Field Detection

## Branch

`feature/dynamic-field-detection`

## Base

`feature/ocr-integration`

## Objective

Detect candidate form fields in unrecognized digital PDFs and OCR-processed scanned PDFs, using native PDF text/coordinates, AcroForm widget metadata, and Phase 10 OCR results. Persist a normalized, reviewable detection result. Generate questions from user-confirmed fields only, reusing the existing guided-session workflow.

## Reuse

- `SourceDocument` ownership, storage, and expiration (Phase 9)
- Phase 9 analysis result (`document_type`, `next_step`)
- Phase 10 `OCRResult`/`OCRPage` normalized OCR output
- `OCRProvider`/`MockOCRProvider` abstraction pattern
- existing question catalog, session, and answer workflow (unmodified)

## In scope

- field-detection provider abstraction (mock + local rules-based)
- native PDF text/coordinate extraction and AcroForm widget metadata (PyMuPDF)
- OCR-result consumption
- label detection, field-type classification, confidence scoring
- persisted, reviewable detection results
- idempotent detection API + field review API (confirm/edit/reject)
- question generation from confirmed fields via existing guided workflow
- frontend review UI, all 4 languages, RTL preserved
- tests, docs, ADR 0010

## Out of scope

- automatic filling or export of arbitrary uploaded PDFs
- signature/handwriting recognition
- cloud AI providers, background workers, object storage
- user accounts, payments, admin dashboards
- Phase 12

## Status

Initialized. See `docs/phases/phase-11-dynamic-field-detection.md` for the full specification and root `TODO.md` for current acceptance-criteria/verification state. Implementation not yet started.
