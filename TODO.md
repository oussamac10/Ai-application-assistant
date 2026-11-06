# Project TODO — Multilingual Government Forms SaaS Platform

## Current Vision & Operating Model
Evolving AI Form Assistant into a production-ready, multi-tenant SaaS platform for government agencies, municipalities, immigration offices, universities, and public institutions.

- **Business Principle**: Organizations pay according to the **number of active published form templates** in their workspace.
- **Citizen Experience**: Citizens access and fill forms for **100% free**. No per-user, per-completion, per-link, or per-QR-code charges.
- **Sequencing**: Payments and Stripe subscriptions are **deferred** until after the core operational pillars (workspaces, schema review, public portals, QR codes, private invitations, and citizen guided intake) are fully established and running.

---

## Active Roadmap & Implementation Phases

## Current Task

**Phase G5-AI: Semantic Intelligence, Vector Search & Auto-Mapping (`pgvector` + Multilingual Embeddings)**

### 7-Line Business Decision Summary
- **Feature:** Phase G5-AI — PostgreSQL `pgvector` Semantic Intelligence Pipeline (Review Studio AI Schema Auto-Mapper, Multilingual Natural-Language Form Finder, Profile Vault 2.0 Semantic Fill, and Gemini 2.0 Flash Plain-Language Bureaucracy Explanations).
- **Customer problem:** Municipal caseworkers spend hours manually mapping OCR boxes on long PDFs to schema keys; foreign citizens cannot find forms because they don't know German bureaucratic names (*Amtsdeutsch*); complex legal terms confuse applicants.
- **Expected value:** Reduces form configuration time from 20 minutes to <2 minutes per form (90% reduction); enables citizens of all 8 languages to find official German forms using everyday native phrasing; eliminates field confusion with instant plain-language explanations.
- **Estimated development effort:** ~2 solo-developer build days across PostgreSQL `pgvector` migration, `EmbeddingService` (Google `text-embedding-004` & local `bge-m3`), Review Studio auto-mapping endpoint, and multilingual form search.
- **Operating impact:** Embeddings run in PostgreSQL with HNSW cosine index (`<=>`) in `<10ms` at negligible cost (~€0.000016 per 50-field form); zero external vector SaaS dependencies (Pinecone/Milvus); 100% GDPR compliant and on-premise capable.
- **Monetization potential:** Core enterprise/agency differentiator: turns the Review Studio into a magical 1-click publishing workflow and drives citizen adoption across multilingual communities.
- **Recommendation:** `Build now` — Extremely high user experience value, zero ongoing infrastructure overhead, and perfect synergy with PostgreSQL 16.

### Goal
Equip the platform with native PostgreSQL vector search (`pgvector`) to power 4 breakthrough capabilities: (1) instant AI schema auto-mapping in Review Studio, (2) cross-lingual form discovery in citizen native languages, (3) semantic Profile Vault pre-filling, and (4) Gemini 2.0 Flash plain-language field explanations.

### Acceptance Criteria
1. PostgreSQL 16 `pgvector` extension enabled via Alembic migration, creating `embedding_vectors` table with `vector(768)` / `vector(1024)` and HNSW cosine index (`<=>`).
2. `EmbeddingService` implemented with clean provider abstraction: Google `text-embedding-004` (cloud standard) and local `fastembed` (`BAAI/bge-m3`, sovereign on-premise).
3. Backend provides `POST /api/organizations/{org_id}/forms/{form_id}/auto-map` returning high-confidence canonical key predictions and top-3 suggestions for detected OCR bounding boxes in `<2s`.
4. Review Studio UI displays 1-click "Auto-Map Fields" action with visual confidence tags and dropdown review.
5. Multilingual Natural-Language Form Finder endpoint `GET /api/public/forms/search?q=...&lang=...` retrieves relevant German administrative templates from native queries (Arabic, Turkish, Ukrainian, etc.).
6. Gemini 2.0 Flash explanation endpoint generates 2-sentence plain-language definitions and document readiness checklists for complicated bureaucratic terms.
7. Automated tests pass with zero live paid AI calls using mock embedding and test fixtures on `ai_form_assistant_test` DB.

### Planned Steps
- [ ] 1. Create Alembic migration enabling `pgvector` and defining `embedding_vectors` table with HNSW index and tenant isolation.
- [ ] 2. Implement `backend/app/ai/embedding_service.py` with `EmbeddingProvider` protocol, `GoogleEmbeddingProvider`, and `FastEmbedProvider`.
- [ ] 3. Seed canonical field dictionary embeddings (250+ administrative keys across personal, address, employment, family, and landlord domains).
- [ ] 4. Implement Review Studio auto-mapper service and endpoint `POST /api/organizations/{org_id}/forms/{form_id}/auto-map`.
- [ ] 5. Implement multilingual form vector search in `backend/app/forms/public_service.py`.
- [ ] 6. Implement Gemini 2.0 Flash plain-language field explanation helper with prompt isolation and document checklist generation.
- [ ] 7. Integrate "Auto-Map Fields" button and confidence badges into `FormSchemaReviewStudio.tsx`.
- [ ] 8. Write comprehensive backend tests for vector search, schema auto-mapping, and tenant isolation targeting `ai_form_assistant_test` DB.
- [ ] 9. Write frontend tests for auto-mapper interactions in Review Studio.
- [ ] 10. Run full verification gate: Ruff, Mypy, Pytest on test DB, TypeScript, ESLint, Vitest.

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
