# Project TODO — Multilingual Government Forms SaaS Platform

## Current Vision & Operating Model
Evolving AI Form Assistant into a production-ready, multi-tenant SaaS platform for government agencies, municipalities, immigration offices, universities, and public institutions.

- **Business Principle**: Organizations pay according to the **number of active published form templates** in their workspace.
- **Citizen Experience**: Citizens access and fill forms for **100% free**. No per-user, per-completion, per-link, or per-QR-code charges.
- **Sequencing**: Payments and Stripe subscriptions are **deferred** until after the core operational pillars (workspaces, schema review, public portals, QR codes, private invitations, and citizen guided intake) are fully established and running.

---

## Active Roadmap & Implementation Phases

## Current Task

**Phase G5-AI: Semantic Intelligence, Vector Search & Auto-Mapping (Completed)**

### 7-Line Business Decision Summary
- **Feature:** Semantic embeddings pipeline (`EmbeddingProvider`, `GeminiEmbeddingProvider`, `MockEmbeddingProvider`), canonical schema auto-mapper, and cross-lingual form discovery on public authority portals.
- **Customer problem:** Form administrators manually map dozens of detected fields to canonical Profile Vault keys; citizens cannot find German municipal forms when querying in their native language (e.g. searching "moving apartment" fails to find "Wohnungsgeberbestätigung").
- **Expected value:** Reduces form setup time by ~85% with 1-click auto-mapping; enables 100% multilingual discovery for foreign-born citizens across all 8 guidance languages.
- **Estimated development effort:** ~1 solo-developer day across embedding protocols, vector cosine similarity math, auto-mapper service, semantic search endpoints, and frontend integration.
- **Operating impact:** Minimal embedding API cost (`text-embedding-004` caching); €0 automated test cost via deterministic mock embeddings.
- **Monetization potential:** Core enterprise differentiator for public sector procurement and higher tier plan value.
- **Recommendation:** `Build now` — Requested by user and completed with full verification gate.

### Acceptance Criteria
- [x] 1. `EmbeddingProvider` protocol with deterministic `MockEmbeddingProvider` (for €0 test cost) and `GeminiEmbeddingProvider` (`text-embedding-004` using `x-goog-api-key`).
- [x] 2. Canonical key semantic catalog (`CANONICAL_SCHEMA_CATALOG`) with rich German/English definitions and synonyms for vault pre-fill mapping.
- [x] 3. `SchemaAutoMapperService` with cosine similarity + lexical matching + type compatibility to automatically map detected form fields to canonical Profile Vault keys in `<2s`.
- [x] 4. Backend endpoints in `organizations/api/routes.py`:
  - `POST /api/organizations/current/forms/{template_id}/auto-map`
  - `POST /api/organizations/current/forms/{template_id}/auto-map/apply`
  - `GET /api/public/organizations/{slug}/forms/semantic-search`
- [x] 5. `MultilingualSemanticSearchService` enabling citizens to query in any of the 8 languages and discover relevant German municipal forms via cross-lingual semantic matching.
- [x] 6. Frontend Review Studio: 1-click "✨ Auto-Map Schema" button and suggestion badges on field cards with confidence ratings and 1-click apply.
- [x] 7. Frontend Public Citizen Portal: Semantic search bar with cross-lingual results, match badges, and explanation cards.
- [x] 8. Full quality gate pass: Ruff, Mypy, Pytest on isolated DB `ai_form_assistant_test` (1,092 passed), Frontend typecheck/lint/test (300 passed), and `graphify update .`.

---

## Active Roadmap & Implementation Phases

