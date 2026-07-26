# OCR Integration — User Guide

**Phase:** 10
**Feature:** OCR Integration

---

## Overview

When Phase 9's document analysis classifies an uploaded PDF as scanned or image-based (`next_step: ocr_required`), the AI Form Assistant can run local OCR (Optical Character Recognition) to extract its text. This runs entirely on the server — no document content is ever sent to a third-party service.

OCR produces **text and geometry only** (lines, words, bounding boxes, confidence). It does not identify which text belongs to which form field — that is Phase 11's responsibility.

---

## How to use it

### Step 1 — Upload a scanned document

Follow the [document upload flow](document-upload-analysis.md). If the analysis result shows **OCR Recognition Needed**, click **Start OCR**.

### Step 2 — Choose the document's language

On the OCR page, select the language the document is written in. Supported languages:

| Language | Code |
|---|---|
| English | `en` |
| Deutsch | `de` |
| Français | `fr` |
| العربية | `ar` |

### Step 3 — Run OCR

Click **Start OCR**. Processing happens synchronously; a spinner is shown while it runs. On completion, the extracted text for each page is displayed, along with the average per-page confidence score.

Re-visiting the OCR page for a document that has already completed OCR shows the same result without re-processing it — OCR requests are idempotent per document.

---

## What gets extracted

For each page:

- Full page text
- Individual lines, each with its own bounding box and confidence
- Individual words within each line, each with its own bounding box and confidence
- An average confidence score for the page

Bounding box coordinates are in the pixel space of the rendered page image (300 DPI by default), **not** PDF point space — see [ADR 0009](decisions/0009-local-ocr-provider.md) for details.

---

## Security and privacy

- OCR runs locally via `tesseract-ocr`; no document content leaves the server.
- Rendered page images are temporary — they are deleted immediately after each OCR run, whether it succeeds or fails.
- OCR results inherit the same private storage and ownership-token model as the source document (Phase 9): only the holder of the document's ownership token can request or view its OCR result.
- OCR results expire on the same schedule as source documents and are purged by the cleanup command, along with any leftover temporary render files from crashed runs.
- OCR text is never logged.

---

## Troubleshooting

### "This document does not require OCR"

The document was already classified as digital/fillable during upload analysis. OCR only runs on documents flagged `ocr_required`.

### "The selected language is not supported for OCR"

Choose one of the four supported languages listed above.

### "OCR processing failed"

The OCR engine could not process the document. Try again; if the problem persists, the source PDF may be corrupted or unreadable.

### "OCR is already in progress for this document"

Wait for the current OCR run to finish before starting a new one.

---

## Related

- [Document Upload and Analysis](document-upload-analysis.md)
- [ADR 0009 — Local OCR Provider](decisions/0009-local-ocr-provider.md)
- [backend/app/ocr/](../backend/app/ocr/)
