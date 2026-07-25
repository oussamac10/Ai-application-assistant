# PDF Export System Documentation

This document describes the PDF generation, mapping, and export architecture of the AI Form Assistant.

---

## 1. Core Architecture

The PDF export system operates on a configuration-driven strategy using standard fillable PDF documents containing interactive **AcroForm** fields.

```
+--------------------+      +--------------------+      +---------------------+
|    Form Session    | ---> |    Form Answers    | ---> | PDFExportService    |
| (ready_for_export) |      |    (confirmed)     |      |                     |
+--------------------+      +--------------------+      +----------+----------+
                                                                   |
                                                                   v
+--------------------+      +--------------------+      +----------+----------+
|  JSON Mapping File | ---> | PDFMappingLoader   | ---> |     pypdf Writer    |
|  (field locations) |      |                    |      |                     |
+--------------------+      +--------------------+      +----------+----------+
                                                                   |
                                                                   v
+--------------------+                                  +----------+----------+
|    FormExport DB   | <--------------------------------|  Generated PDF File |
| (status, checksum) |                                  |  (temporary storage)|
+--------------------+                                  +---------------------+
```

- **Registry**: Loads PDF templates and JSON mappings from the `fixtures/pdf` directory.
- **Loader**: Parses and validates mapping configurations, ensuring there are no duplicate mappings.
- **Renderer**: Uses `pypdf` to write string values to the AcroForm form fields in a copy of the template, preserving interactive features if required, and saves it to a private temporary directory.
- **Validator**: Ensures the generated file has a `%PDF-` signature, has a non-zero file size, and computes a SHA-256 checksum for audit and integrity checks.
- **Service**: Orchestrates the export workflow: checks session status (must be `ready_for_export`), confirms user ownership via custom token header, formats canonical values, applies overflow policies, registers the `FormExport` record, runs rendering, and handles cleanup.

---

## 2. Formatting and Normalization

Canonical answers are formatted deterministically based on their field type and the `outputLanguage` of the session before being written to the PDF.

| Field Type | Canonical Format (DB) | Output Language | Formatted Output (PDF) |
|---|---|---|---|
| `date` | `YYYY-MM-DD` | `de` | `DD.MM.YYYY` |
| | `YYYY-MM-DD` | `fr` / others | `DD/MM/YYYY` |
| `boolean` | `true` / `false` | `de` | `Ja` / `Nein` |
| | `true` / `false` | `fr` | `Oui` / `Non` |
| | `true` / `false` | `ar` | `نعم` / `لا` |
| | `true` / `false` | `en` / others | `Yes` / `No` |
| `multiple_choice` | `["a", "b"]` | Any | `A, B` |
| `money` | `{"amount": 1000, "currency": "EUR", "period": "monthly"}` | Any | `1,000 EUR monthly` |
| `address` | `{"street": "X", "postal_code": "Y", "city": "Z", "country": "W"}` | Any | `X, Y Z, W` |

---

## 3. Constraint & Overflow Policies

Each field mapping defines a `maxLength` and an `overflow` policy:

1. **`reject`**: If the formatted value exceeds `maxLength`, the system aborts and throws a `ValidationError` (422), which is displayed as a validation overflow error on the frontend.
2. **`truncate`**: The value is trimmed to fit `maxLength`.
3. **`wrap`**: The value is written as-is, letting the PDF viewer handle display wrapping.

---

## 4. API Endpoints

### 4.1 Export Generation
- **Path**: `POST /api/form-sessions/{session_id}/exports`
- **Headers**:
  - `X-Session-Token: <token>` (Required)
- **Response** (200 OK):
  ```json
  {
    "exportId": "public-uuid-here",
    "status": "completed",
    "fileName": "registration-2026-07-25.pdf",
    "contentType": "application/pdf",
    "fileSize": 12500,
    "expiresAt": "2026-07-26T22:00:00Z",
    "downloadUrl": "/api/form-exports/public-uuid-here/download"
  }
  ```
- **Errors**:
  - `401 Unauthorized`: Token is missing or invalid.
  - `404 Not Found`: Session does not exist.
  - `409 Conflict`: Session is not in `ready_for_export` status.
  - `422 Unprocessable Entity`: Formatted value violates `maxLength` under the `reject` policy.

### 4.2 PDF Download
- **Path**: `GET /api/form-exports/{export_id}/download`
- **Headers**:
  - `X-Session-Token: <token>` (Required)
- **Response**: Binary stream of the PDF file.
- **Errors**:
  - `401 Unauthorized`: Token does not match the session owner.
  - `404 Not Found`: Export record or session does not exist.
  - `422 Unprocessable Entity`: Export has expired (TTL 24 hours) or file is deleted.

---

## 5. Security & Expiration

1. **Private Storage**: Export files are saved in `/tmp/ai-form-assistant/exports/` using random UUID filenames (e.g., `basic-registration-v1-uuid.pdf`). The internal storage path is never exposed in API responses.
2. **Token Authentication**: Ownership is verified using the HMAC-SHA256 hash stored in the session record, passed strictly via request headers.
3. **Cleanup**: Expired exports are deleted by calling `python -m app.commands.cleanup_expired_exports`. This command should be scheduled (e.g. via Cron) to run periodically in production.
