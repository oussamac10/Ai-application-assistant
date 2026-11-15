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
  - Single Alembic head (`h9c0d1e2f3a4`), `ruff check/format`, `mypy app` (237 files), `pytest` on `ai_form_assistant_test` (1,106 passed, 1 skipped), `tsc --noEmit`, `next lint`, `vitest run` (45 files, 314 passed), `next build`, Playwright E2E `user-accounts-persistent-sessions-flow.spec.ts` (2 passed).

---

## Current Task: Table-Per-Row Validation Fix, Choice-in-Row Grouping & Zero-PII Continual Schema Learning

- **Goal**:
  1. Fix table-row validation bugs (`"validation"` banner from `field_key` vs UUID mismatch, `country`/`number`/`choice` normalization & validation, and missing Row 1 Applicant fields), add atomic batch row submit/skip endpoints, and align `TableRowGroupCard` with Light/Dark theme + 8-locale i18n.
  2. Upgrade PDF extraction & export to detect table structures per row, bundle intra-row & grouped checkboxes into `single_choice`/`multiple_choice` fields with `option_boxes`, distinguish Row 1 (`applicant`) vs Rows 2..N (`member`, no applicant Vault leakage), and tick exact `option_boxes` on PDF export.
  3. Add interactive row selection & choice controls in both **Review Studio** (collapsible table row groups, row tabs, canvas row highlight, Shift-click / multi-select "Combine into Choice Question" & "Group as Table Row", inline options editor, "Apply Row 1 settings to all rows") and **Guided Session** (clickable row selector pills, 1-tap choice pills inside rows, "Skip remaining empty rows").
  4. Add Zero-PII **Continual Schema Learning** (`learned_form_patterns` table, migration `i0d1e2f3a4b5`) capturing admin/agency table, choice, and field curations (without any applicant PII) to improve future PDF detections, auto-mapping, and citizen field resolution.
- **Acceptance Criteria**:
  - Submitting valid or partially skipped rows in `TableRowGroupCard` (including `"German"`/`"Deutsch"` nationality, `choice` options, numbers, and empty optional cells) succeeds without generic `"validation"` errors and shows localized per-field errors if any cell is invalid.
  - Uploading multi-row/checkbox PDFs (such as Stuttgart WBS) groups table fields per row (including Row 1 Applicant) and bundles adjacent checkboxes (`ja`/`nein`, `m`/`w`/`d`) into choice fields whose selected PDF checkboxes get ticked on export.
  - Review Studio supports collapsible table groups, row tabs, multi-select combine-into-choice & group-as-table-row actions, option editing, and bulk row column sync.
  - Guided Session supports clickable row tabs, 1-tap compact choice buttons in table rows, and "Skip remaining empty rows".
  - `learned_form_patterns` (Zero-PII) records agency/admin curations and improves future similar PDF extractions (`hash` -> `Jaccard` -> `EmbeddingProvider`), while passing `ruff`, `mypy`, isolated `pytest`, `typecheck`, `lint`, `vitest`, `next build`, and Playwright E2E.
- **Planned Steps**:
  - [x] Fix backend `country`/`number`/`choice` normalization & validation (`normalization.py`, `validation.py`).
  - [x] Add `field_id`, `placeholder`, `rows_overview`, explicit `configuration["table"]` priority, and atomic `table-rows/submit` & `table-rows/skip` endpoints (`answers/schemas.py`, `services.py`, `routes.py`).
  - [x] Add `LearnedFormPattern` model, Alembic migration `i0d1e2f3a4b5`, and Zero-PII `FormPatternLearningService`.
  - [x] Upgrade `pdf_field_extractor.py`, `organization_service.py`, `organizations/api/routes.py`, `auto_mapper.py`, `question_bridge.py`, and `dynamic_overlay.py` (`option_boxes` export + table/choice extraction + learning hooks).
  - [x] Add backend unit & integration tests and verify isolated `pytest`, `ruff`, and `mypy`.
  - [x] Upgrade Guided Session UX (`apiClient.ts`, `FieldRenderer.tsx`, `TableRowGroupCard.tsx`, `session/[sessionId]/page.tsx`) + all 8 `frontend/messages/*.json`.
  - [x] Upgrade Review Studio UX (`portal/types.ts`, `portalClient.ts`, `ReviewStudioFieldCard.tsx`, `ReviewStudioTableGroupCard.tsx`, `ReviewStudioCanvas.tsx`, `FormSchemaReviewStudio.tsx`).
  - [x] Add frontend Vitest suites and run full verification gate (`typecheck`, `lint`, `vitest`, `build`, Playwright E2E, `graphify update .`) + commit on feature branch.
- **Files Expected to Change**:
  - `backend/app/answers/{normalization/normalization,validation/validation,schemas,services,api/routes}.py`
  - `backend/app/forms/{learning_models,learning_service,pdf_field_extractor,organization_service,auto_mapper,schemas}.py`
  - `backend/app/organizations/api/routes.py`, `backend/app/field_detection/question_bridge.py`, `backend/app/pdf/dynamic_overlay.py`
  - `backend/migrations/env.py`, `backend/migrations/versions/i0d1e2f3a4b5_add_learned_form_patterns.py`
  - `frontend/src/features/form-session/{services/apiClient.ts,components/FieldRenderer.tsx,components/TableRowGroupCard.tsx}` & `frontend/src/app/application/session/[sessionId]/page.tsx`
  - `frontend/src/features/portal/{types.ts,services/portalClient.ts,components/FormSchemaReviewStudio.tsx,components/review-studio/*}`
  - `frontend/messages/{en,de,fr,ar,tr,uk,es,ru}.json`, `docs/{DATABASE_DESIGN,AI_PIPELINE}.md`, backend & frontend test suites.
- **Decisions and Assumptions**:
  - Standalone `single_choice` continues rendering `<select>` unless `compactChoicePills` is enabled (preserving existing UI contracts).
  - `_detect_geometric_table_row` preserves `<= 10.0` tolerance for backwards compatibility while `configuration["table"]` carries authoritative multi-row bindings.
  - Learning table is 100% Zero-PII (schema labels, headers, options, Vault keys, and normalized structure only).
- **Blockers**: None.
- **Verification**:
  - Backend: `ruff check .` (`All checks passed!`), `ruff format --check .` (`344 files already formatted`), `mypy app` (`Success: no issues found in 241 source files`), isolated `pytest -q` on `ai_form_assistant_test` (`1111 passed, 1 skipped`).
  - Frontend: `npm run typecheck` (`tsc --noEmit` exit `0`), `npm run lint` (`✔ No ESLint warnings or errors`), `CI=1 npx vitest run` (`47 passed (47)`, `318 passed (318)`), `npm run build` (`✓ Compiled successfully`, `18/18` static pages), Playwright `e2e/user-accounts-persistent-sessions-flow.spec.ts` (`2 passed` in `13.5s`), 8-locale parity check (`492` keys across all 8 locales).

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
