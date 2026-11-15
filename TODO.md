# Project TODO — AI Form Assistant (B2B Relocation & Expat Intake SaaS)

## Current Vision & Operating Model
Production-ready, multilingual SaaS platform for **B2B relocation agencies, international HR teams, and immigration consultants** (with public-sector / municipal readiness as an enterprise tier).

- **Primary Buyer & Pricing Model** (implemented in `backend/app/billing/services.py`):
  - **Agency Sandbox (`agency_sandbox`)**: Free — `3` active candidate cases/month, watermarked PDF preview.
  - **Agency Pro (`agency_pro`)**: `€149/mo` — `50` active candidate cases/month, full invite links, unwatermarked official PDFs, Profile Vault, Dual-Pane Verification Studio.
  - **Enterprise & Public Sector (`enterprise`)**: `€499/mo` — `200` active candidate cases/month, custom form digitization SLA, DPA/GDPR, on-premise option.
- **Citizen / Candidate Experience**: Candidates access assigned forms via magic invite links for **100% free**, in 8 UI languages (`de`, `en`, `ar`, `fr`, `tr`, `uk`, `es`, `ru`) including full RTL support.
- **Unit Economics Guardrail**: Hard `€0.25/case` AI cost circuit breaker (`backend/app/ai/guardrails.py`) protecting `>85%` gross margins.

---

## Completed Foundation (Verified Green)

- **Core Engine (Phases 1–18)** & **SaaS Hardening (`S0`–`S3`)**:
  - 3-language model (`sourceLanguage`, `userLanguage`, `outputLanguage`), deterministic validators (incl. MOD-97 IBAN), 6-tier `QuestionResolver`, hybrid OCR/layout field detection, AcroForm + PyMuPDF Unicode/RTL PDF export, Fernet-encrypted Profile Vault, GDPR Art. 17/20 export & erasure, Dual-Pane Verification Studio.
- **Multi-Tenant Organizations & Public Portals (`G1`–`G4`)**:
  - Organization workspaces, RBAC, Visual Schema Review Studio, Category Taxonomy, Public Organization Portals (`/organizations/[slug]`), `/f/[slug]` short links, SVG/PNG QR codes, printable A4 counter posters.
- **Semantic Intelligence & Auto-Mapping (`G5-AI` Core)**:
  - `EmbeddingProvider` (`MockEmbeddingProvider`, `GeminiEmbeddingProvider`), `SchemaAutoMapperService`, and `MultilingualSemanticSearchService` (`auto-map`, `auto-map/apply`, `semantic-search` in `backend/app/organizations/api/routes.py`).
- **B2B Subscription Billing & AI Cost Firewall (`S4`)**:
  - `OrganizationSubscription` & `AIUsageEvent` models, `€0.25/case` circuit breaker (`app/ai/guardrails.py`), Stripe Checkout / Customer Portal / Webhook endpoints (`/api/billing/*`), case quota enforcement (`402 Payment Required`), and `/pricing` + `PortalDashboard.tsx` upgrade UI.
- **Quality Gates (Verified)**:
  - **Dual-Theme System (Aikido Obsidian Dark + Daylight Light Mode)**: Added flash-free `ThemeProvider` (`formflow-theme`), `ThemeToggle` (`Sun`/`Moon` icon & segmented pill in `Navbar`, `Sidebar`, and `AppShell` mobile bar), `html.light` WCAG 2.2 AA CSS variable + `[data-theme-locked="dark"]` surface/contrast engine, and 8-locale `nav.*` translation parity (`ThemeProvider.test.tsx` 4 tests passing).
  - **Aikido-Inspired Obsidian & Emerald Frontend Overhaul**: Unified dark obsidian (`#0A0E17` / `#0F1522`) & emerald (`#10B981`) design system with `prefers-reduced-motion`-safe scan/reveal animations, rebuilt obsidian error/loading/not-found boundaries, and international worldwide copy/defaults across all portals, modals, auth/account, and guided session pages.
  - **Plain-Language UI Overhaul**: Removed version badges, internal keys/slugs, raw coordinates, and developer jargon across all routes/components with 100% key + `{placeholder}` parity across all 8 locale files.
  - **Table-Per-Row Validation Fix, Choice-in-Row Grouping & Zero-PII Continual Schema Learning**: Fixed row validation errors (`fieldId`, multilingual countries/choices/numbers/dates), added atomic `table-rows/submit` & `table-rows/skip`, per-row PDF table & intra-row checkbox extraction with `option_boxes` export, Review Studio multi-select grouping & row sync, and Zero-PII `learned_form_patterns` (migration `i0d1e2f3a4b5`; verified: `1111 passed, 1 skipped`, `318 passed`).
  - **System-Panel Scoped Brand Color Engine, WCAG Contrast & Studio Modal Polish**: Runtime `--brand-*` CSS variables & Tailwind `emerald-*` token bindings scoped strictly to `[data-system-panel="true"]` (`AppShell.tsx`, `theme.ts`, `tailwind.config.ts`, `globals.css`, `layout.tsx`, `OrganizationContext.tsx`, `OrganizationSettings.tsx`, `Sidebar.tsx`, workspace views) with warm amber-gold Light Mode darkening (`targetH = 35`), studio redesign of `InviteSuccessModal.tsx` (summary rows, integrated invite bar, Send by Email & Open Preview actions), accessible dialog & sentence-case harmonization across `NewCaseModal.tsx`, `ShareFormModal.tsx`, and `FormUploadModal.tsx`, plus a **View Link** action in `PortalDashboard.tsx` (`brandThemeEngine.test.tsx`: `3 passed`, `inviteSuccessModal.test.tsx`: `5 passed`, `vitest run`: `49 files, 326 tests passed`, `next build`, Playwright `2 passed`).
  - Single Alembic head (`i0d1e2f3a4b5`), `ruff check/format`, `mypy app` (241 files), `pytest` on `ai_form_assistant_test`, `tsc --noEmit`, `next lint`, `vitest run`, `next build`, Playwright E2E `user-accounts-persistent-sessions-flow.spec.ts` (2 passed).