### Planned Steps
- [x] 1. Create Alembic migration for `organization_categories` table and `form_templates.category_id` foreign key.
- [x] 2. Update SQLAlchemy models in `backend/app/organizations/models.py` and `backend/app/forms/models.py`.
- [x] 3. Implement category schemas, repository, service methods, and starter categories seeder with translations in 8 guidance languages (`de`, `en`, `ar`, `fr`, `tr`, `uk`, `es`, `ru`).
- [x] 4. Add FastAPI router endpoints for organization category CRUD and update public organization response in `PublicFormService` / `OrganizationService`.
- [x] 5. Update form review update payload to support `category_id`.
- [x] 6. Update frontend types and API client functions in `frontend/src/features/portal/`.
- [x] 7. Update `FormUploadModal.tsx` and `FormSchemaReviewStudio.tsx` to let users choose a category.
- [x] 8. Implement "Categories & Taxonomy" tab in `OrganizationSettings.tsx`.
- [x] 9. Implement multilingual category filter pills in `PublicOrganizationPortal.tsx` with instant language translation.
- [x] 10. Write backend and frontend tests verifying category creation, assignment, public portal filtering, and multilingual display.
- [x] 11. Run full verification gate: Ruff, Mypy, Pytest on test DB, TypeScript, ESLint, Vitest.
- [x] 12. Add direct form-category relation endpoints (`PATCH /forms/{id}/category`, `POST /categories/{id}/forms`, `POST /forms/auto-categorize`).
- [x] 13. Add interactive category badges and quick assignment dropdown menus directly on Official Administrative Form cards in `PortalDashboard.tsx`.
- [x] 14. Add category filter tabs and 1-click "Auto-Categorize Official Forms" button in `PortalDashboard.tsx`.
- [x] 15. Add TYPO3-style assigned form relation management modal inside `OrganizationCategoryManager.tsx`.
- [x] 16. Verify with backend pytest on isolated test DB and Vitest suites (288/288 frontend tests passing).
- [x] 17. Removed "Load Default German Categories" button, auto-seeding logic, and hardcoded starter categories backend module; organizations now maintain custom taxonomy independently.
- [x] 18. Removed "TYPO3 MODEL" pill badge and references from categories management UI.
- [x] 19. Linked category translations to organization's supported languages with on-demand language selection.
- [x] 20. Fixed sidebar layout width overflow and viewport overlap bug in `Sidebar.tsx` and `FormSchemaReviewStudio.tsx`.
- [x] 21. Localized boolean buttons in `FieldRenderer.tsx` (`نعم`/`لا` for Arabic, `Ja`/`Nein` for German, etc.) and persisted field translations in `FormSchemaReviewStudio.tsx`.
- [x] 22. Created reusable `ModernSelect` component (`frontend/src/components/ui/ModernSelect.tsx`) with Lucide icons, status badges, sublabels, search filtering, checkmark indicators, outside-click handling, and full keyboard navigation.
- [x] 23. Replaced native browser `<select>` elements in `OrganizationCategoryManager.tsx` (Icon selector, Parent Category hierarchy selector, and Choose Language to Translate picker) with polished `<ModernSelect>` components.
- [x] 24. Added unit test suite in `ModernSelect.test.tsx` and verified all portal test suites pass (34/34 tests green).
- [x] 25. Enhanced PDF field extraction in `backend/app/forms/organization_service.py` to extract authentic German labels from `/TU` alternate name/tooltip or adjacent printed text instead of developer variable names (`chkEinzug` -> `Einzugsbestätigung des Wohnungsgebers nach § 19 Bundesmeldegesetz (BMG)`), skip pushbuttons (`BTDrucken`, `Zurücksetzen`), and detect true `boolean` types.
- [x] 26. Added Citizen Guidance Translations drawer and 1-click Auto-Translate capability to `FormSchemaReviewStudio.tsx` backed by `POST /api/organizations/current/forms/translate-field`.
- [x] 27. Replaced all native `<select>` dropdowns across `FormSchemaReviewStudio.tsx`, `FormUploadModal.tsx`, `NewCaseModal.tsx`, and `PublicOrganizationPortal.tsx` with `<ModernSelect>` (supporting `size="sm"` and search).
- [x] 28. Fixed sidebar layout hierarchy in `Sidebar.tsx` and `FormSchemaReviewStudio.tsx` (`flex flex-col flex-1 overflow-hidden`, `shrink-0` on headers, `h-full` without sticky bugs) preventing header clipping and horizontal overflow.
- [x] 29. Re-extracted fields on live dev DB form `wohnungsgeberbestaetigung-3a5959e5` and verified with full quality gate: Ruff, Mypy, Pytest on test DB (24 passed), TypeScript, ESLint, Vitest (41 test files, 298 passed).
- [x] 30. Added `graphify` automated codebase knowledge graph skill (`.agents/skills/graphify/SKILL.md`) and registered it in `.agents/AGENTS.md` for automatic dependency mapping, cross-layer blast-radius tracing, and zero-regression refactoring.

