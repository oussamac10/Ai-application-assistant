# ADR 0007: Explicit PDF Template Mapping and Secure Export

## Status
Approved

## Context
In MVP Phase 8, the AI Form Assistant requires the ability to generate a completed PDF form based on the verified and confirmed answers from a user session. 
We must support:
- Filling a predefined PDF template.
- Mapping backend semantic field keys to specific fields in the PDF template without hardcoding coordinates in python code.
- Enforcing constraints such as max lengths and overflow policies.
- Validating the generated PDF before making it available to the user.
- Securing the PDF download endpoint so only the owner of the session can access/download it.
- Restricting download lifetime, tracking export records, and periodically cleaning up files.

## Decision
1. **AcroForm PDF Strategy**:
   - We utilize standard PDF forms containing fillable interactive AcroForm fields.
   - We use `pypdf`'s writer to populate the fields programmatically without having to maintain coordinate-based drawing code.

2. **Explicit JSON Mapping**:
   - PDF templates are mapped using explicit JSON configurations (e.g. `basic-registration-v1.mapping.json`).
   - The mapping file details:
     - `templateKey`: Unique key matching the PDF file.
     - `formVersionKey`: Links the mapping to an exact immutable form version key (e.g. `basic-registration:1`).
     - `strategy`: The filling strategy (e.g. `acroform`).
     - `fields`: Array of field mapping configurations:
       - `fieldKey`: Semantic key of the form field.
       - `pdfFieldName`: Matching interactive AcroForm field name in the PDF.
       - `format`: Specific formatter type (e.g. `person_name`, `date`, `email`, `country`, `single_choice`).
       - `maxLength`: Max length constraint.
       - `overflow`: Overflow policy (`reject`, `truncate`, or `wrap`).

3. **Deterministic Formatting & Normalization**:
   - Stored values are formatted based on the `outputLanguage` and formatter type. For example, dates are formatted as `DD.MM.YYYY` for German output or `DD/MM/YYYY` for French output.
   - If a formatted string exceeds `maxLength` on a field with `overflow: "reject"`, the service aborts and raises a `ValidationError` (422), which is handled by the frontend.
   - `overflow: "truncate"` trims the value to fit, and `wrap` leaves it to the PDF renderer.

4. **Security & Expiration**:
   - **Access Restriction**: Generating or downloading an export requires the same session ownership token verification used in the guided flow, matching the HMAC-SHA256 hash.
   - **Header-based Authentication**: The ownership token is sent in the custom `X-Session-Token` header, ensuring it never leaks in the URL or browser history.
   - **Temporary Storage**: Export files are stored in a private directory (e.g. `/tmp/ai-form-assistant/exports`) with random UUID-based filenames to prevent directory traversal and public enumeration.
   - **Expiration**: Export records and files expire after a configurable TTL (default 24 hours). A cleanup command deletes expired files on the disk.

5. **Validation & Integrity**:
   - The generated PDF is validated to verify it has a valid `%PDF-` signature, has a non-zero size, and computes a SHA-256 checksum that is saved in the database.

## Consequences
- **Configuration-Driven Mapping**: No coordinates are hardcoded in the codebase, enabling easy support for new PDF templates by writing JSON mapping files.
- **Strict Security**: Form exports are highly secure and private, preventing unauthorized downloads and ensuring data is automatically removed.
- **Robust Integration**: The frontend handles constraints, errors, and secure downloads gracefully using Blob URL generation.
