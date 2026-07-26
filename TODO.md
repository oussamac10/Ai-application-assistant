# Project TODO

## Completed Phases

| Phase | Branch | Status |
|---|---|---|
| 1 — Project Foundation | `main` | ✅ Done |
| 2 — Form Definitions and Versioning | `feature/form-definitions-versioning` | ✅ Done |
| 3 — Temporary Anonymous Sessions | `feature/anonymous-sessions` | ✅ Done |
| 4 — Mock Question and Answer Workflow | `feature/mock-qa-workflow` | ✅ Done |
| 5 — Local AI Integration with Ollama | `feature/local-ai-ollama` | ✅ Done |
| 6 — Reusable Question Catalog and Hybrid Resolution | `feature/question-catalog-hybrid-resolution` | ✅ Done |
| 7 — Frontend Guided Form Experience | `feature/frontend-guided-experience` | ✅ Done |
| 8 — PDF Template Mapping and Export | `feature/pdf-template-export` | ✅ Done |
| 9 — Form Upload and Document Analysis | `feature/form-upload-analysis` | ✅ Done |
| 10 — OCR Integration | `feature/ocr-integration` | ✅ Done |

---

## Current Task

**Phase 11 — Dynamic Field Detection.** Branch: `feature/dynamic-field-detection`. Base: `feature/ocr-integration`.

## Goal

Analyze unrecognized uploaded forms (unmatched digital PDFs and OCR-processed scanned PDFs) and detect candidate form fields from native PDF text/coordinates, OCR text/lines/words/coordinates/confidence, and AcroForm widget metadata. Produce a normalized, persisted, user-reviewable field-detection result. Generate questions from confirmed fields only, via the existing guided-session workflow. Do not automatically fill arbitrary PDFs.

See `docs/phases/phase-11-dynamic-field-detection.md` for the full specification.

## Acceptance Criteria

- [ ] `FieldDetectionProvider` protocol
- [ ] deterministic `MockFieldDetectionProvider`
- [ ] rules-based `LocalFieldDetectionProvider`
- [ ] native PDF text + coordinate extraction (PyMuPDF)
- [ ] AcroForm widget metadata extraction (name, type, rect, page)
- [ ] OCR-result consumption as a detection input source
- [ ] label detection and label/input-area association
- [ ] field-type classification with deterministic ordering and confidence
- [ ] persisted `FieldDetectionResult`/`DetectedField`/`DetectedFieldOption` + reversible migration
- [ ] ownership + expiration checks reused from Phase 9
- [ ] idempotent detection API (`POST`/`GET /api/source-documents/{id}/field-detection`)
- [ ] field review API (confirm/edit/reject)
- [ ] question generation from confirmed fields only, via existing guided workflow
- [ ] frontend review UI, all 4 languages, RTL preserved
- [ ] backend, frontend, migration, and Playwright tests
- [ ] ADR 0010, `docs/field-detection.md`, updated docs
- [ ] Ruff, mypy, ESLint, TypeScript all pass
- [ ] Phase 7, 8, 9, 10 regressions preserved

## Planned Steps

- [x] Phase initialization and documentation
- [ ] Detection domain schemas and provider protocol
- [ ] Deterministic mock provider
- [ ] Persistence and reversible migration
- [ ] Native/OCR/AcroForm input normalization (extraction.py)
- [ ] Local heuristic provider
- [ ] Service, eligibility, idempotency, and API
- [ ] Field review API
- [ ] Question-generation bridge
- [ ] Frontend review UI
- [ ] Playwright tests
- [ ] Documentation and full verification

## Files Expected to Change

See `docs/phases/phase-11-dynamic-field-detection.md` "Files Expected to Change" — initial estimate, may be updated during implementation.

## Decisions and Assumptions

- Native-text and AcroForm geometry extraction uses PyMuPDF, independent of the Phase 9 `PDFAnalyzer` (which only counts, doesn't locate).
- Confirmed fields become a real, temporary, published `FormVersion` so the entire existing session/answer/PDF pipeline works unmodified.
- OCR-derived candidate coordinates stay in rendered-image pixel space (ADR 0009); native/AcroForm candidates stay in PDF point space — never silently mixed.
- Supported languages for generated questions remain en/de/fr/ar.

## Blockers

- None

## Verification

- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Playwright Phase 11 flows pass
- [ ] Ruff lint passes
- [ ] Phase 11 new/modified files pass Ruff formatting
- [ ] mypy passes
- [ ] ESLint passes
- [ ] TypeScript passes
- [ ] Migration downgrade and re-upgrade pass
- [ ] Acceptance criteria manually verified

---

## Next Phases (not yet started)

| Phase | Description |
|---|---|
| **12** | User accounts and persistent sessions |
| **13** | Administration and content review |

---

## Known Deferred Items (carried from Phase 10)

- Full Playwright regression result: **15 of 16 passed**
- One guided-flow test requires a published Basic Registration v1 form fixture seeded in the local test database
- The failure is unrelated to OCR or Phase 11, but the full suite must be re-verified in a correctly seeded environment before claiming a full pass
- Full repository Ruff formatting still includes pre-existing formatting issues under `app/documents/`, predating Phase 10 and intentionally left unchanged
