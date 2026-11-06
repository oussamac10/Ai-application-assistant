# Multilingual Government Forms SaaS Platform — Master Roadmap

**Core Vision:** Transform AI Form Assistant into a scalable, secure, multilingual, multi-tenant SaaS platform for government agencies, municipalities, immigration offices, universities, and public institutions.

- **Primary Business Model**: Organizations pay according to the **number of active published form templates** in their subscription.
- **Citizen Access**: Citizens fill out published official forms for **100% free**. No per-user, per-completion, per-link, or per-QR-code charges.
- **Implementation Strategy**: **Payments and subscriptions are deferred to Phase G8**. The primary focus is establishing the core operational platform first (workspaces, verification, schema review, public portals, QR codes, private invitations, and citizen guided intake).

---

## Strategic Roadmap Phases (G1 -> G9)

### Phase G1 — Multi-Tenant Organization Workspaces & Government Verification (`Active`)
- **Objectives:** Allow municipalities and institutions to manage their verified workspace, configure branding, and manage staff roles.
- **Scope:**
  - `Organization` profile schema: logo, cover image, office address, contact details, official website, supported languages.
  - Government status verification workflow: `unverified` -> `pending_review` -> `verified_official` -> `rejected`.
  - Role-Based Access Control (RBAC): `Platform Super Admin`, `Org Owner`, `Org Admin`, `Form Editor`, `Viewer`, `Citizen`.
  - Organization settings UI in the portal.

### Phase G2 — Form Upload, Parsing & Human Schema Review Workflow
- **Objectives:** Replace unreviewed dynamic uploads with an official government publishing state machine: `Draft -> Processing -> Needs Review -> Ready -> Published -> Archived`.
- **Scope:**
  - Background ARQ job parses uploaded PDF (AcroForms, OCR, Azure layout).
  - Visual Schema Review Studio: interactive dual-pane UI where staff review, rename, reorder, and correct fields before publishing.
  - Form metadata: category, instructions, required supporting documents, submission instructions.

### Phase G3 — Public Organization Portals & Citizen Discovery Directory
- **Objectives:** Give every verified organization an SEO-optimized public portal (`/organizations/[slug]`) and provide a central search directory on the platform homepage.
- **Scope:**
  - Public directory endpoint: search organizations by municipality, city, or name.
  - Public Organization Portal: branded landing page with verified badge, office hours, contact details, and searchable form list.
  - Zero-friction citizen access: no registration required for public forms.

### Phase G4 — Public Form Links & Printable Counter QR Codes (`Completed`)
- **Objectives:** Enable offices to generate unlimited links and printable physical collateral for counters and waiting areas.
- **Scope:**
  - Short URL resolver `/f/{short_code}` resolving to the active published form version.
  - Dynamic QR code generation (SVG and high-resolution PNG with organization branding).
  - Printable A4 counter poster generator ("Scan to fill out in your native language" for municipal counters).
  - 1-click share modal with direct link copying and website embed snippets.

### Phase G5 — Private Invitations & Email Verification
- **Objectives:** Allow case managers to invite specific citizens to fill out private administrative forms with strict identity protection.
- **Scope:**
  - Private invitation engine with cryptographically secure tokens, expiration dates, and revocation.
  - Email verification challenge (magic link or one-time 6-digit code) before unlocking form questions.
  - Audit logging of access attempts and completion timestamps.

### Phase G6 — Multilingual Citizen Guided Intake & Official PDF Export
- **Objectives:** Empower citizens to complete forms in their preferred language while producing an official, structurally accurate completed PDF in the required authority language.
- **Scope:**
  - 3-language model (`sourceLanguage`, `userLanguage`, `outputLanguage`) across 8 full UI languages (`en, de, fr, ar, tr, uk, es, ru`).
  - Strict deterministic validation (dates, IBAN, names) and Unicode font overlay rendering.
  - Multi-method submission instructions (Download & print, email, or physical delivery).

### Phase G7 — Organization Analytics Dashboard & AI Cost Firewall
- **Objectives:** Give organizations operational visibility into form performance while enforcing tenant-level AI spend guardrails.
- **Scope:**
  - Aggregated zero-PII metrics: form opens, QR scans, completions, average duration, popular languages.
  - Strict privacy: zero citizen answers or PII stored in analytics tables.
  - Per-tenant API token spend monitor and circuit breaker.

