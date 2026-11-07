# Project TODO — Multilingual Government Forms SaaS Platform

## Current Vision & Operating Model
Evolving AI Form Assistant into a production-ready, multi-tenant SaaS platform for government agencies, municipalities, immigration offices, universities, and public institutions.

- **Business Principle**: Organizations pay according to the **number of active published form templates** in their workspace.
- **Citizen Experience**: Citizens access and fill forms for **100% free**. No per-user, per-completion, per-link, or per-QR-code charges.
- **Sequencing**: Payments and Stripe subscriptions are **deferred** until after the core operational pillars (workspaces, schema review, public portals, QR codes, private invitations, and citizen guided intake) are fully established and running.

---

## Active Roadmap & Implementation Phases

## Current Task

**Phase G3-CAT: TYPO3-Inspired Multilingual Form Categories & Citizen Guidance Language Filtering**

### 7-Line Business Decision Summary
- **Feature:** TYPO3-Inspired Multilingual Form Categories & Taxonomy Engine with Citizen Guidance Language Filtering.
- **Customer problem:** Municipalities publish dozens of diverse administrative forms (housing, civil status, immigration, taxation, social welfare) in a flat, unorganized catalog; foreign citizens speaking 8+ languages cannot browse or locate relevant procedures without scrolling through long German titles.
- **Expected value:** Reduces form discovery time for citizens by 70%; enables structured municipal taxonomies; delivers native-language category navigation across all 8 supported languages without manual translation overhead.
- **Estimated development effort:** ~0.5–1 solo-developer build day across Alembic migration, FastAPI category CRUD & public endpoints, pre-seeded multilingual taxonomies, Review Studio / Upload category selector, and Public Portal responsive multilingual category pills.
- **Operating impact:** Negligible: pure relational PostgreSQL query + JSONB translations; zero external paid API calls or cloud overhead; 100% GDPR compliant.
- **Monetization potential:** High agency/municipal value: essential capability for municipal onboarding, government verifications, and enterprise multi-department deployments.
- **Recommendation:** `Build now` — Essential UX pillar requested directly by user, inspired by enterprise TYPO3 standard, and completely aligns with our multilingual government SaaS model.

### Goal
Empower organizations to create and manage structured, hierarchical form categories inspired by TYPO3 (`sys_category`) with full translation support across all Supported Guidance Languages for Citizens, assign forms to categories in upload & review workflows, and allow citizens to filter forms on public portals (e.g. `/organizations/first-f95b49`) with dynamic category labels matching their selected guidance language.

### Acceptance Criteria
1. Database schema migration:
   - Create `organization_categories` table (`id`, `organization_id`, `name`, `slug`, `icon`, `description`, `parent_id` self-referencing hierarchy, `translations` JSONB, `sort_order`, `is_active`, timestamps, unique `(organization_id, slug)`).
   - Add `category_id` (FK to `organization_categories.id`, `ondelete="SET NULL"`) to `form_templates`.
2. Backend API routes & service:
   - `GET /api/organizations/{org_id}/categories` (list categories with form counts).
   - `POST /api/organizations/{org_id}/categories` (create category with multilingual translations).
   - `PUT /api/organizations/{org_id}/categories/{cat_id}` (update category details & translations).
   - `DELETE /api/organizations/{org_id}/categories/{cat_id}` (delete category safely).
   - Update `GET /api/public/organizations/{slug}` to return `categories` (with form counts and translations) and populate `category_id` on each published form.
   - Support updating `category_id` on form templates via Review Studio update endpoint.
   - Pre-seed official German municipal starter categories ("Wohnen & Meldewesen", "Familie & Kinder", "Ausländerwesen & Aufenthalt", "Arbeit & Gewerbe", "Kfz & Mobilität", "Soziales & Gesundheit") with verified 8-language translations for new/existing organizations.
3. Organization Workspace Frontend:
   - "Categories & Taxonomy" management tab in Organization Settings (`/account`).
   - Category selector in `FormUploadModal.tsx` and `FormSchemaReviewStudio.tsx` (under General Details & Rules).
4. Public Citizen Portal Frontend (`/organizations/[slug]`):
   - Category filter pills/tabs above the forms catalog (e.g. `All (12)`, `Wohnen & Meldewesen (5)`, `Familie (3)`, etc.).
   - Dynamic multilingual translation of category titles based on the citizen's selected guidance language (`userLanguage`).
   - Clicking a category pill filters forms instantly and updates counts.
5. All automated tests pass (Ruff, Mypy, Pytest on `ai_form_assistant_test` DB, TypeScript, Vitest).

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
