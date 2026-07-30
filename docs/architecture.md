# Architecture Documentation

This document explains the architecture of the AI Form Assistant backend and frontend.

## System Overview

The system is a monorepo consisting of:
1. **Next.js Frontend**: Serves the user interface and proxies API requests.
2. **FastAPI Backend**: Implements the business logic, schemas, validation, and REST API.
3. **PostgreSQL Database**: Persistent storage for form templates, versions, fields, options, and temporary sessions.

```mermaid
graph TD
    Client[Next.js Frontend] -->|REST API /api/*| App[FastAPI Backend]
    App -->|SQLAlchemy ORM| DB[(PostgreSQL Database)]
```

---

## Backend Layers

The backend follows a clean, layered architecture organized into domain packages:

```
+-------------------------------------------------------------+
|                      API Routing Layer                      |
| (app/forms/api/routes.py, sessions/api, answers/api/routes) |
+-----------------------------+-------------------------------+
                              |
                              v
+-----------------------------+-------------------------------+
|                       Service Layer                         |
|   (app/forms/services.py, sessions/services, answers/serv)  |
+-----------------------------+-------------------------------+
                              |
                              v
+-----------------------------+-------------------------------+
|                     Repository Layer                        |
|  (app/forms/repositories, sessions/repos, answers/repos)    |
+-----------------------------+-------------------------------+
                              |
                              v
+-----------------------------+-------------------------------+
|                       Database Models                       |
|    (app/forms/models.py, sessions/models, answers/models)   |
+-------------------------------------------------------------+
```

### 1. Database Models Layer (`models.py`)
Declares database entities mapped to Postgres tables using SQLAlchemy 2.0 type-safe `Mapped` and `mapped_column` annotations.

### 2. Repository Layer (`repositories.py`)
Separates persistence mechanics from business logic. Handles basic database queries and object creations.

### 3. Service Layer (`services.py`)
Contains the application's business rules and workflows (e.g., publishing check, cloning logic, configuration validation, session tokens hashing). Service methods are framework-agnostic and raise clean Python exceptions rather than FastAPI `HTTPException`.

### 4. API Routing Layer (`routes.py`)
Defines FastAPI endpoints, handles dependency injection (e.g., DB session), validates payloads with Pydantic, and returns JSON DTOs.

---

## Error Handling Pattern

To keep route handlers thin and business logic separate from HTTP concerns, exception handling is centralized in `backend/app/main.py` using global exception handlers:

- **ResourceNotFoundError** -> HTTP `404 Not Found`
- **StateConflictError** / **IntegrityError** -> HTTP `409 Conflict`
- **ValidationError** / **ConfigurationValidationError** -> HTTP `422 Unprocessable Entity`
- **UnauthorizedError** -> HTTP `401 Unauthorized` (used for invalid/missing session ownership tokens)

---

## Field-Detection Providers (Phase 11 / 14)

Field detection is behind a provider interface (`app/field_detection/providers/base.py`),
selected by `FIELD_DETECTION_PROVIDER`:

```
FieldDetectionProvider (Protocol)
├── MockFieldDetectionProvider          deterministic, for tests/dev
├── LocalFieldDetectionProvider         rules-based, no network, the default
└── AzureDocumentIntelligenceProvider   hosted Azure Document Intelligence (opt-in)
```

The Azure provider converts Azure `words`/`selectionMarks` into the same `DetectionToken`
shape the local provider consumes and reuses its text passes, then adds Azure's own
`keyValuePairs`. Deterministic confidence routing, ownership, and orchestration are
identical for every provider. Results are cached on a fingerprint of
(document checksum, provider, model id, analysis version), so switching providers
recomputes rather than serving stale cross-provider fields, and an unchanged configuration
never re-calls a paid service. See
[ADR 0013](decisions/0013-azure-document-intelligence-provider.md).

Question generation translates every detected label and choice option in **batched**,
deduplicated, cached requests (`app/ai/batch_translation.py`,
`AIProvider.translate_output_batch`) rather than one AI call per text, with bounded concurrency
across chunks. Translations map back by request id, never by response position. `prepare-questions`
is synchronous and can take tens of seconds; `next.config.js` raises the rewrite proxy's ceiling
accordingly and the upload flow retries a bare gateway failure, which is safe because the endpoint
is idempotent. See [ADR 0014](decisions/0014-batched-translation-and-request-duration.md).

Translation itself lives behind a dedicated `TranslationProvider` abstraction
(`app/translation/`), separate from `AIProvider`: mock, Ollama and Azure Translator implementations,
selected by `TRANSLATION_PROVIDER` with an optional fallback. Azure detects the document's source
language, which becomes the generated form version's `source_language` instead of an assumed one.
Only the interface language is translated during preparation; other supported languages hold
source-text placeholders that `app/translation/backfill.py` fills on demand. See
[ADR 0015](decisions/0015-translation-provider-and-azure-translator.md).

The uploaded form's own language is detected once by `app/language/` (script-first, then
function-word frequency; deterministic and dependency-free), persisted on `source_documents`,
and reused on later requests. It drives RTL-aware field geometry and is the version's
`source_language`. `und` records "could not determine" and is never silently turned into `en`.
The three language concepts stay separate: `source_language` describes the document,
`user_language` the interface, `output_language` the completed form.

---

## Frontend Architecture

The Next.js frontend is structured for localization, secure step-based workflow management, and responsive dynamic form presentation:

### 1. Route Layout & Localization
- **`LanguageProvider`**: Wrapped around the root layout, it dynamically sets the document language and direction (e.g., `dir="rtl"` and `lang="ar"` for Arabic) based on UI language choices, preserving selections in `localStorage`.
- **`next-intl`**: Handles static translation strings for headers, labels, placeholders, errors, and summaries using static translation assets (`en.json`, `de.json`, `fr.json`, `ar.json`).

### 2. Session Ownership and Security
- **`sessionCredentials` Service**: Manages `ownershipToken` mappings in `sessionStorage` isolated by browser tab.
- **Secure API Client (`apiClient.ts`)**: Appends the tab's `ownershipToken` using the `X-Session-Token` request header. It completely avoids URL token injection.

### 3. Automatic Upload-to-Questions Orchestration (Phase 13)

`app/field_detection/orchestration.py::PrepareQuestionsService` composes document analysis, OCR,
field detection, deterministic confidence routing, and question generation into one idempotent
call (`POST /api/source-documents/{id}/prepare-questions`). Normal users never drive OCR/detection/
review as separate manual steps; the frontend's `DocumentUploadForm` calls this endpoint
automatically after upload and navigates straight to the guided session. The Phase 11 manual
review screen (`FieldDetectionPanel`) is unchanged and still reachable directly for admin/debug
use — see [ADR 0012](decisions/0012-automatic-confidence-routing.md).

### 4. Workflow Routing & Dynamic Rendering
- **Guided Form Container (`/application/session/[sessionId]/page.tsx`)**: Integrates standard, clarification, and confirmation sub-flows based on backend answer state transitions.
- **`FieldRenderer` Component**: A unified entrypoint rendering appropriate input inputs for all 14 field types including:
  - Text: `string`, `person_name`, `country`, `money`
  - Numeric: `integer`, `decimal`
  - DateTime: `date`
  - Special: `email`, `phone` (with custom direction controls), `boolean` (custom Yes/No buttons), `address` (multi-line textarea)
  - Choices: `single_choice` (custom dropdown select), `multiple_choice` (checkbox list group)

