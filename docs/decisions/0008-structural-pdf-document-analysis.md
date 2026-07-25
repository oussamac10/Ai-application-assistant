# ADR 0008 — Structural PDF Document Analysis

**Status:** Accepted  
**Phase:** 9 — Form Upload and Document Analysis  
**Date:** 2026-07-25  

---

## Context

Phase 9 introduces a document-upload workflow that allows users to submit a PDF form through the AI Form Assistant. Before any session or guided workflow can begin, the backend must:

1. Validate the uploaded file is a safe, well-formed PDF.
2. Structurally analyze the document (page count, text presence, interactive fields, embedded images).
3. Match it against a set of pre-defined fingerprints to determine whether it corresponds to a supported form template.
4. Return an analysis result that drives the frontend's next-step recommendation.

This ADR documents the architectural decisions made for this feature.

---

## Decisions

### 1. Validation happens before storage

All security checks (PDF signature, page count, encryption, active content) are performed **after writing the file to a temporary path** but **before storing the database record**. If validation fails, the temporary file is deleted and no record is persisted.

This avoids storing files that do not pass security requirements and keeps the database clean.

### 2. File validation order

```text
1. Content-type check (application/pdf or .pdf extension)
2. File size check (configurable via DOCUMENT_UPLOAD_MAX_BYTES, default 10 MB)
3. PDF signature check (%PDF header)
4. PDF structure check (parseable by pypdf, page count within limit, not zero pages)
5. Encryption check (reject encrypted/password-protected files)
6. Safety check (reject JavaScript, OpenAction, AA, Launch action, embedded attachments)
```

Deterministic code performs all these checks — no AI is involved.

### 3. Structural analysis is separate from validation

`PDFAnalyzer` operates **after** validation succeeds. It extracts:

- Page count and per-page dimensions
- Whether native text is present (character count heuristic)
- Whether embedded images exist (XObject Image detection)
- Whether AcroForm interactive fields exist (Widget annotation count)

This separation allows the validation layer to remain stateless and pure, while the analyzer builds a richer structural picture.

### 4. Document classification uses heuristics, not AI

The `document_type` classification (`digital_pdf`, `fillable_pdf`, `scanned_pdf`, `hybrid_pdf`, `unknown`) is computed deterministically from analyzer output:

```text
has_acroform + has_native_text → fillable_pdf
not has_acroform + has_native_text + not has_images → digital_pdf
not has_any_native_text + has_images → scanned_pdf
has_native_text + has_images → hybrid_pdf
otherwise → unknown
```

This follows the principle: use deterministic code when AI is not required.

### 5. Template matching uses fingerprint files

Pre-defined templates are described by JSON fingerprint files in `fixtures/pdf/`. Each fingerprint records:

- Expected page count
- Expected page dimensions (with configurable tolerance: ±5 points)
- Required AcroForm field names
- Optional text markers that must appear in the document text

Template matching runs **after analysis**. The registry loads all fingerprints from the fixtures directory and evaluates each one against the current document's analysis results.

If exactly one fingerprint matches → `supported_template` is returned with the matched template key.  
If zero or multiple fingerprints match → `dynamic_field_detection` or `review_required` is returned.

### 6. OCR is explicitly out of scope for Phase 9

Documents classified as `scanned_pdf` return `next_step: ocr_required`. No OCR engine is invoked. This is a Phase 10 responsibility.

### 7. Storage uses random UUIDs, not original filenames

The `DocumentStorage` class writes files to `DOCUMENT_STORAGE_PATH` under a randomly generated UUID-based subdirectory. The original filename is sanitized and stored in the database, but the storage path is opaque.

This prevents:
- Directory traversal attacks
- Filename collision
- Predictable URL enumeration

### 8. Ownership tokens follow the same HMAC pattern as sessions

Document ownership tokens use the same `generate_ownership_token` / `hash_ownership_token` pattern used for session credentials. The raw token is returned once at upload time and never stored. The hash is stored in the database and compared on subsequent requests.

### 9. Documents expire after 24 hours by default

`expires_at` is set at upload time using `DOCUMENT_EXPIRATION_HOURS` (default: 24). The cleanup CLI (`cleanup_expired_exports`) purges both the file from disk and updates the database status to `deleted`.

### 10. Session creation from a document is a separate step

After analysis, the frontend calls `POST /api/source-documents/{document_id}/session` to create a guided workflow session. This step:

- Validates document ownership
- Validates document is in `analyzed` state
- Resolves the matched form template and version from the database
- Delegates to `SessionService` to create the session
- Returns the session ID and token

This separation allows users to review the analysis result before committing to a session.

---

## Consequences

### Positive

- All file security checks are deterministic and testable without a running AI service.
- The analysis pipeline is composable and independently testable.
- Template matching supports future expansion simply by adding new fingerprint files.
- The separation of validation / analysis / matching / session creation reduces coupling between subsystems.

### Negative / Trade-offs

- Fingerprint-based matching requires manual curation for each new supported template.
- Scanned PDFs cannot be processed until Phase 10 introduces OCR.
- Documents with active content (JS, Launch) are rejected entirely — this is intentional but may frustrate power users with legitimate PDFs.

---

## Related

- [AGENTS.md §19 — Upload and OCR Rules](../../.agents/AGENTS.md)
- [fixtures/pdf/basic-registration-v1.fingerprint.json](../../fixtures/pdf/basic-registration-v1.fingerprint.json)
- [backend/app/documents/](../../backend/app/documents/)
- [backend/tests/documents/test_documents.py](../../backend/tests/documents/test_documents.py)
