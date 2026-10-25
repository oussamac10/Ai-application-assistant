# Project TODO

## Completed Phases

Archived under `docs/progress/`:

1–18. Core MVP & Hybrid Multilingual Pipeline (`phase-1` through `phase-18-explanations-and-checklist.md`)
- **SaaS Phase S0**: P0 Security, RBAC, Dynamic-Form Isolation, Credential Hardening & Retention (`docs/progress/phase-s0-security-and-hardening.md`)
- **SaaS Phase S1**: Storage Provider, Smartphone Camera Scan Normalization, Multi-Script OCR + Async Jobs & Rate Limiting, and Embedded Unicode/RTL PDF + Watermarked Preview (`docs/progress/phase-s1-storage-camera-async-unicode.md`)

---

## Current Task

**Phase S1 Live-Scan & Guided-Session Bugfixes**: Fix duplicate required asterisks (`* *`), OCR-corrupted trailing required asterisk (`Nachname ":` -> `Last name "`), and misaligned `DOCUMENT PLACEMENT` preview / missing raster box coordinates on scanned & camera-uploaded forms.

## Goal

Ensure scanned and camera-uploaded forms (`JPG/PNG/WebP` and raster PDFs) detect drawn input boxes accurately, scale all location bounding boxes into PDF point space for `DOCUMENT PLACEMENT` preview and PDF overlay export, preserve requiredness even when OCR misreads `*:` as `":`, and display clean single-asterisk required headings in the UI.

## Acceptance Criteria

- [x] Required fields never render duplicate asterisks (`* *`) in guided session or summary UI; `question_bridge` strips requiredness markers and trailing colons from `FormField` display labels after resolving `requiredness`.
- [x] OCR-corrupted unpaired trailing `<space>"` / `<space>":` required markers on `source == "ocr"` labels (e.g. `Nachname ":` -> `Nachname *`) are normalized deterministically so requiredness (`required`) is preserved and `"` never leaks into the display label.
- [x] `get_field_location_for_session` converts both `input_bounding_box` and `label_bounding_box` from OCR pixel coordinates into PDF point coordinates (`page_width_pt` x `page_height_pt`), eliminating bottom-of-page (`96%`) highlight clamping.
- [x] `extract_ocr_document_input` filters empty-box border OCR hallucinations and extracts raster `RuledRegion`s (drawn boxes and underlines) with resolution-aware `visual_fields` thresholds so scanned/camera forms highlight and export inside the actual drawn input boxes.
- [x] All backend (`ruff`, `mypy`, isolated `pytest` on `ai_form_assistant_test`) and frontend (`typecheck`, `lint`, `vitest`) checks pass with fresh verification evidence.

## Planned Steps

- [x] 1. Write failing RED tests for duplicate asterisk stripping & clean display labels (`backend` + `frontend`) and verify RED.
- [x] 2. Write failing RED tests for OCR unpaired-quote asterisk normalization (`Nachname ":` -> `required`), `label_bounding_box` OCR->PDF coordinate scaling, and raster `RuledRegion` + empty-box OCR noise filtering; verify RED.
- [x] 3. Implement minimal backend & frontend fixes to turn all tests GREEN.
- [x] 4. Run full backend + frontend verification suites, verify on the synthetic scanned/camera test forms, restart `worker`, and update `TODO.md` / `docs/progress/phase-s1-storage-camera-async-unicode.md`.

## Files Expected to Change

- `backend/app/field_detection/requiredness.py`
- `backend/app/field_detection/question_bridge.py`
- `backend/app/field_detection/extraction.py`
- `backend/app/field_detection/visual_fields.py`
- `backend/app/field_detection/providers/local.py`
- `backend/app/pdf/dynamic_overlay.py`
- `backend/tests/field_detection/test_requiredness.py`
- `backend/tests/field_detection/test_requiredness_persistence.py`
- `backend/tests/field_detection/test_extraction.py`
- `backend/tests/field_detection/test_visual_fields.py`
- `backend/tests/pdf/test_dynamic_overlay_export.py`
- `frontend/src/features/form-session/utils/formatFieldLabel.ts`
- `frontend/src/app/application/session/[sessionId]/page.tsx`
- `frontend/src/app/application/session/[sessionId]/summary/page.tsx`
- `frontend/src/features/form-session/tests/guided-session-requiredness.test.tsx`
- `frontend/src/features/form-session/tests/summary-answer-states.test.tsx`

## Decisions and Assumptions

- Unpaired `<space>"` before optional colon at the end of an OCR line (`source == "ocr"`, `count('"') == 1`) is normalized to `*` only on OCR tokens/labels, never on native digital text or paired quotes (`See "Section A"`), preserving `docs/claude/domain-rules.md` deterministic evidence rules.
- Raster `RuledRegion` detection uses pure C-accelerated `Pillow` (`ImageFilter.BoxBlur` + `ImageChops.subtract`) with zero new third-party dependencies.

## Blockers

- None

## Verification

- [x] Backend `ruff check .`, `ruff format --check .`, and `mypy app` pass
- [x] Backend isolated `pytest` (`ai_form_assistant_test`) passes
- [x] Frontend `npm run typecheck`, `npm run lint`, and `npx vitest run` pass
