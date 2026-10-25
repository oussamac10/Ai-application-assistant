# Project TODO

## Completed Phases

Archived under `docs/progress/`:

1. Project Foundation
2. Form Definitions and Versioning
3. Temporary Anonymous Sessions
4. Mock Question and Answer Workflow
5. Local AI Integration with Ollama
6. Reusable Question Catalog and Hybrid Resolution
7. Frontend Guided Form Experience
8. PDF Template Mapping and Export
9. Form Upload and Document Analysis
10. OCR Integration
11. Dynamic Form Field Detection
12. User Accounts and Saved Applications
13. Automatic Upload-to-Questions User Flow
14. Azure Document Intelligence Provider
15. Azure Translator Integration
16. Hybrid Document Detection
17. Dynamic Coordinate-Overlay PDF Export, Document Location Preview & Voice Dictation

## Current Task

Implement Phase 18: Plain-Language "Explain This Field" Helper and Personalized Final Submission & Attachment Checklist.

## Goal

Help users completing unfamiliar bureaucratic forms understand what each field means and where to find the required information in plain, non-legal language (in their chosen `userLanguage`), and provide a personalized, interactive Submission & Supporting Document Checklist on the final completion screen (`complete/page.tsx`) based on the form's fields, signatures, and document context.

## Acceptance Criteria

- [x] Deterministic + multilingual plain-language field explanation resolver (`backend/app/answers/explanations.py`) that explains common bureaucratic concepts (housing provider confirmation / `Wohnungsgeberbestätigung`, `IBAN`/`BIC`, `Kaution`, `Grundmiete`/`Betriebskostenvorauszahlung`/`Heizkostenvorauszahlung`, `PLZ`/`Ort`, tax/registration identifiers, signatures, dates, etc.) in plain words with "What this means" and "Where to find it" guidance, strictly adhering to product boundaries (never offering legal advice or eligibility decisions)
- [x] `CurrentFieldResponse` (`backend/app/answers/schemas.py`, `backend/app/answers/services.py`) includes structured `field_explanation` metadata (`summary`, `where_to_find`, `example`) localized to `session.user_language` (with translation fallback via `TranslationProvider` when needed)
- [x] Guided Session UI (`frontend/src/app/application/session/[sessionId]/page.tsx`) includes an interactive *"Explain this field in simple words"* toggle button and collapsible callout card showing the plain-language explanation, where to find the value, and a concrete example
- [x] `SummaryResponse` (`backend/app/answers/schemas.py`, `backend/app/answers/services.py`) includes a deterministic `submission_checklist` list of actionable post-completion checklist items (e.g., printing & signing deferred signatures, obtaining landlord/second-party counter-signature when `Wohnungsgeber`/`Vermieter` fields are present, attaching identity/supporting documents when referenced, verifying IBAN/account details)
- [x] Final Completion page (`frontend/src/app/application/session/[sessionId]/complete/page.tsx`) renders the interactive **Submission & Supporting Document Checklist** so users can check off required steps and attachments before submitting their completed PDF to the authority
- [x] Unit tests for backend explanation & checklist generation and frontend tests pass with zero regressions

## Planned Steps

- [x] Create `backend/app/answers/explanations.py` with deterministic plain-language field explanations and submission checklist generation
- [x] Expose `field_explanation` on `CurrentFieldResponse` and `submission_checklist` on `SummaryResponse` in `backend/app/answers/schemas.py` and `backend/app/answers/services.py`
- [x] Update `frontend/src/features/form-session/services/apiClient.ts`, `frontend/src/app/application/session/[sessionId]/page.tsx`, and `frontend/src/app/application/session/[sessionId]/complete/page.tsx`
- [x] Add unit tests in `backend/tests/answers/test_explanations_and_checklist.py` and verify backend (`pytest`, `ruff`, `mypy`) and frontend (`vitest`, `tsc --noEmit`)

## Files Expected to Change

- `TODO.md`
- `docs/progress/phase-17-dynamic-pdf-export.md`
- `backend/app/answers/explanations.py`
- `backend/app/answers/schemas.py`
- `backend/app/answers/services.py`
- `backend/tests/answers/test_explanations_and_checklist.py`
- `frontend/src/features/form-session/services/apiClient.ts`
- `frontend/src/app/application/session/[sessionId]/page.tsx`
- `frontend/src/app/application/session/[sessionId]/complete/page.tsx`

## Decisions and Assumptions

- Plain-language explanations use a deterministic static catalog first (matching semantic field keys, label keywords, and field types in `en`, `de`, `fr`, `ar`, and fallback translation for any other `user_language`), avoiding unnecessary paid AI calls per `AGENTS.md` Section 5.5 and 6.1.
- Explanations strictly inform the user what the form field asks for and where to find the information on official letters/contracts; they never give legal advice, financial advice, or eligibility conclusions (`AGENTS.md` Section 4).

## Blockers

- None

## Verification

- [x] Backend tests pass (`pytest`)
- [x] Backend linting and type checking pass (`ruff check`, `ruff format --check`, `mypy`)
- [x] Frontend tests and type checking pass (`vitest`, `tsc --noEmit`)
