# Phase 14 — Azure Document Intelligence Provider

**Branch:** `feature/azure-document-intelligence`
**Base:** `feature/automatic-upload-to-questions`
**Status:** Complete — verified against the live Azure service

## Objective

Add Azure Document Intelligence as a **second, opt-in** field-detection provider alongside
the local rules-based detector, and prove Azure output converts into the app's existing
internal detected-field format. The local provider stays the default. Hybrid/fallback
between providers is **Phase 15** and is deliberately not implemented here.

See [ADR 0013](../decisions/0013-azure-document-intelligence-provider.md) for the rationale.

## What changed

### Backend

| File | Purpose |
|---|---|
| `app/core/config.py` | Seven `AZURE_DOCUMENT_INTELLIGENCE_*` settings; `azure` added to the supported providers; validation that fails fast **only** when Azure is the selected provider |
| `app/field_detection/providers/azure_client.py` (new) | REST transport: submit PDF, poll the operation, bounded timeout/retries, status→error-code mapping, request-id capture |
| `app/field_detection/providers/azure.py` (new) | The provider: combines Azure `keyValuePairs` with the shared local text passes |
| `app/field_detection/azure_normalization.py` (new) | Polygon→`BoundingBox` (inch/pixel/normalized, rotation, multiple/missing polygons), words/selection-marks→`DetectionToken`, key-value→`DetectedFieldCandidate` |
| `app/field_detection/usage.py` (new) | `ProviderUsageRecord` + `record_provider_usage()` |
| `app/field_detection/errors.py` | `AzureDocumentIntelligenceError` and the six safe `AZURE_ERROR_CODES` |
| `app/field_detection/service.py` | `azure` in the factory; `detection_fingerprint` caching; usage recording for success / failure / cache hit |
| `app/field_detection/models.py` | `FieldDetectionResult.detection_fingerprint` |
| `app/field_detection/providers/base.py` | `DetectionDocumentInput.source_pdf_path` (a remote provider must upload the original file) |
| `app/field_detection/providers/local.py` | `detect_from_tokens()` made public so Azure can reuse the text passes |
| `migrations/versions/40175fb1902b_*.py` | `provider_usage_records` table + `detection_fingerprint` column |

### Frontend

**No changes.** The normal-user flow is provider-agnostic: upload → processing → guided
questions, exactly as in Phase 13. The provider is a backend deployment choice.

## How detection works with Azure

1. `FieldDetectionService` passes the stored PDF path in `DetectionDocumentInput`.
2. The client submits the file, polls the async operation, and returns the plain-JSON
   `analyzeResult` (no SDK object ever enters the workflow).
3. Normalization converts each page's `unit`/`width`/`height` into scale factors, then:
   - `keyValuePairs` → candidates (Azure's own label↔input pairing — emitted **first**, so
     deduplication prefers it over layout inference);
   - `words` → `DetectionToken`s; `selectionMarks` → `"[_]"` marker tokens.
4. Those tokens are run through `LocalFieldDetectionProvider.detect_from_tokens()`, so all
   Phase 13 behaviour (blank runs, label-above-blank-line, sentence-embedded German
   date/currency blanks, party/`§`-section context, prose/heading exclusion) applies
   unchanged.
5. The merged candidates go through the existing low-confidence downgrade, deduplication
   and deterministic ordering, then the **unchanged** Phase 13 confidence routing.

## Configuration

```bash
FIELD_DETECTION_PROVIDER=azure
AZURE_DOCUMENT_INTELLIGENCE_ENABLED=true
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://<resource>.cognitiveservices.azure.com
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=<key>
AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID=prebuilt-layout
AZURE_DOCUMENT_INTELLIGENCE_API_VERSION=2024-11-30
AZURE_DOCUMENT_INTELLIGENCE_TIMEOUT_SECONDS=120
AZURE_DOCUMENT_INTELLIGENCE_MAX_RETRIES=1
```

