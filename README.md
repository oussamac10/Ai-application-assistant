# AI Form Assistant

A multilingual AI form assistant that helps users understand and complete forms written in languages they may not speak.

## Project Purpose

The AI Form Assistant bridges the language gap by allowing users to complete forms in three separate language concepts:
* `sourceLanguage`: The language of the original form.
* `userLanguage`: The language used for questions, clarifications, and explanations.
* `outputLanguage`: The language used in the completed form.

It guides the user through the form one field at a time, normalizing, validating, and confirming answers.

## Current Phase: Phase 15 — Azure Translator Integration

See [`docs/claude/current-phase.md`](docs/claude/current-phase.md) and
[`docs/phases/phase-15-azure-translator.md`](docs/phases/phase-15-azure-translator.md).
Translation now lives behind its own `TranslationProvider` abstraction (mock / Ollama / Azure
Translator) rather than riding on the AI provider, the document's source language is detected
instead of assumed, and only the interface language is translated during question preparation —
see "Optional: Azure Translator" below and
[ADR 0015](docs/decisions/0015-translation-provider-and-azure-translator.md).

Phase 14 (completed) added Azure Document Intelligence as an **opt-in** second field-detection
provider alongside the local detector — see "Optional: Azure Document Intelligence field
detection" below and [ADR 0013](docs/decisions/0013-azure-document-intelligence-provider.md).

Phase 13 (completed) made uploading a PDF analyze, detect fields and start guided questions
automatically, with no manual field-review step for normal users — see
[`docs/field-detection.md`](docs/field-detection.md) and
[ADR 0012](docs/decisions/0012-automatic-confidence-routing.md).

### MVP Phase 7 — Frontend Guided Form Experience (original foundation)

The sections below describe Phase 7, the guided-form UI foundation the product still builds on:
* **Client-Side UI Localization**: Dynamic switching between English (`en`), Deutsch (`de`), Français (`fr`), and Arabic (`ar`).
* **Arabic RTL Layout Support**: Automatic toggling of HTML `dir="rtl"` and RTL-compliant UI flows when Arabic is selected.
* **Privacy Notice Compliance**: Explicit checkbox acceptance is required before starting any session.
* **Secure Anonymous Session Ownership**: Storing `ownershipToken` in client-side `sessionStorage` instead of URLs to prevent credentials leakage.
* **14 Field Type Components**: Usable Tailwind-styled input components rendered dynamically via a central `FieldRenderer` dispatcher.
* **Clarification & Normalization Workflows**: Sidebar clarification sub-forms asking for missing inputs, and confirmation screens comparing original inputs side-by-side with proposed normalized values.
* **Back-Navigation & Edit Hooks**: Clean `Back` button navigation preserving raw inputs, and direct editing from the summary review page.
* **Progress Tracking**: Progress metrics fetched dynamically from backend calculations.
* **Final Summary Review**: Complete summary page displaying all questions and confirmed values, final confirmation checks, and transition to a completed screen.

*Note: OCR, document uploads, account registration, and PDF export generation are omitted from Phase 7.*


---

## Prerequisites

Before starting, ensure you have the following installed on your host system:
* **Docker** & **Docker Compose**
* **Node.js** (v20 or higher) & **npm**
* **Python** (v3.11 or v3.12)
* **Git**

---

## Environment Configuration

Copy the example environment file:
```bash
cp .env.example .env
```
Safe defaults are provided for local development.

---

## Running Locally

### Starting with Docker Compose

To build and start the complete local development environment (postgres database, FastAPI backend, and Next.js frontend):
```bash
docker compose up --build
```

### Service URLs

Once running, services are accessible at:
* **Frontend Application**: `http://localhost:3003`
* **FastAPI Backend Application**: `http://localhost:8000`
* **Backend API Docs (Swagger)**: `http://localhost:8000/docs`
* **PostgreSQL Database**: `localhost:5432`

---

## Service Verification & Health Checks

You can verify service status using:
* **Backend Status API**: `curl -i http://localhost:8000/api/health`
* **Backend Database Status API**: `curl -i http://localhost:8000/api/health/database`

---

## Local Development Commands

### Backend Commands (from `./backend`)