---

## Current Task: Portal Modals Studio Redesign & Light-Mode Gold Contrast Polish

- **Goal**:
  - Eliminate modal text collisions, olive-khaki gold darkening, and awkward link actions while harmonizing keyboard/backdrop accessibility and sentence-case labels across portal modals.
- **Acceptance Criteria**:
  - Sovereign Gold (`#FEDB00`) darkens to warm burnished amber-gold (`targetH = 35`, `targetS >= 0.9`) while Light Mode modal backdrops use crisp charcoal glass (`rgba(15, 23, 42, 0.42)`).
  - `InviteSuccessModal.tsx` displays separated `Applicant` and high-contrast neutral `Assigned form` summary rows, a unified `Personal invite link` bar with `Copy` action, security verification note, `Send by Email` (`mailto:`), `Open Preview` (`target="_blank"`), and `Escape` / backdrop / `X` / `Done` dismissal.
  - `NewCaseModal.tsx`, `ShareFormModal.tsx`, and `FormUploadModal.tsx` enforce `Escape` dismissal, accessible `role="dialog"`, sentence-case labels, clean wrapping (`break-words`), and `PortalDashboard.tsx` exposes a direct `View Link` button for active cases.
  - Full frontend verification gate (`typecheck`, `lint`, `vitest`, `next build`, Playwright E2E) passes on `feature/dynamic-authority-brand-theming`.
- **Planned Steps**:
  - [x] Refine Light Mode yellow/gold darkening hue (`targetH = 35`, `targetS = Math.max(s, 0.9)`) in `theme.ts` and modal backdrop (`rgba(15, 23, 42, 0.42)`) in `globals.css`.
  - [x] Rebuild `InviteSuccessModal.tsx` with horizontal studio header, 2-row summary card, unified invite link input/copy bar, security helper text, and Email / Preview / Done actions.
  - [x] Harmonize `NewCaseModal.tsx`, `ShareFormModal.tsx`, and `FormUploadModal.tsx`, and add **"View Link"** (`view-link-case-*`) alongside Resend / Revoke in `PortalDashboard.tsx`.
  - [x] Add `inviteSuccessModal.test.tsx` (`5 passed`) and pass `typecheck`, `lint`, `vitest`, `next build`, Playwright E2E, and `graphify update .`.
- **Files Changed**:
  - `frontend/src/features/portal/utils/theme.ts`, `frontend/src/app/globals.css`
  - `frontend/src/features/portal/components/{InviteSuccessModal,NewCaseModal,ShareFormModal,FormUploadModal,PortalDashboard}.tsx`
  - `frontend/src/features/portal/tests/inviteSuccessModal.test.tsx`, `TODO.md`
- **Decisions and Assumptions**:
  - Preserved all existing `next-intl` `"portal"` keys (`inviteModalTitle`, `inviteModalSub`, `copyInvite`, `copied`, `done`) and footer `"Close"` button selector in `ShareFormModal.tsx` so existing tests remain intact.
- **Blockers**: None.
- **Verification**:
  - `cd frontend && npm run typecheck` (`tsc --noEmit` passed)
  - `cd frontend && npm run lint` (`next lint` — no ESLint warnings or errors)
  - `cd frontend && CI=1 npx vitest run` (`49 test files passed (49)`, `326 tests passed (326)`, including `inviteSuccessModal.test.tsx` 5 passed & `brandThemeEngine.test.tsx` 3 passed)
  - `cd frontend && npm run build` (`next build` compiled successfully, 18/18 static pages)
  - `cd frontend && npx playwright test e2e/user-accounts-persistent-sessions-flow.spec.ts` (`2 passed (14.3s)`)