---

### Phase G2: Form Upload, Parsing & Human Schema Review Workflow (Completed)
- [x] Publishing workflow state machine: `Draft -> Processing -> Needs Review -> Ready -> Published -> Archived`.
- [x] Universal form ingestion: PDF AcroForms + layout coordinate extraction + universal English canonical field key mapping.
- [x] Visual Schema Review Studio: dual-pane UI where staff review, rename, reorder, and correct fields before publishing.
- [x] 100% accurate PDF layout extraction (no phantom fields; exact text prompt + vector box detection).
- [x] Visual PDF page canvas with numbered highlight bounding boxes, zoom controls, and click-to-focus synchronization.
- [x] Permanent canvas interactivity: direct click-and-drag drawing of new fields, drag-to-move existing fields, and 6-point corner/edge resize handles with live auto-save.
- [x] Universal form metadata management: neutral international English placeholders, empty default evidence checklist, and clean field creation with key auto-deduplication.

### Phase G3: Public Organization Portals & Citizen Discovery Directory (Completed)
- [x] Public Organization Portals at `/organizations/[slug]` (e.g. `/organizations/stadt-stuttgart`).
- [x] Branded portal UI: verified government badge, logo, description, office contact, and searchable form catalog.
- [x] Citizen municipality search directory at `/organizations` and linked in navigation.
- [x] SEO-optimized server-rendered public pages.

### Phase G4: Public Form Links & Printable Counter QR Codes (Completed)
- [x] Short URL resolver (`/f/[slug]`) mapping to the active published form version.
- [x] High-resolution SVG and PNG QR code generation with organization branding.
- [x] Printable A4 counter poster generator ("Scan to fill out in your native language" for municipal counters).
- [x] Share modal with 1-click link copying, compact download buttons, and embed snippets.
- [x] Portal UI Refinement: Clean, compact button labels across all 8 languages (`Review`, `Share`, `Upload PDF`, `New Intake`), sentence-case metric strips, and clutter-free card footers.

### Phase G5-AI: Semantic Intelligence, Vector Search & Auto-Mapping (pgvector + Multilingual Embeddings)
- [ ] PostgreSQL 16 `pgvector` migration with HNSW cosine index (`<=>`) and tenant-isolated `embedding_vectors` table.
- [ ] `EmbeddingService` interface supporting Google `text-embedding-004` (cloud standard) and local `fastembed` (`bge-m3`, sovereign on-premise).
- [ ] Review Studio AI Schema Auto-Mapper: automatically maps detected OCR bounding box labels to canonical keys in `<2s` with confidence ratings and top-3 suggestions.
- [ ] Multilingual Natural-Language Form Finder: cross-lingual semantic discovery over German forms from citizen native phrasing (Arabic, Turkish, Ukrainian, etc.).
- [ ] Profile Vault 2.0 Semantic Auto-Fill: high-confidence cross-form attribute matching across varied key naming schemes.
- [ ] Grounded Gemini 2.0 Flash / 1.5 Flash plain-language bureaucracy explanations (*Amtsdeutsch*) and document readiness checklists.

### Phase G5: Private & Invitation-Only Intake with Email Verification
- [ ] Private invitation engine with cryptographically secure tokens and expiration timestamps.
- [ ] Recipient email verification gate (magic link or one-time 6-digit code) before unlocking questions.
- [ ] Invitation management dashboard for case managers: revocation, resend, and audit trail.