Before running commands, initialize the virtual environment:
```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

* **Run Server**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
* **Run Tests**: `PYTHONPATH=. pytest`
* **Format Check**: `ruff format --check .`
* **Auto-format**: `ruff format .`
* **Lint Check**: `ruff check .`
* **Auto-fix Lint**: `ruff check --fix .`
* **Type Check**: `mypy app`
* **Initialize alembic**: Already initialized. To run migrations: `alembic upgrade head`
* **Load Fixture**: `python -m app.commands.load_fixture` (loads the Basic Registration multilingual template version 1 and publishes it)
* **Cleanup Expired Sessions**: `python -m app.commands.cleanup_expired_sessions` (scans and marks expired open sessions as expired)

### Frontend Commands (from `./frontend`)

Before running commands, install node modules:
```bash
cd frontend
npm install
```

* **Run Dev Server**: `npm run dev`
* **Run Tests**: `npm test`
* **Lint Check**: `npm run lint`
* **Type Check**: `npm run typecheck`
* **Build Project**: `npm run build`

---

## Decisions & Important Assumptions

1. **Port Configuration**: Due to common host port collisions (e.g. DDEV mapping ports 3000-3001), the frontend port on the host has been mapped to `3003`. Internally, the container exposes port `3000`.
2. **API Proxying**: Next.js uses client-side proxy rewrites in `next.config.js` to route all `/api/*` calls from the browser to the backend (`http://backend:8000`). This completely eliminates CORS issues.
3. **Database Health Failures**: In `/api/health/database`, we return a `503 Service Unavailable` status code with `{"status":"error", "database":"unavailable"}` if database connections fail, which is handled gracefully by the frontend.
4. **Python Version**: Development virtual environment was set up with Python 3.12 on the host to avoid source compilations of pre-wheels packages on Python 3.14.

---

## Optional: Azure Document Intelligence field detection

Field detection defaults to a fully local, rules-based provider that sends nothing off the
machine. Azure Document Intelligence can be selected instead (Phase 14):

```bash
FIELD_DETECTION_PROVIDER=azure
AZURE_DOCUMENT_INTELLIGENCE_ENABLED=true
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://<resource>.cognitiveservices.azure.com
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=<key from "Keys and Endpoint">
AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID=prebuilt-layout
```

Create the resource in the Azure Portal (**Create a resource → Document Intelligence**),
then copy **Endpoint** and **KEY 1** from its *Keys and Endpoint* blade into your `.env`.
To sanity-check the model against a document first, upload it to
[Document Intelligence Studio](https://documentintelligence.ai.azure.com/studio) and run
**Layout**.

> **This uploads your PDF to Microsoft.** It is therefore disabled by default and requires
> *both* `AZURE_DOCUMENT_INTELLIGENCE_ENABLED=true` and `FIELD_DETECTION_PROVIDER=azure`.
> The API key is backend-only and is never exposed to the frontend or logged. The free F0
> tier analyzes only the first 2 pages per document.

Full setup, verification steps and known limitations:
[`docs/phases/phase-14-azure-document-intelligence.md`](docs/phases/phase-14-azure-document-intelligence.md).

## Optional: Azure Translator

Question labels and choice options are translated by a `TranslationProvider`, selected
independently of the AI provider. The default keeps everything local:

```bash
TRANSLATION_PROVIDER=ollama
TRANSLATION_FALLBACK_PROVIDER=none
```

Azure Translator can be selected instead (Phase 15), with Ollama kept as a safety net:

```bash
TRANSLATION_PROVIDER=azure
TRANSLATION_FALLBACK_PROVIDER=ollama
AZURE_TRANSLATOR_ENABLED=true
AZURE_TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
AZURE_TRANSLATOR_API_KEY=<key from "Keys and Endpoint">
AZURE_TRANSLATOR_REGION=<the resource's region, e.g. westeurope>
```

Create the resource in the Azure Portal (**Create a resource → Translator**), then copy **KEY 1**
and **Location/Region** from its *Keys and Endpoint* blade. The region header is required for a
regional resource — Azure rejects the request without it.

> **This sends field labels and choice-option labels to Microsoft** — not the document, not its
> full text, and not any answer a user typed. Text that is entirely an identifier (email, IBAN,
> BIC, date, phone number, amount, URL, UUID, internal key) is detected deterministically and never
> transmitted. Disabled by default; requires *both* `AZURE_TRANSLATOR_ENABLED=true` and
> `TRANSLATION_PROVIDER=azure`. The API key is backend-only and is never exposed to the frontend or
> logged.

> **The endpoint must be a Translator resource.** A Document Intelligence endpoint answers
> `404` for `/translate` and `401` for `/translator/text/v3.0/translate` — its key is not valid
> for Translator. Create a separate **Translator** resource.

## Automatic document-language detection

The uploaded form's own language is detected locally (no third party, no extra dependency) once
per document, persisted, and reused. It sets the generated form version's `source_language`,
drives RTL-aware field grouping for Arabic/Hebrew/Persian/Urdu, and lets Azure Translator be
asked to detect rather than being told a wrong `from=`.

When a document has too little text the result is `und` ("undetermined"), which is never silently
turned into English. The three language concepts stay separate: `source_language` describes the
document, `user_language` the interface, `output_language` the completed form. Interface direction
(`lang`/`dir`) follows `user_language` only — an Arabic form in an English interface stays LTR.

Full setup, benchmark and known limitations:
[`docs/phases/phase-15-azure-translator.md`](docs/phases/phase-15-azure-translator.md).

---

## Common Troubleshooting

### Port 3000/3003 is already in use
If Docker fails to bind ports, run:
```bash
lsof -i :3003
```
and terminate any process occupying the port, or edit `ports` inside `docker-compose.yml`.

### Database Connection Failure
If the frontend shows `Database Connection: Unavailable` or backend health check logs connection errors, ensure the database container is fully initialized and healthy. You can verify it via `docker compose ps`.
To force recreate DB volumes, run:
```bash
docker compose down -v
docker compose up --build
```
