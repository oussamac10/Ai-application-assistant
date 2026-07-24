# ADR 0005: Hybrid Question Catalog & Resolution

## Status
Approved

## Context
Many web forms share semantically identical concepts (e.g. personal first name, last name, phone number, email, date of birth) despite varying wording across forms and versions. To minimize paid LLM costs, eliminate non-deterministic question translations, and support multilingual capabilities efficiently, we need a reusable question catalog mapped to stable semantic keys. 

We also need a hybrid resolution pipeline that checks local database definitions/translations first, static form template translation second, and queries AI (translation or generation) only when local assets are absent. Furthermore, AI-generated/translated items must default to `pending_review` status and undergo manual administrative approval before being eligible for global session reuse, ensuring strict quality control.

## Decision
1. **Database Schema**: We introduced three database tables:
   - `question_definitions`: Defines the stable semantic key (e.g. `personal.first_name`), expected field type, purpose, and domain.
   - `question_translations`: Stores the localized texts (`text`, `help_text`, `placeholder`) in ISO 639-1 languages. Tracks `source` (`manual`, `fixture`, `ai_translated`, `ai_generated`, `deterministic_fallback`) and `review_status` (`approved`, `pending_review`, `rejected`).
   - `question_resolution_logs`: Audit logs tracking every lookup attempt, resolved language, AI utilization details, and the lookup result.
2. **Hybrid Resolution Pipeline**:
   The resolution logic is defined inside the stateless `QuestionResolver` class following this strict sequence:
   - **Step 1**: Find an approved reusable translation in `userLanguage` from the database.
   - **Step 2**: Find a pending reusable translation in `userLanguage` from the database if `QUESTION_ALLOW_PENDING_REUSE` is enabled.
   - **Step 3**: Fallback to static form translation labels from the immutable form version's `translations`.
   - **Step 4**: Perform AI translation of an approved `sourceLanguage` reusable question definition (if `QUESTION_AI_TRANSLATION_ENABLED` is true). Save the translated result in `pending_review` status.
   - **Step 5**: Perform AI generation using field metadata (if `QUESTION_AI_GENERATION_ENABLED` is true). Save the generated question in `pending_review` status.
   - **Step 6**: Fallback to deterministic non-AI label fallback (e.g. "Please provide a value for “First name”.").
3. **Manual Review Administrative Routes**:
   - `GET /api/questions`: Lists question definitions with optional language and review status filters.
   - `POST /api/questions/{question_key}/translations`: Manually creates or updates a translation.
   - `POST /api/questions/{question_key}/translations/{language}/approve`: Approves a pending translation.
   - `POST /api/questions/{question_key}/translations/{language}/reject`: Rejects a pending translation.
   - Access controls are enforced by verifying `QUESTION_ADMIN_API_ENABLED=true` in `settings`. If disabled, routes return `403 Forbidden`.
4. **Seed Data**:
   - Seeding 11 core semantic question definition keys and their reviewed translations in English (`en`), German (`de`), French (`fr`), and Arabic (`ar`) via `load_fixture.py`.

## Consequences
- **Zero AI Overhead for Core Fields**: Standard questions lookup is fully cached/database-first, causing zero AI latency and cost.
- **Robust Quality Control**: All AI content is quarantined in `pending_review` status and not reusable globally across sessions until reviewed.
- **Strict Decoupling**: Resolver is stateless and independent from session workflow state, ownership, or progress calculation.
- **Audit Trails**: Resolution logs allow tracking exactly how any question was resolved and monitoring AI provider utilization.
- **Test Stability**: The test suite covers all steps of the hybrid resolution pipeline using standard `MockAIProvider` mocks.