### Phase G6: Multilingual Citizen Guided Intake & Official PDF Export
- [x] 3-language model (`sourceLanguage`, `userLanguage`, `outputLanguage`) and 8 UI languages (`en, de, fr, ar, tr, uk, es, ru`).
- [x] AcroForm widget auto-filling and PyMuPDF coordinate overlays with Unicode & Arabic font shaping.
- [ ] Form-specific submission instructions (Download & print, email, or physical delivery).
- [ ] Required documents checklist presentation prior to starting the form.

### Phase G7: Organization Analytics Dashboard & AI Cost Firewall
- [ ] Aggregated zero-PII metrics: form opens, QR scans, completions, average duration, popular languages.
- [ ] Tenant-level AI spend monitor and hard per-session circuit breaker.
- [ ] Organization analytics tab in the portal.

### Phase G8: Document-Based SaaS Subscriptions (Stripe Integration - Deferred)
- [ ] Stripe Checkout and Customer Portal configured for active published form slots (e.g. 5, 25, 100 forms).
- [ ] Slot enforcement: publishing a new form checks against active plan limits; drafts and archived forms do not count.
- [ ] Billing history and invoice management.

### Phase G9: Platform Super Admin, Audit Trails & Pilot Launch
- [x] Founder Admin Console (`/admin` and `GET /api/admin/overview`).
- [ ] Organization verification review queue for platform administrators.
- [ ] Comprehensive audit logs for municipal compliance.

### 7-Line Business Decision Summary
- **Feature:** Phase S4 — B2B & B2G Subscription Billing, Case Quotas & Token Cost Firewall.
- **Customer problem:** Relocation agencies, international HR teams, and municipal authorities need predictable monthly seat/case quotas with centralized corporate invoicing (Stripe Checkout & Customer Portal), while the platform requires a hard API cost guardrail per case (`<= €0.25/case`) to maintain `> 85%` gross margins.
- **Expected value:** Unlocks automated self-serve MRR (`€149/mo` Agency Pro, `€499/mo` Enterprise), automates case quota enforcement, and protects against runaway LLM/Azure API costs from rogue/heavy candidate usage.
- **Estimated development effort:** ~2 solo-developer build days across backend quota schemas, Stripe webhooks, token ledger, and frontend checkout buttons in the `/portal`.
- **Operating impact:** Establishes a hard `€0.25` variable cost circuit breaker per case, protecting gross margins `> 88%` on `€149/mo` (50 cases = max `€12.50` API COGS) and `> 90%` on `€499/mo` (200 cases = max `€50.00` API COGS).
- **Monetization potential:** Converts trial agency accounts into recurring `€149`–`€499`/mo B2B subscriptions via standard Stripe Checkout & Customer Portal.
- **Recommendation:** `Build now` — Core billing infrastructure is the essential commercial foundation for B2B and B2G monetization.

## Goal

Provide full-stack B2B and B2G monetization: allow organizations to subscribe to Agency Pro (`€149/mo` / 50 cases) or Enterprise (`€499/mo` / 200 cases), enforce case creation limits, manage billing via Stripe Customer Portal, and cap AI token/API costs per case with a strict `€0.25` circuit breaker.

## Acceptance Criteria

- [x] **Billing Data Models & Alembic Migration**: Add `organization_subscriptions` and `ai_usage_events` tables with proper foreign keys and indexes.
- [x] **Token & Cost Firewall**: Create `app/ai/guardrails.py` tracking token spend per case/session, enforcing hard `€0.25/case` circuit breaker.
- [x] **Case Quota Enforcement**: In `OrganizationService.create_case()`, enforce monthly limits based on active subscription (`sandbox: 3`, `pro: 50`, `enterprise: 200`), returning `402 Payment Required` with upgrade prompt when exceeded.
- [x] **Stripe Checkout & Portal Endpoints**:
  - `POST /api/billing/create-checkout-session`: Generates Stripe Checkout URL for selected B2B plan.
  - `POST /api/billing/create-portal-session`: Generates Stripe Customer Portal URL.
  - `POST /api/billing/webhook`: Processes `checkout.session.completed`, `customer.subscription.updated/deleted` idempotently.
