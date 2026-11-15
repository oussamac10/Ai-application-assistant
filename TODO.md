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
  - Single Alembic head (`h9c0d1e2f3a4`), `ruff check/format`, `mypy app` (237 files), `pytest` on `ai_form_assistant_test` (1,106 passed, 1 skipped), `tsc --noEmit`, `next lint`, `vitest run` (45 files, 314 passed), `next build`, Playwright E2E `user-accounts-persistent-sessions-flow.spec.ts` (2 passed).

---

## Current Task: UI Dark/Light Mode Contrast & Plain-Language Polish (Completed)

- **Goal**: Fix every Dark Mode and Light Mode contrast/theme bug across all frontend components and remove all version badges, internal keys/slugs/coordinates, and developer jargon so the entire website is intuitive and easy to understand in all 8 languages.
- **Acceptance Criteria**:
  - Zero dark-box-on-white or dark-text-on-dark-gradient issues in Light Mode (`html.light`), and `Sidebar` always respects the user's Dark/Light toggle.
  - Zero version badges (`v1`, `v{versionNumber}`), internal keys/slugs (`{f.key}`, `{cat.slug}`, `AcroForm Key`), raw coordinate numbers, Python code snippets, or opaque engineering jargon visible to users.
  - 100% key and `{placeholder}` parity preserved across `frontend/messages/{en,de,fr,ar,tr,uk,es,ru}.json`.
  - `npm run typecheck`, `npm run lint`, `vitest run`, `npm run build`, and Playwright E2E pass.
- **Planned Steps**:
  - [x] Fix Light/Dark CSS overrides, gradient stops, `<option>` styling, and white paper borders in `frontend/src/app/globals.css`.
  - [x] Fix component-level theme bugs (`Sidebar.tsx`, `AppShell.tsx`, `account/page.tsx`, `pricing/page.tsx`, `SessionConfirmationPanel.tsx`, `SessionContextSidebar.tsx`, `OrganizationSettings.tsx`).
  - [x] Remove version badges, internal keys/slugs/coordinates, code snippets, and developer jargon across navigation, homepage, pricing, upload/session/summary/complete flows, account, admin, portal, and studio components.
  - [x] Rewrite technical jargon in all 8 `frontend/messages/*.json` locale files with 100% key + placeholder parity (`474` keys each).
  - [x] Update affected Vitest copy assertions and run full frontend verification (`typecheck`, `lint`, `vitest` 45 files / 314 passed, `next build`, Playwright E2E 2 passed) + `graphify update .`.
- **Files Changed**: `frontend/src/app/globals.css`, `frontend/src/components/{Sidebar,AppShell,Navbar,Footer}.tsx`, `frontend/src/app/{layout,page,pricing/page,datenschutz/page,account/page,admin/page,f/[...slug]/page,application/session/[sessionId]/summary/page,application/session/[sessionId]/complete/page}.tsx`, `frontend/src/features/**`, `frontend/messages/*.json`, and updated frontend unit tests.

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