### Phase G8 — Document-Based SaaS Subscriptions (Stripe Integration — Deferred)
- **Objectives:** Activate commercial billing based on active published form templates once operational core is running smoothly.
- **Scope:**
  - Stripe Checkout and Customer Portal configured for active published form slots (e.g., Starter: 5 forms, Pro: 25 forms, Business: 100 forms).
  - Slot enforcement: publishing a new form checks against active plan limits; drafts and archived forms do not count.
  - Invoicing, billing history, and upgrade/downgrade workflows.

### Phase G9 — Platform Super Admin, Audit Trails & Pilot Launch
- **Objectives:** Equip platform operators to verify government credentials, monitor system health, and deploy to EU sovereign infrastructure.
- **Scope:**
  - Super admin verification queue for reviewing official municipal credentials.
  - Comprehensive audit logs for municipal compliance.
  - Production deployment to EU sovereign hosting.
- **Scope:** Paid EU `VertexAIProvider` adapter (preventing EEA-prohibited free-tier usage), non-root multi-stage Dockerfiles (`output: "standalone"`), GitHub Actions CI with PostgreSQL 16 + Alembic + `next build` + Playwright smoke tests, automated 6-hourly `age`-encrypted DB backups + monthly restore drill, Sentry EU + uptime/spend alerts.