---

## Upcoming Roadmap: Sell-First SaaS

### Step 1 — Go-Live & Trial Time-to-Value (Completed)
- [x] **1.1 Unify Plan Limits**: Align `agency_pro` / `enterprise` limits between `backend/app/billing/services.py` (monthly cases & template slots) and `backend/app/forms/organization_service.py` via `get_published_template_limit`.
- [x] **1.2 `<60s` Trial Onboarding**: Added `backend/app/forms/starter_templates.py` + `POST /api/organizations/current/forms/starter-templates` + 1-click **"Load 3 German Starter Templates"** empty-state action in `PortalDashboard.tsx` (*Anmeldung*, *Wohnungsgeberbestätigung*, *Aufenthaltstitel*).
- [x] **1.3 Playwright E2E Verification**: Updated `frontend/e2e/user-accounts-persistent-sessions-flow.spec.ts` to match current UI (`2 passed` in `11.9s`).

### Step 2 — Agency Sales Essentials (Completed)
- **Goal**: Harden private candidate invite links with 6-digit email OTP verification, case-manager revoke/resend/audit controls, pre-form document checklists & post-export submission instructions, and white-label agency branding on `/portal/invite/[token]`.
- **Completed & Verified**:
  - [x] **2.1 Private Invite Email / OTP Verification (`G5`)**: Require 6-digit email OTP verification (`POST /api/cases/invite/{token}/send-otp` & `/verify-otp`, 10-min TTL, 5-attempt lockout, single-use replay protection) before unlocking private forms, plus case-manager `/revoke-invite` and `/resend-invite` endpoints, **Candidate Intakes & Invites** UI controls in `PortalDashboard.tsx`, `NewCaseModal.tsx` org/catalog form merging, and zero-PII audit timestamps & logs (`alembic` `h9c0d1e2f3a4`).
  - [x] **2.2 Pre-Form Document Checklist & Submission Instructions (`G6`)**: Populated `required_documents`, `submission_method`, and `instructions` on starter/German templates and `SessionResponse`, added collapsible pre-form checklist banner in `GuidedSession`, and rendered **Official Submission Instructions** + frictionless export (bypassing `ExportAccountGateModal` for `isSponsoredCase`) on `SessionComplete`.
  - [x] **2.3 White-Label Invite Experience**: Rendered agency logo (`/api/organizations/{id}/logo`), brand name, verified authority badge, theme accent, coordinator contact footer with RTL `<bdi>` isolation, pre-form document checklist, and fixed `setSessionToken` session storage on `CandidateIntakeLanding.tsx`.
- **Verification**: `ruff check .`, `ruff format --check .`, `mypy app` (237 files), isolated `pytest` (`ai_form_assistant_test`: `1,106 passed, 1 skipped`), `npm run typecheck`, `npm run lint`, `vitest run` (`45 files, 314 passed`), `npm run build`, Playwright E2E `user-accounts-persistent-sessions-flow.spec.ts` (`2 passed`), `graphify update .`.

### Step 3 — EU Production Deployment & First 5 Paying Agencies
- [ ] **3.1 Production Hardening**: Non-root multi-stage Dockerfiles, EU hosting, automated encrypted Postgres backups, Sentry EU alerting, and paid EU Gemini/Vertex routing.
- [ ] **3.2 Founder Validation (`S3-01`)**: 30–50 targeted outreach demos to German relocation agencies & expat HR teams; convert first 5 paying `Agency Pro` (`€149/mo`) customers.

### Step 4 — Post-Revenue Expansion (Build Only From Paying Customer Demand)
- [ ] **4.1 Multi-Form Client Packets**: Group 3–5 forms into one client link where shared fields (name, passport, address, IBAN) are answered once and fill all PDFs.
- [ ] **4.2 Client Supporting-Document Uploads**: Allow candidates to upload passport/lease/contract scans into the case alongside the filled PDFs.
- [ ] **4.3 Case-Manager Review Comments & Re-open Flow**: Flag a specific field for correction and send a 1-click re-open link.
- [ ] **4.4 Zero-PII Organization Analytics & AI Spend Monitor (`G7`)**: Form opens, QR scans, completion rates, language breakdown, and per-tenant AI spend visibility in `/portal`.
- [ ] **4.5 Municipal Verification Queue & Compliance Audit Logs (`G9`)**: `/admin` org verification queue (`pending_review` -> `verified_official`) and persisted zero-PII audit logs.
- [ ] **4.6 `pgvector` HNSW Scaling (`G5-AI` Scale)**: Only when form catalog exceeds in-memory cosine similarity scale.

---

## Archive
Completed phase histories (`G2`–`G4`, `G5-AI`, `S0`–`S4`) are preserved in `docs/progress/` and git history.
