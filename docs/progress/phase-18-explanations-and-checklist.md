# Phase 18 — Plain-Language Field Explanations & Submission Checklist

## Goal

Help users completing unfamiliar bureaucratic forms understand what each field means and where to find the required information in plain, non-legal language (in their chosen `userLanguage`), and provide a personalized, interactive Submission & Supporting Document Checklist on the final completion screen (`complete/page.tsx`).

## Summary of Delivered Changes

- **Plain-Language Civic Explanations (`backend/app/answers/explanations.py`)**: Deterministic multilingual catalog (`en`, `de`, `fr`, `ar` + `TranslationProvider` fallback) providing `summary`, `where_to_find`, and `example` without legal advice or eligibility conclusions.
- **Guided Session & Summary Integration (`backend/app/answers/schemas.py`, `backend/app/answers/services.py`)**: Exposed `field_explanation` on `CurrentFieldResponse` and `submission_checklist` on `SummaryResponse`.
- **Frontend UI (`frontend/src/app/application/session/[sessionId]/page.tsx`, `complete/page.tsx`)**: Collapsible *"Explain this field in simple words"* helper card during guided sessions and interactive **Submission & Supporting Document Checklist** on completion, plus PDF zoom alignment, `Ort, Datum, Unterschrift` 3-field splitting, and multi-signature state isolation.