### Phase S7 — Go-To-Market, Programmatic Form SEO, Credit Referrals & Iteration (`Ongoing` | `P1`)
- **Objectives:** Reach first 10 -> 100 paying customers at near-zero CAC and prioritize v1.2 features (*Multi-Document Packet Mode*, *Attachment Checklists*) strictly from paying user telemetry.
- **Scope:** 20+ bilingual `/forms/[slug]/[lang]` SEO landing pages, 50 personalized founder Loom demos to relocation consultants/*Vereine*, and **post-download 1-for-1 free form credit referral loop** (`<= EUR 0.014` API COGS/referral).

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
| **S1** | `S1-01` | Implement `StorageProvider` (`Local` + EU `S3/R2`) across `documents` and `pdf` | **P0** | **Completed (Verified)** | `S0-04` | 1.5d | Container restarts preserve all saved documents & exports |
| **S1** | `S1-02` | Add smartphone camera image (`JPG/PNG/WebP`) upload -> EXIF strip -> A4 PDF normalization | **P0** | **Completed (Verified)** | `S1-01` | 1.0d | Camera photo enters guided Q&A cleanly |
| **S1** | `S1-03` | Fix OCR `sourceLanguage` (`deu+eng+fra+ara+tur+ukr+spa`) + move `prepare-questions` to Redis/ARQ worker + rate limiting | **P0** | **Completed (Verified)** | `S1-01` | 2.0d | Scanned foreign PDF returns `202` in `<300ms` & completes async |
| **S1** | `S1-04` | Embed `NotoSans` + `NotoSansArabic` TTF fonts in PDF overlay + add watermarked preview | **P0** | **Completed (Verified)** | `S0-04` | 1.5d | Arabic, Cyrillic & Turkish characters render cleanly in PDF |
| **S2** | `S2-01` | Email verification, password reset, GDPR hard-delete (`DELETE /auth/me`) & JSON export (`GET /auth/me/export`) | **P1** | **Completed (Verified)** | `S1-01` | 2.0d | Zero S3 blobs or `form_answers` remain after deletion |
| **S2** | `S2-02` | Reusable Personal Profile Vault (`user_profile_entries` with Fernet encryption) + 1-click session pre-fill | **P1** | **Completed (Verified)** | `S2-01` | 2.0d | Form #2 pre-fills matching semantic keys in 1 click |
| **S2** | `S2-03` | Dual-Pane Verification Studio + deterministic cross-field consistency warnings | **P1** | **Completed (Verified)** | `S1-04` | 1.0d | 4-column comparison + rendered preview before export |
| **S3** | `S3-01` | 5-day Pricing Smoke Test + 15 newcomer / 10 consultant discovery interviews (`EXP-01`–`EXP-03`) | **P0** | **Todo (Founder Field Validation)** | `S0-04` | 1.0d | Validated pricing tiers before locking billing |
| **S3** | `S3-02` | Conversion homepage (+ 1-click sample forms), full 8-lang i18n (`tr/uk/es/ru`), modular session UI, *Impressum/Datenschutz/AGB* + *RDG* notices | **P1** | **Completed (Verified)** | `S2-03` | 3.0d | `<20s` to Q1; zero English leaks across 8 languages |
| **S3** | `S3-03` | Curate Top 10 German templates + register `PDFFingerprintRegistry` hashes (+ ready for 15–25 user private beta) | **P1** | **Completed (Verified)** | `S3-02` | 2.0d | `EUR 0` OCR/translation cost on matched Top-10 PDFs |
| **S4** | `S4-01` | Deterministic AI bypass, `gemini-2.5-flash-lite` routing, anon `<=5p` local-only sandbox, `submit_answer` rate limit, `ai_usage_events` + `EUR 0.25` cap | **P0** | **Todo** | `S1-03` | 1.5d | Free users incur `EUR 0` Azure cost; session capped at `EUR 0.25` |
| **S4** | `S4-02` | Stripe Checkout (`EUR 4.99` / default `EUR 16.99` Pack / `EUR 12.99` & `79/yr` / `EUR 39` Pro), Stripe Tax, `credit_ledger`, 7d typo re-export, auto-refund on fail, `+EUR 12` upsell, German *Kündigungsbutton* | **P1** | **Todo** | `S3-01`, `S4-01` | 3.5d | Live Stripe unlock, hard plan caps, zero-chargeback auto-refund |
| **S4B** | `S4B-01` | Admin runtime/cost kill-switches (`Azure` toggle, daily AI cap, upload pause, ARQ job inspector) + `AuditEvent` log | **P1** | **Todo** | `S4-01` | 1.0d | Founder can halt paid API spikes in 1 click without redeploying |
| **S4B** | `S4B-02` | Protected `/admin` UI (`require_admin`): margin pulse, user credit grant/ban, visual `forms` & `questions` approval studio | **P1** | **Todo** | `S4-02`, `S4B-01` | 1.5d | Full zero-PII platform control; `403` enforced for non-admins |
| **S5** | `S5-01` | Organization / Association Portals (`/p/[orgSlug]` + `/org/[slug]/admin` + `EUR 99/mo` `200`-doc plan, gated on `EXP-03`) | **P1** | **Todo** | `S4-02` | 5.0d | 2 pilot organizations live on `/p/{slug}` |
| **S6** | `S6-01` | Paid EU `VertexAIProvider` (`europe-west3`), multi-stage non-root Dockerfiles (`standalone`), `docker-compose.prod.yml`, Caddy HTTPS | **P0** | **Todo** | `S1-03` | 2.0d | Zero EEA unpaid-tier calls; non-root + Observatory A+ |
| **S6** | `S6-02` | GitHub Actions Postgres 16 + Alembic + Next build + Playwright CI, Hetzner EU deploy & backup restore drill | **P0** | **Todo** | `S6-01` | 2.5d | Automated CI/CD + `<10m` verified DB restore |
| **S7** | `S7-01` | 20+ bilingual `/forms/[slug]/[lang]` SEO pages + 50 agency Looms + post-download 1-for-1 credit referral loop | **P1** | **Todo** | `S6-02` | Ongoing | First 10 -> 100 paying customers at near-zero CAC |

---

## 3. 30 / 60 / 90-Day Solo-Developer Execution Timeline

- **Days 1–30:** Complete `Phase S0` + `Phase S1` + `Phase S2` + `Phase S3` (8-language UX + discovery/pricing test) + `Phase S4` (Stripe self-serve checkout) + `Phase S4B` (Founder `/admin` Control Center) + `Phase S6` (EU Hetzner prod deploy).
- **Days 31–60:** Validate `EXP-03` & complete `Phase S5` (Organization Portals `/p/{slug}`) + founder Loom outreach -> **First 10–40 Paying Customers**.
- **Days 61–90:** Scale programmatic form SEO (35+ forms x 8 languages), onboard 5–10 Organization Portals, and build v1.2 *Multi-Document Packet Mode* once >=5 organizations pay -> **Path to First 100 Paying Customers**.
