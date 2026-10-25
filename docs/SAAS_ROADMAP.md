# SaaS Master Roadmap & Task Checklist

**Baseline Verified in Code:** Core Phases 1–18 implemented (`878+` backend tests, `225` frontend unit tests, `59` Playwright E2E specs).  
**Forward Objective:** Transform the repository into a secure, EU-hosted, revenue-generating SaaS for individual newcomers and B2B2C Relocation Agencies / Migrant Associations.

> [!IMPORTANT]
> Only items marked **`Completed (Verified)`** exist in the codebase today. Planned SaaS tasks remain **`Todo`** or **`In Progress`** until implemented and verified by automated tests.

---

## 1. SaaS Implementation Phases (`Phase S0` -> `Phase S7`)

### Phase S0 — P0 Security, Privacy & Production Blockers Remediation (`3 Days` | `P0`)
- **Objectives:** Close all critical vulnerabilities (`FLAW-01`–`FLAW-07` subset in auth/catalog/logging/cleanup) before public exposure.
- **Scope:**
  - `S0-01`: Filter `GET /api/published-forms` to `origin == "predefined_template"` (hiding `signature-demo` in prod) and guard `forms` + `questions` admin endpoints with `require_admin` RBAC (`users.role = "platform_admin"`) + CSRF.
  - `S0-02`: Move `GEMINI_API_KEY` from URL query string to `x-goog-api-key` HTTP header, separate `systemInstruction`, and set `httpx`/`httpcore` loggers to `WARNING`.
  - `S0-03`: Fail fast at startup in `production` when `AUTH_SECRET`, `SESSION_TOKEN_SECRET`, or `AUTH_COOKIE_SECURE=True` are unset; remove `REBIND_ON_NEXT_REQUEST` bypass; add constant-time dummy Argon2 check on unknown-email login.
  - `S0-04`: Restrict `cleanup_expired_exports.py` `SourceDocument` deletion to `user_id IS NULL`, clear `doc.expires_at` on `ApplicationService.claim`, fix multi-page `PypdfRenderer`, fix `/applications` progress %, and strip `console.log` from `[sessionId]/page.tsx`.

### Phase S1 — Storage Provider, Async Preparation, Camera Scan & Unicode PDF (`6 Days` | `P0`)
- **Objectives:** Replace `/tmp` with durable private EU S3 storage, support phone camera photos of paper forms, fix scanned foreign-language OCR, eliminate 180s synchronous HTTP timeouts, and support Arabic/Cyrillic/Turkish PDF export fonts.
- **Scope:** `StorageProvider` (`Local` + `S3/R2`), `JPG/PNG/WebP -> A4 PDF` upload normalization (EXIF stripped), multi-script Tesseract (`deu+eng+fra+ara+tur+ukr+spa`), Redis + ARQ background worker (`202 Accepted` + `/api/jobs/{id}`) + API rate limiting, embedded `NotoSans` + `NotoSansArabic` TTF fonts + watermarked PDF preview.

### Phase S2 — Complete Account Lifecycle, GDPR Controls, Profile Vault & Verification Studio (`5 Days` | `P1`)
- **Objectives:** Maximize retention via 1-click Reusable Profile Pre-Fill and close GDPR Art. 17/20 requirements.
- **Scope:** Email verification & password reset (`Postmark`/`Scaleway TEM`), hard-delete cascade (`DELETE /api/applications/{id}`, `DELETE /api/auth/me`) + data export (`GET /api/auth/me/export`), Fernet-encrypted `user_profile_entries` vault (`personal.*`, `contact.*`, `address.*`, `finance.iban`), Dual-Pane Verification Studio + deterministic cross-field consistency warnings.

### Phase S3 — UX Polish, 8 Full UI Languages, Curated Top-10 Library & Private Beta (`5 Days` | `P1`)
- **Objectives:** Ship a calm, conversion-ready multilingual product across 8 full UI languages (`en, de, fr, ar, tr, uk, es, ru`) and run a 5-day pricing smoke test + 15-user private beta.
- **Scope:** Replace developer homepage, localize all hardcoded English strings, modularize `[sessionId]/page.tsx`, publish Impressum/Datenschutz/AGB, curate Top 10 everyday German templates, run Mom-Test discovery + pricing smoke test.