Both `AZURE_DOCUMENT_INTELLIGENCE_ENABLED=true` **and** `FIELD_DETECTION_PROVIDER=azure`
are required — enabling one without the other is rejected at startup, so a document is
never sent to a third party by accident.

### Creating the Azure resource

1. Azure Portal → **Create a resource** → search **Document Intelligence** → Create.
2. Pick a subscription, resource group and region; choose a pricing tier (**F0** is the
   free tier — see limits below). Name the resource and create it.
3. Open the resource → **Keys and Endpoint**. Copy **Endpoint** into
   `AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT` and **KEY 1** into
   `AZURE_DOCUMENT_INTELLIGENCE_API_KEY`.
4. Put both in your local `.env` (never commit them — `.env` is git-ignored; only
   `.env.example`, which holds empty placeholders, is committed).

### Trying the model first in Document Intelligence Studio

Before wiring credentials into the app it is worth confirming the model handles your
document: open <https://documentintelligence.ai.azure.com/studio>, sign in, pick
**Layout**, select your resource, upload the PDF, and run **Analyze**. The Studio's
"Result" tab shows the exact `analyzeResult` JSON this provider consumes — pages, words,
polygons, selection marks and (model permitting) key-value pairs.

### Free-tier (F0) limitations

- Roughly 500 pages per month, and only the **first 2 pages** of each submitted document
  are analyzed. A 3-page contract therefore returns page 1–2 content only on F0, which will
  reduce the detected-field count versus a paid tier.
- Rate limited to a low requests-per-minute ceiling; the provider surfaces this as
  `azure_rate_limited` and retries once within the configured budget.
- One F0 resource per subscription per region.

## Privacy

Selecting the Azure provider means the uploaded PDF **leaves this system** and is processed
by Microsoft. That is why it is disabled by default and gated behind two explicit settings.
See `docs/privacy.md`. Usage records store only metadata *about* a request (page count,
duration, outcome, request id) — never document text, extracted values, or answers.

## Manual verification

Automated tests never call Azure. To verify against the live service:

1. Set the environment variables above (and `NEXT_PUBLIC_ENABLE_DETECTION_DEBUG_UI=false`).
2. `docker compose build backend && docker compose up -d --force-recreate backend`
3. Confirm the container sees the provider:
   `docker compose exec backend python -c "from app.core.config import settings; print(settings.FIELD_DETECTION_PROVIDER)"`
4. Upload `Jobcenter-LK-SM-Muster-Mietvertrag-Zimmer.pdf` through the normal UI at
   <http://localhost:3003/application>, or via the API:
   ```bash
   UP=$(curl -s -X POST http://localhost:8000/api/source-documents \
     -F "file=@Jobcenter-LK-SM-Muster-Mietvertrag-Zimmer.pdf;type=application/pdf" \
     -F "language=de" -F "outputLanguage=de" -F "privacyAccepted=true")
   DOC=$(echo "$UP" | python3 -c "import sys,json;print(json.load(sys.stdin)['documentId'])")
   TOK=$(echo "$UP" | python3 -c "import sys,json;print(json.load(sys.stdin)['ownershipToken'])")
   curl -s -X POST "http://localhost:8000/api/source-documents/$DOC/prepare-questions" \
     -H "X-Document-Token: $TOK" -H "Content-Type: application/json" \
     -d '{"language":"de","outputLanguage":"de"}'
   ```

**Measured on the live service** (resource `…-document-intelligence-dev`, `prebuilt-layout`,
api-version `2024-11-30`, `features=keyValuePairs`): `status: "ready"`, **24** guided
questions, first question `vermieter_name`, `vermieter_name` and `mieter_name` distinct, the
full `kontoinhaber` / `bank` / `iban` / `bic` block present, 3 date fields and 4 money fields
recovered from sentence-embedded blanks, plus 5 additive key-value fields (the
Hausschlüssel / Wohnungsschlüssel / Zimmerschlüssel group) that layout analysis alone
missed. The repeat request returned the same `sessionId` with `reusedExistingSession: true` in
0.1 s, and `provider_usage_records` held exactly one `served_from_cache=false` row
(`pages=2 duration=4.0s succeeded=true`). Neither the API key nor the endpoint appeared in the
backend logs.

