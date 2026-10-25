# Phase S1 — Storage Provider, Camera Scan Normalization, Async Jobs & Unicode/RTL PDF

**Status:** Completed & Verified (`2026-10-25`)

## Summary of Changes

1. **`S1-01` Pluggable `StorageProvider` & Persistent Volumes**:
   - Implemented `StorageProvider` Protocol (`backend/app/storage/base.py`), `LocalStorageProvider` (`backend/app/storage/local.py`), zero-bloat AWS Signature Version 4 `S3StorageProvider` (`backend/app/storage/s3.py`) over `httpx` (compatible with EU Hetzner Object Storage, Cloudflare R2, MinIO, and AWS S3), and `get_storage_provider()` factory (`backend/app/storage/factory.py`).
   - Refactored `documents`, `ocr`, `field_detection`, `pdf`, and `cleanup_expired_exports` to persist, materialize (`local_path`), read, and delete artifacts via storage keys while retaining backward compatibility with legacy paths.
   - Configured persistent `storage_data:/var/lib/ai-form-assistant/storage` volume in `docker-compose.yml`.

2. **`S1-02` Smartphone Camera Image Upload (`JPG/PNG/WebP` -> EXIF Strip -> A4 PDF)**:
   - Added `backend/app/documents/image_normalizer.py` enforcing magic-byte detection (`%PDF`, JPEG, PNG, WebP), `40 MP` decompression-bomb cap (`DOCUMENT_UPLOAD_MAX_IMAGE_PIXELS`), `ImageOps.exif_transpose` orientation correction, 100% EXIF/GPS/ICC metadata stripping via raw pixel reconstruction, and ISO A4 portrait/landscape PDF wrapping before structural analysis.
   - Updated frontend upload picker (`DocumentUploadForm.tsx`), upload error mapping (`resolveUploadErrorMessage.ts`), and all four UI locales (`en`, `de`, `fr`, `ar`).

3. **`S1-03` Multi-Script OCR Fix + Async `prepare-questions` Worker (`202` + `/api/jobs/{id}`) + Rate Limiting**:
   - Expanded OCR language support (`deu`, `eng`, `fra`, `ara`, `tur`, `ukr`, `spa` + multi-script `auto` decoupled from `userLanguage` in `orchestration.py` and `providers/local.py`; added `tesseract-ocr-{tur,ukr,spa}` in `backend/Dockerfile`).
   - Added `processing_jobs` table + Alembic migration `b2c3d4e5f6a7_add_processing_jobs_phase_s1.py`, Fernet-encrypted transient session token envelope (`app/jobs/crypto.py`), `GET /api/jobs/{job_id}` ownership-checked status endpoint, Redis + ARQ `WorkerSettings` (`app/jobs/worker.py` + `docker-compose.yml` `redis` & `worker` services), `202 Accepted` queuing on slow `prepare-questions`, and frontend `202` job polling (`field-detection/services/apiClient.ts`).
   - Added Redis + thread-safe in-memory sliding-window rate limiter (`app/core/rate_limit.py`) returning `429 Too Many Requests` + `Retry-After` on upload, preparation, register, and login routes.

4. **`S1-04` Embedded `NotoSans` + `NotoSansArabic` TTF PDF Overlay + Watermarked Preview**:
   - Bundled SIL Open Font License (`OFL-1.1`) `NotoSans-Regular.ttf` and `NotoSansArabic-Regular.ttf` in `backend/app/pdf/fonts/` and implemented `backend/app/pdf/font_support.py` (`draw_unicode_text_in_box` + `apply_preview_watermark`) with MuPDF HarfBuzz glyph shaping, flush-right RTL alignment, mixed-script `<span class="lat">` fallback preventing `.notdef` tofu glyphs, and Unicode AcroForm fallback in `PypdfRenderer`.
   - Added ownership-protected ephemeral watermarked preview endpoint `GET /api/form-sessions/{session_id}/preview-pdf` (zero `FormExport` DB writes) and summary-page preview button (`summary/page.tsx` + `en/de/fr/ar` translations).

5. **Live-Scan & Guided-Session Verification Fixes**:
   - Stripped requiredness markers (`*`, `(*)`, `(Optional)`) and trailing colons from `FormField` display labels in `question_bridge.py` (after `_resolve_requiredness`) and added `formatFieldLabel.ts` in `frontend/src/features/form-session/utils/` so guided-session and summary headings never render duplicate `* *`.
   - Updated `requiredness.py` to detect asterisks immediately preceding trailing colons (`Vorname *:`, `Nom (*):`), and updated `extraction.py` to recover unpaired OCR-corrupted trailing quote-asterisks (`Nachname ":` -> `Nachname *:`) and filter wide empty-box border OCR hallucinations (`"PT"`, `"|"`, `"اا"`).
   - Added pure-Pillow C-accelerated raster `RuledRegion` (`box` & `underline`) detection in `extract_ocr_document_input`, resolution-aware scaling + border-noise filtering in `visual_fields.py`, OCR source preservation in `local.py`, and OCR-pixel-to-PDF-point scaling for `label_bounding_box` in `dynamic_overlay.py` so `DOCUMENT PLACEMENT` highlights and PDF overlays align inside drawn input boxes on scanned/camera uploads.

## Verification Results

- `docker compose config -q`: **Passed (`0` errors)**
- Backend (`ruff check .`, `ruff format --check .`, `mypy app` across `188` files): **Passed (`0` errors)**
- Backend `pytest` (`ai_form_assistant_test` isolated DB, mock AI/translation providers): **`1,170 passed, 1 skipped, 0 failed`**
- Visual PDF verification (`150 DPI` PNG inspection): **Verified crisp shaped RTL Arabic, Ukrainian Cyrillic, Turkish diacritics, zero `.notdef` tofu boxes, and diagonal watermark**
- Frontend (`npm run typecheck`, `npm run lint`, `npx vitest run`): **`29/29` test files (`242/242` tests passed)**