- [x] **Agency Portal UI Integration**: Display active plan, case quota progress bar, and "Upgrade Plan" / "Manage Subscription" controls in `frontend/src/features/portal/components/PortalDashboard.tsx`.
- [x] **Verification**: Backend tests in `backend/tests/billing/` and frontend tests pass cleanly with zero live Stripe/AI calls.

## Planned Steps

- [x] 1. Create `backend/app/billing/models.py` (`OrganizationSubscription`, `AIUsageEvent`), schemas, and Alembic migration.
- [x] 2. Implement `backend/app/ai/guardrails.py` for token/cost tracking and `€0.25` session limit.
- [x] 3. Implement `backend/app/billing/services.py` with Stripe API abstractions, webhook handler, and quota logic.
- [x] 4. Connect case creation in `OrganizationService` to check active subscription quota.
- [x] 5. Implement `/api/billing/` endpoints and register in FastAPI `main.py`.
- [x] 6. Update `PortalDashboard.tsx` with subscription banner and upgrade flow.
- [x] 7. Add automated backend and frontend tests and run full verification gates.

## Files Expected to Change

- `TODO.md`
- `backend/app/billing/`
- `backend/app/ai/guardrails.py`
- `backend/app/organizations/services.py`
- `backend/app/main.py`
- `backend/migrations/`
- `backend/tests/billing/`
- `frontend/src/features/portal/`
- `backend/app/organizations/api/candidate_routes.py`
- `backend/app/main.py`
- `backend/migrations/versions/e5f6a7b8c9d0_add_organizations_and_cases.py`
- `backend/tests/organizations/test_organizations_and_cases.py`
- `frontend/src/app/portal/page.tsx`
- `frontend/src/app/portal/invite/[token]/page.tsx`
- `frontend/src/features/portal/components/*`
- `frontend/messages/en.json`
- `frontend/messages/de.json`
- `frontend/src/components/layout/Header.tsx`

## Decisions and Assumptions

- **7-Line Business Decision Summary**:
  - Feature: B2B/B2G Case Management Portal & Candidate Intake Engine.
  - Customer problem: Relocation agencies & authorities manage cases via PDFs and email; candidates make repetitive mistakes.
  - Expected value: Cuts processing time by 80%, boosts retention, unlocks €149–€499/mo SaaS contracts.
  - Estimated development effort: 1.5 days; solo-maintainable modular monolith.
  - Operating impact: 0 added AI costs; €0 COGS on official templates.
  - Monetization potential: Direct B2B/B2G subscription revenue.
  - Recommendation: Build now.
- B2B case managers must be authenticated (`User` with role `case_manager`, `admin`, or `owner`).
- Candidates access their assigned form session via single-use cryptographic magic tokens without having to create an account first.
- Reuses the existing `FormSession`, `GuidedSession`, `DualPaneVerificationStudio`, and PDF export engine seamlessly.

## Verification

- Backend tests on `ai_form_assistant_test` database pass:
  - `tests/organizations/test_organizations_and_cases.py` (6 passed)
  - `tests/auth/`, `tests/vault/`, `tests/applications/` (32 passed)
  - `tests/field_detection/test_azure_tables_and_marks.py` (3 passed)
- Backend code hygiene:
  - `ruff check .` -> clean (209 source files)
  - `ruff format --check .` -> clean (297 files formatted)
  - `mypy app` -> clean (Success: no issues found in 209 source files)
- Frontend code hygiene & test suite:
  - `npm run typecheck` -> clean (`tsc --noEmit` 0 errors)
  - `npm run lint` -> clean (`next lint` 0 errors)
  - `npx vitest run` -> 31 test files, 257 tests passed (including `portal.test.tsx` and `eight-locales-parity.test.tsx`)
- Certified German Residence Permit Template:
  - `fixtures/pdf/de-aufenthaltstitel-v1.pdf`, `.mapping.json`, `.fingerprint.json` generated and seeded.
