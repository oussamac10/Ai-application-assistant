# Reusable Question Catalog & Hybrid Resolution

## Overview
This document outlines the design and integration of the reusable question catalog and the hybrid resolution pipeline introduced in MVP Phase 6.

Form field definitions are kept language-independent. The user-facing label, placeholder, and helper text are resolved at runtime depending on:
1. `sourceLanguage`: Language of the original form.
2. `userLanguage`: Language used for questions and explanations.
3. `outputLanguage`: Language used in the completed form.

## Database Catalog Schema
The database models are defined in [models.py](file:///Users/oussama/Desktop/ai-application-assistant/backend/app/questions/models.py):

### `QuestionDefinition`
- `id` (UUID, PK)
- `question_key` (VARCHAR, Unique, Indexed): Semantic identifier (e.g. `personal.first_name`).
- `field_type` (VARCHAR): Expected field type matching form field types.
- `purpose` (VARCHAR): Purpose of the question (e.g. `collect_value`).
- `domain` (VARCHAR): Domain namespace (e.g. `personal`, `finance`, `address`).
- `is_active` (BOOLEAN): Soft active state flag.
- `created_at` / `updated_at` (DateTime)

### `QuestionTranslation`
- `id` (UUID, PK)
- `question_definition_id` (UUID, FK)
- `language` (VARCHAR): ISO 639-1 language code.
- `text` (TEXT): Resolved question text.
- `help_text` (TEXT, Optional)
- `placeholder` (TEXT, Optional)
- `source` (VARCHAR): Source descriptor (`manual`, `fixture`, `ai_translated`, `ai_generated`, `deterministic_fallback`).
- `review_status` (VARCHAR): Review state (`approved`, `pending_review`, `rejected`).
- `provider` / `model` / `prompt_version` (VARCHAR, Optional): AI generation lineage metadata.
- `approved_at` / `created_at` (DateTime)

## Hybrid Lookup Pipeline
Question lookup follows a provider-independent resolver (`QuestionResolver`) and proceeds through the following levels:

```
  Field Question Resolution Request
               │
               ▼
   [ Approved Target Lang in DB? ] ──(Yes)──► Return translation
               │ (No)
               ▼
   [ Pending Target Lang in DB? ]  ──(Yes)──► Return if ALLOW_PENDING_REUSE=true
               │ (No)
               ▼
   [ Static Translation in Form? ] ──(Yes)──► Return static form translation
               │ (No)
               ▼
   [ AI Translation of Source? ]   ──(Yes)──► Translate, store pending DB, return
               │ (No)
               ▼
    [ AI Generation from Meta? ]   ──(Yes)──► Generate, store pending DB, return
               │ (No)
               ▼
   [ Deterministic Non-AI Fallback] ────────► Formulate label fallback, return
```

## Seed Questions Catalog
We pre-seed 11 core reusable question definitions and translations for `en`, `de`, `fr`, and `ar` in [seed.py](file:///Users/oussama/Desktop/ai-application-assistant/backend/app/questions/seed.py):

1. `personal.first_name`
2. `personal.last_name`
3. `personal.date_of_birth`
4. `contact.email`
5. `contact.phone`
6. `address.street`
7. `address.postal_code`
8. `address.city`
9. `address.country`
10. `finance.monthly_income`
11. `civil_status.marital_status`

## Administrative Review API
Endpoints are protected under settings `QUESTION_ADMIN_API_ENABLED=true` check and return `403 Forbidden` if disabled:
- `GET /api/questions`: Search and filter resolved catalog questions.
- `POST /api/questions/{question_key}/translations`: Manually specify translation attributes.
- `POST /api/questions/{question_key}/translations/{language}/approve`: Elevate reviewStatus to `approved` to enable global reuse.
- `POST /api/questions/{question_key}/translations/{language}/reject`: Quarantine a translation to `rejected` status.