**Expected:** `status: "ready"` with a `sessionId`; at least five usable questions;
landlord and tenant fields distinct (`vermieter_name` / `mieter_name`); no technical review
screen for a normal user; guided questions begin.

**Cost/idempotency check:** run `prepare-questions` a second time — it must return the same
`sessionId` with `reusedExistingSession: true`, and
`SELECT provider, succeeded, served_from_cache FROM provider_usage_records ORDER BY created_at;`
must show exactly **one** `served_from_cache = false` row for the document.

## Diagnostics

Every stage logs one safe, counts-only line (no document text, labels, values or
credentials). `LOG_LEVEL` controls verbosity; `app/main.py` configures logging explicitly
because uvicorn only sets up its own loggers — without that, none of these appeared:

```
Azure analyze started: model=prebuilt-layout api_version=2024-11-30 features=keyValuePairs bytes=487369
Azure analyze completed: model=... pages=2 duration=4.77s request_id=e7b7d196-...
Azure normalization: ... pages=2 lines=59 words=244 selection_marks=10 paragraphs=34
    tables=0 key_value_pairs=26 -> tokens=254 text_candidates=20 kv_candidates=21
    kv_kept=5 raw_candidates=25
Detection summary: document=... provider=azure provider_raw=25 after_dedup=24 unknown=0
    auto_confirmed=9 medium_usable=15 below_threshold_excluded=0 usable_total=24
Question generation input: document=... detected=24 usable=24 (mode=auto,
    accepted_statuses=confirmed,edited,pending_review) user_language=en output_language=de
Question generation result: document=... questions=24 skipped=0 version=published
    supported_output_languages=de,en
```

A reused result logs instead, with no provider call:

```
Detection cache HIT: document=... provider=azure model=prebuilt-layout candidates=24
    usable=24 (provider NOT called)
```

## Add-on features

`prebuilt-layout` returns **no** `keyValuePairs` unless `features=keyValuePairs` is
requested on the analyze call, which the client now does by default. If Azure rejects the
feature for a given model/api-version (HTTP 400) the call is retried once without it, so an
unsupported add-on degrades to layout-only rather than failing the document.

Key-value pairs are **additive only**: they are filtered against the text passes by region
overlap. Without that filter the real rental contract produced 37 questions instead of 24 —
`iban` from a key-value pair alongside `mietkosten_iban` from the text passes (name-based
deduplication cannot equate the two), plus checkbox *option* labels ("Küche",
"Hausschlüssel") promoted to standalone questions.

## Known limitations

- **F0 free tier truncates to the first 2 pages.** Confirmed live: a `provider_usage_records`
  row for the 3-page rental contract reports `page_count=2`. This contract's fields all sit on
  pages 1–2 so nothing was lost, but any document with content on page 3+ needs a paid tier.
- Azure typed `PLZ, Ort` and `BIC` as `multiline_text` where the local provider yields
  `address` / `string`: Azure's word bounding boxes differ slightly from PyMuPDF's, so the
  "large blank gap below a lone label" heuristic fires. Cosmetic only (a textarea instead of a
  single-line input). Worth revisiting in Phase 15 when both providers can be compared directly.
- The application's `logger.info` diagnostics (including the Azure request id) are not emitted
  to stdout under uvicorn's default logging configuration — a pre-existing gap. The request id
  is always available in `provider_usage_records`.
- `prebuilt-layout` does not return `keyValuePairs` for every document; when it does not,
  detection falls back entirely to the shared text passes, i.e. local-provider parity plus
  selection marks.
- Scanned PDFs are supported by Azure directly, but the current orchestration still runs
  the Phase 10 OCR step first for `ocr_required` documents; using Azure *instead of* OCR is
  a Phase 15 concern.
- No fallback: an Azure failure fails the document with the generic processing error rather
  than retrying locally. That is Phase 15.
- `estimated_cost` is recorded as NULL — real pricing belongs to Phase 18.