### Phase S4 — SaaS Monetization, Token Metering & Stripe Checkout (`5 Days` | `P1`)
- **Objectives:** Collect automated self-serve revenue with strict per-session AI cost guardrails.
- **Scope:** `ai_usage_events` token/cost ledger + `EUR 0.25/session` cap, Stripe Checkout + Stripe Tax + Customer Portal (`EUR 5.90` single unlock, `EUR 19.90` 5-form Relocation Pack, `EUR 12.90/mo` Individual Pro), idempotent `credit_ledger` webhook processor.

### Phase S5 — Organization / Association Portals (`5 Days` | `P1`)
- **Objectives:** Unlock recurring `EUR 89–229/mo` B2B2C MRR for relocation agencies, recruiters, and migrant associations (per [`docs/association-document-portal.md`](association-document-portal.md)).
- **Scope:** `organizations`, `organization_members`, `organization_portal_forms`, org admin verification workspace (`/org/[slug]/admin`), and branded public client portal (`/p/[orgSlug]`) billed against organization quota.

### Phase S6 — Production EU Deployment, CI/CD, Backups & Monitoring (`4 Days` | `P0`)
- **Objectives:** Launch hardened EU infrastructure (`Hetzner Cloud Germany` + `Caddy` + `Vertex AI europe-west3` / `Azure Germany West Central`).
- **Scope:** Non-root multi-stage Dockerfiles (`output: "standalone"`), GitHub Actions CI with PostgreSQL 16 + Alembic + `next build` + Playwright smoke tests, automated 6-hourly `age`-encrypted DB backups + monthly restore drill, Sentry EU + uptime alerts.

### Phase S7 — Go-To-Market, Programmatic Form SEO & Post-Revenue Iteration (`Ongoing` | `P1`)
- **Objectives:** Reach first 10 -> 100 paying customers and prioritize v1.2 features (*Multi-Document Packet Mode*, *Attachment Checklists*) strictly from paying user telemetry.

---

## 2. Master Checklist

