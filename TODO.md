# Project TODO

## Completed Phases

Archived under `docs/progress/`:

1–18. Core MVP & Hybrid Multilingual Pipeline (`phase-1` through `phase-18-explanations-and-checklist.md`)
- **SaaS Phase S0**: P0 Security, RBAC, Dynamic-Form Isolation, Credential Hardening & Retention (`docs/progress/phase-s0-security-and-hardening.md`)
- **SaaS Phase S1**: Storage Provider, Smartphone Camera Scan Normalization, Multi-Script OCR + Async Jobs & Rate Limiting, Scanned Box Detection, and Embedded Unicode/RTL PDF + Watermarked Preview (`docs/progress/phase-s1-storage-camera-async-unicode.md`)
- **SaaS Phase S2**: Account Lifecycle, GDPR Art. 17/20 Self-Service Controls, Encrypted Reusable Profile Vault (1-Click Pre-Fill), and Dual-Pane Verification Studio (`docs/progress/phase-s2-accounts-gdpr-vault-studio.md`)
- **Business-Driven SaaS Partner Upgrade (Stage A & B)**: Vetted SaaS marketing/pricing/research skills, permanent `saas-business-advisor` Co-Founder skill, `10`–`10,000` user CFO unit economics & 7-doc `docs/business/` suite (`docs/progress/stage-b-saas-business-partner-upgrade.md`)
- **SaaS Phase S3 (`S3-02` & `S3-03`) + 2D Vector-Grid Field Detection & Test Consolidation**: 8 Full Static UI Languages (`en, de, fr, ar, tr, uk, es, ru`), Conversion Homepage + 1-Click Top-10 Fingerprinted German Templates, German Legal Pages (`/impressum`, `/datenschutz`, `/agb`), General 2D Vector-Grid Field Detection, and Test Suite Consolidation (`docs/progress/phase-s3-ux-i18n-legal-german-templates.md`)
- **Visual Row-Band Reading Order & Zero-Indexed First-Question Back-Button Guard**: (`docs/progress/phase-s3-row-band-sorting.md`)
- **Universal Worldwide B2B & B2G Platform Pivot**: Multi-tenant Agency/Enterprise Portal (`/portal`), dynamic candidate magic-link invitations, destination-agnostic intake (`/portal/invite/[token]`), worldwide templates (`eu-schengen-visa`, `us-immigration-intake`, `uk-visas-intake`), and complete 8-locale copy modernization (`en, de, fr, ar, tr, uk, es, ru`) with 100% test parity.
- **Phase S4: B2B/B2G Billing, Quotas, Admin Tower & Standalone Pricing**: Full Stripe Checkout & Customer Portal integration, Organization subscriptions (`agency_sandbox`, `agency_pro`, `enterprise`), token usage ledger & €0.25 circuit breaker, Founder Admin Console (`/admin` & `GET /api/admin/overview`), dedicated B2B/B2G Pricing page (`/pricing`), and dual-port (`3000` & `3003`) host connectivity.

---

## Current Task

**System Readiness & Smoke Test (`S3-01` / Worldwide End-to-End Operational Smoke Test)**

### Status
- Docker containers healthy: `frontend` (:3000 & :3003), `backend` (:8000), `postgres` (:5432), `redis` (:6379), `worker` (ARQ).
- Founder Admin Console live at `/admin` (`admin@example.com` granted platform_admin in dev).
- Agency Studio live at `/portal` with candidate magic links and quota monitors.
- Standalone Pricing page live at `/pricing`.
- All backend (Ruff, mypy, Pytest) and frontend (TypeScript, ESLint, Vitest, 8-locale parity) tests passing with 0 errors.

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
