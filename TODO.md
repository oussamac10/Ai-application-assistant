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
  - **Aikido-Inspired Obsidian & Emerald Frontend Overhaul**: Unified dark obsidian (`#0A0E17` / `#0F1522`) & emerald (`#10B981`) design system with `prefers-reduced-motion`-safe scan/reveal animations, rebuilt obsidian error/loading/not-found boundaries, and international worldwide copy/defaults across all portals, modals, auth/account, and guided session pages (`tsc --noEmit` 0 errors, `next lint` 0 warnings/errors, `vitest run` 44 files / 308 passed, `next build` clean, Playwright `user-accounts-persistent-sessions-flow.spec.ts` 2 passed).
  - Single Alembic head (`g8b9c0d1e2f3`), `ruff check/format`, `mypy app` (236 files), `pytest` on `ai_form_assistant_test` (1,092 passed, 1 skipped), `tsc --noEmit`, `next lint`, `vitest run` (44 files, 308 passed), `next build`, Playwright E2E `user-accounts-persistent-sessions-flow.spec.ts` (2 passed).

---

## Current Task: Sell-First SaaS Roadmap

### Step 1 — Go-Live & Trial Time-to-Value (Completed)
- [x] **1.1 Unify Plan Limits**: Align `agency_pro` / `enterprise` limits between `backend/app/billing/services.py` (monthly cases & template slots) and `backend/app/forms/organization_service.py` via `get_published_template_limit`.
- [x] **1.2 `<60s` Trial Onboarding**: Added `backend/app/forms/starter_templates.py` + `POST /api/organizations/current/forms/starter-templates` + 1-click **"Load 3 German Starter Templates"** empty-state action in `PortalDashboard.tsx` (*Anmeldung*, *Wohnungsgeberbestätigung*, *Aufenthaltstitel*).
- [x] **1.3 Playwright E2E Verification**: Updated `frontend/e2e/user-accounts-persistent-sessions-flow.spec.ts` to match current UI (`2 passed` in `11.9s`).

### Step 2 — Agency Sales Essentials
- [ ] **2.1 Private Invite Email / OTP Verification (`G5`)**: Require recipient email verification (magic link or 6-digit OTP) before unlocking sensitive private forms, plus case-manager link revocation/resend/audit trail.
- [ ] **2.2 Pre-Form Document Checklist & Submission Instructions (`G6`)**: Show required supporting documents before Q&A starts and form-specific submission steps after PDF export.
- [ ] **2.3 White-Label Invite Experience**: Display the agency's logo, brand name, and contact details on `/portal/invite/[token]`.

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