| Phase | Task ID | Task Description | Priority | Status | Dependencies | Effort | Acceptance Criteria |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Core 1–18** | `HIST-01` | Monorepo, 3-language session/answer state machine, deterministic validators, 6-tier question catalog | P0 | **Completed (Verified)** | — | Done | Verified in `backend/app/{forms,sessions,answers,questions}` |
| **Core 1–18** | `HIST-02` | PDF upload/sanitization, local OCR, hybrid local/Azure detection, accounts, signatures, live preview & overlay | P0 | **Completed (Verified)** | `HIST-01` | Done | Verified through Phase 18 commits |
| **S0** | `S0-01` | Filter `/api/published-forms` to `origin="predefined_template"` & enforce `require_admin` RBAC + CSRF on `forms`/`questions` admin routes | **P0** | **Completed (Verified)** | `HIST-02` | 0.5d | Dynamic uploads never appear publicly; `401`/`403` enforced |
| **S0** | `S0-02` | Move `GEMINI_API_KEY` to `x-goog-api-key` header, separate `systemInstruction`, silence `httpx` URL logs | **P0** | **Completed (Verified)** | `HIST-02` | 0.5d | Zero API keys in `INFO` logs; unit tests pass |
| **S0** | `S0-03` | Fail fast on missing prod secrets (`AUTH_SECRET`, `SESSION_TOKEN_SECRET`, `AUTH_COOKIE_SECURE`), remove `REBIND_ON_NEXT_REQUEST`, add dummy Argon2 login verify | **P0** | **Completed (Verified)** | `HIST-02` | 0.5d | Prod config validation raises `ValueError` on unsafe defaults |
| **S0** | `S0-04` | Guard `cleanup_expired_exports` with `user_id IS NULL`, fix multi-page `PypdfRenderer`, dashboard progress & `console.log` | **P0** | **Completed (Verified)** | `HIST-02` | 1.0d | Claimed PDFs survive 24h cleanup; Page 2+ AcroForms render |
| **S1** | `S1-01` | Implement `StorageProvider` (`Local` + EU `S3/R2`) across `documents` and `pdf` | **P0** | **Todo** | `S0-04` | 1.5d | Container restarts preserve all saved documents & exports |
| **S1** | `S1-02` | Add smartphone camera image (`JPG/PNG/WebP`) upload -> EXIF strip -> A4 PDF normalization | **P0** | **Todo** | `S1-01` | 1.0d | Camera photo enters guided Q&A cleanly |
| **S1** | `S1-03` | Fix OCR `sourceLanguage` (`deu+eng+fra+ara+tur+ukr+spa`) + move `prepare-questions` to Redis/ARQ worker + rate limiting | **P0** | **Todo** | `S1-01` | 2.0d | Scanned foreign PDF returns `202` in `<300ms` & completes async |
| **S1** | `S1-04` | Embed `NotoSans` + `NotoSansArabic` TTF fonts in PDF overlay + add watermarked preview | **P0** | **Todo** | `S0-04` | 1.5d | Arabic, Cyrillic & Turkish characters render cleanly in PDF |
| **S2** | `S2-01` | Email verification, password reset, GDPR hard-delete (`DELETE /auth/me`) & JSON export (`GET /auth/me/export`) | **P1** | **Todo** | `S1-01` | 2.0d | Zero S3 blobs or `form_answers` remain after deletion |
| **S2** | `S2-02` | Reusable Personal Profile Vault (`user_profile_entries` with Fernet encryption) + 1-click session pre-fill | **P1** | **Todo** | `S2-01` | 2.0d | Form #2 pre-fills matching semantic keys in 1 click |
| **S2** | `S2-03` | Dual-Pane Verification Studio + deterministic cross-field consistency warnings | **P1** | **Todo** | `S1-04` | 1.0d | 4-column comparison + rendered preview before export |
| **S3** | `S3-01` | 5-day Pricing Smoke Test + 15 user / 10 organization discovery interviews | **P0** | **Todo** | `S0-04` | 1.0d | Validated pricing tiers before building ledger |
| **S3** | `S3-02` | Conversion homepage, full i18n (`tr/uk/es/ru.json`), modularize `[sessionId]/page.tsx`, legal pages | **P1** | **Todo** | `S2-03` | 3.0d | Zero English leaks across all 8 languages |
| **S3** | `S3-03` | Curate Top 10 everyday German templates + run 15–25 user private beta | **P1** | **Todo** | `S3-02` | 2.0d | >=15 end-to-end beta completions |
| **S4** | `S4-01` | `ai_usage_events` token/cost metering + `EUR 0.25/session` spend cap | **P1** | **Todo** | `S1-03` | 1.5d | Exact per-session margin tracked in DB |
| **S4** | `S4-02` | Stripe Checkout (`EUR 5.90` / `EUR 19.90` / `EUR 12.90/mo`), `credit_ledger`, Stripe Tax & webhooks | **P1** | **Todo** | `S3-01`, `S4-01` | 3.5d | Live Stripe transaction unlocks clean PDF idempotently |
| **S5** | `S5-01` | Organization / Association Portals (`/p/[orgSlug]` + `/org/[slug]/admin` + `EUR 89/229` plans) | **P1** | **Todo** | `S4-02` | 5.0d | 2 pilot organizations live on `/p/{slug}` |
| **S6** | `S6-01` | Multi-stage non-root Dockerfiles, `output: "standalone"`, `docker-compose.prod.yml`, Caddy HTTPS/headers | **P0** | **Todo** | `S1-03` | 1.5d | Non-root containers + Mozilla Observatory A+ |
| **S6** | `S6-02` | GitHub Actions Postgres 16 + Alembic + Next build + Playwright CI, Hetzner EU deploy & backup restore drill | **P0** | **Todo** | `S6-01` | 2.5d | Automated CI/CD + `<10m` verified DB restore |
| **S7** | `S7-01` | 20+ bilingual form SEO pages + founder Loom outreach to 50 agencies/associations | **P1** | **Todo** | `S5-01`, `S6-02` | Ongoing | First 10 -> 100 paying customers |

---

## 3. 30 / 60 / 90-Day Solo-Developer Execution Timeline

- **Days 1–30:** Complete `Phase S0` + `Phase S1` + `Phase S6` (EU Hetzner staging/prod) + `Phase S3` (8-language UX + discovery/pricing test) + `Phase S4` (Stripe self-serve checkout live).
- **Days 31–60:** Complete `Phase S2` (Reusable Profile Vault + GDPR self-service) + `Phase S5` (Organization Portals `/p/{slug}`) + founder Loom outreach -> **First 10 Paying Customers**.
- **Days 61–90:** Scale programmatic form SEO (35+ forms x 8 languages), onboard 5–10 Organization Portals, and build v1.2 *Multi-Document Packet Mode* once >=5 organizations pay -> **Path to First 100 Paying Customers**.
