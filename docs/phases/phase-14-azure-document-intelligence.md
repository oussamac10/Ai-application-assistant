# Phase 14 — Azure Document Intelligence Provider

**Branch:** `feature/azure-document-intelligence`
**Base:** `feature/automatic-upload-to-questions`
**Status:** Implemented; live-service verification outstanding (see "Known limitations")

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

**Expected:** `status: "ready"` with a `sessionId`; at least five usable questions;
landlord and tenant fields distinct (`vermieter_name` / `mieter_name`); no technical review
screen for a normal user; guided questions begin.

**Cost/idempotency check:** run `prepare-questions` a second time — it must return the same
`sessionId` with `reusedExistingSession: true`, and
`SELECT provider, succeeded, served_from_cache FROM provider_usage_records ORDER BY created_at;`
must show exactly **one** `served_from_cache = false` row for the document.

## Known limitations

- **Live-service verification is outstanding.** No Azure credentials were available in the
  development environment, so the real endpoint has never been called. Everything is
  verified against a `prebuilt-layout`-shaped fixture whose words and polygons were
  generated from the real rental-contract PDF's own text layer, driven through the real
  orchestration end-to-end. The steps above must be run once credentials exist before this
  phase is considered fully proven.
- The F0 free tier only analyzes the first 2 pages of a document (see above).
- `prebuilt-layout` does not return `keyValuePairs` for every document; when it does not,
  detection falls back entirely to the shared text passes, i.e. local-provider parity plus
  selection marks.
- Scanned PDFs are supported by Azure directly, but the current orchestration still runs
  the Phase 10 OCR step first for `ocr_required` documents; using Azure *instead of* OCR is
  a Phase 15 concern.
- No fallback: an Azure failure fails the document with the generic processing error rather
  than retrying locally. That is Phase 15.
- `estimated_cost` is recorded as NULL — real pricing belongs to Phase 18.
