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

## Completed Tasks

- Eliminated redundant `getSummary` API calls on every question transition in the guided session flow (`backend/app/answers/schemas.py`, `backend/app/answers/services.py`, `frontend/src/app/application/session/[sessionId]/page.tsx`).
- Fixed answer confirmation and summary display formatting for money amounts (`2000.0 EUR once` -> `2000 EUR`), multiple-choice arrays, and boolean Yes/No values.

## Current Task

Conduct a comprehensive UI/UX audit, create `DESIGN.md`, establish a cohesive design token system, and upgrade all frontend components and pages to a refined, accessible, production-grade interface.

## Goal

Replace generic AI template tropes (neon purple/violet glow orbs, rainbow progress bars, excessive glassmorphism, inconsistent radii, continuous pulsing dots) with a cohesive, accessible, Linear/Vercel-inspired document-intelligence design system documented in `DESIGN.md` and implemented across `globals.css`, `tailwind.config.ts`, shared components, and all application routes while preserving 100% of existing functionality and test contracts.

## Acceptance Criteria

- [x] Project-level `DESIGN.md` created documenting colors, typography, layout, components, accessibility, RTL rules, and motion tokens
- [x] `frontend/src/app/globals.css` and `frontend/tailwind.config.ts` updated with structured design tokens (surfaces, borders, accents, typography scale, focus-visible rings, and `prefers-reduced-motion` support)
- [x] Shared components (`Navbar`, `FieldRenderer`, `SignaturePad`, `DeclarationGroup`, `DocumentUploadForm`, `ApplicationCard`, `ClaimBanner`, `LoginForm`, `RegisterForm`) refined for visual hierarchy, keyboard focus, touch targets, and RTL alignment
- [x] Core pages (`page.tsx`, `application/page.tsx`, `session/[sessionId]/page.tsx`, `session/[sessionId]/summary/page.tsx`, `session/[sessionId]/complete/page.tsx`, `applications/page.tsx`) upgraded with cohesive layout, clear step progression, and accessible contrast
- [x] All frontend unit/component tests (`vitest`), `tsc --noEmit`, and `next lint` pass without regression

## Planned Steps

- [x] Inspect repository, frontend stack, routes, components, styling, and tests
- [x] Create `DESIGN.md` with complete design system specification
- [x] Upgrade Phase 1 Foundation (`globals.css`, `tailwind.config.ts`, `layout.tsx`)
- [x] Upgrade Phase 2 Shared Components (`Navbar`, `FieldRenderer`, `SignaturePad`, `DeclarationGroup`, `DocumentUploadForm`, `ApplicationCard`, `ClaimBanner`, `LoginForm`, `RegisterForm`)
- [x] Upgrade Phase 3 & 4 Pages (`page.tsx`, `application/page.tsx`, `session/[sessionId]/page.tsx`, `summary/page.tsx`, `complete/page.tsx`, `applications/page.tsx`)
- [x] Run Phase 5 Verification (`vitest`, `tsc --noEmit`, `next lint`, and visual viewport checks)

## Files Expected to Change

- `DESIGN.md`
- `frontend/tailwind.config.ts`
- `frontend/src/app/globals.css`
- `frontend/src/app/layout.tsx`
- `frontend/src/components/Navbar.tsx`
- `frontend/src/app/page.tsx`
- `frontend/src/app/application/page.tsx`
- `frontend/src/app/application/session/[sessionId]/page.tsx`
- `frontend/src/app/application/session/[sessionId]/summary/page.tsx`
- `frontend/src/app/application/session/[sessionId]/complete/page.tsx`
- `frontend/src/app/applications/page.tsx`
- `frontend/src/app/application/document/[documentId]/detect-fields/page.tsx`
- `frontend/src/features/document-upload/components/DocumentUploadForm.tsx`
- `frontend/src/features/form-session/components/FieldRenderer.tsx`
- `frontend/src/features/form-session/components/SignaturePad.tsx`
- `frontend/src/features/form-session/components/DeclarationGroup.tsx`
- `frontend/src/features/applications/components/ApplicationCard.tsx`
- `frontend/src/features/applications/components/ClaimBanner.tsx`
- `frontend/src/features/auth/components/LoginForm.tsx`
- `frontend/src/features/auth/components/RegisterForm.tsx`
- `frontend/src/features/auth/components/AccountMenu.tsx`

## Decisions and Assumptions

- All existing `data-testid` attributes, ARIA roles/labels, translated string keys, and route contracts must remain intact so every existing unit and E2E test passes without modification.
- Design direction: "Precision Civic Studio" — deep obsidian/slate architectural surfaces (`#090b10` / `#0f131a` / `#151b24`), crisp `1px` hairline borders, authoritative indigo/blue primary action tokens (`#4f46e5` / `#6366f1`) without neon violet/cyan gradients, tabular numerals for progress/metrics, and full LTR/RTL logical property discipline.

## Blockers

- None

## Verification

- [x] Frontend tests pass (`28 passed` test files, `240 passed` tests)
- [x] Linting passes (`next lint` — 0 warnings or errors)
- [x] Type checking passes (`tsc --noEmit` — 0 errors)
- [x] Visual and responsive checks completed

## Completed

- Created `DESIGN.md` and upgraded the entire Next.js frontend to the "Precision Civic Studio" design system with zero regressions across all 240 unit and integration tests.
