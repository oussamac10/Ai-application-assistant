# Project TODO

## Completed Phases

Archived under `docs/progress/`:

1. Project Foundation
2. Form Definitions and Versioning
3. Temporary Anonymous Sessions
4. Mock Question and Answer Workflow
5. Local AI Integration with Ollama
6. Reusable Question Catalog and Hybrid Resolution
7. Frontend Guided Form Experience
8. PDF Template Mapping and Export
9. Form Upload and Document Analysis
10. OCR Integration
11. Dynamic Form Field Detection
12. User Accounts and Saved Applications
13. Automatic Upload-to-Questions User Flow
14. Azure Document Intelligence Provider
15. Azure Translator Integration
16. Hybrid Document Detection
17. Dynamic Coordinate-Overlay PDF Export, Document Location Preview & Voice Dictation
18. Plain-Language Field Explanations & Submission Checklist

## Current Task

Execute **SaaS Phase S0** (`S0-01` through `S0-04`): P0 Security, Privacy & Production Blockers Remediation (see [`docs/SAAS_ROADMAP.md`](docs/SAAS_ROADMAP.md)).

## Goal

Eliminate all P0 security, multi-tenancy, credential-leakage, and data-retention blockers identified in the Principal Architecture Audit before enabling cloud object storage, Stripe billing, and public SaaS launch.

## Acceptance Criteria

- [x] **`S0-01` Admin RBAC & Dynamic Form Isolation**:
  - Add `users.role` (`user` | `org_admin` | `platform_admin`, default `user`) + Alembic migration `a1b2c3d4e5f6` + `ADMIN_EMAILS` bootstrap configuration.
  - Protect all admin form/version/field CRUD/publish/clone endpoints (`/api/forms*`, `/api/form-versions/{id}` admin routes, `/api/form-fields/{id}`) and `/api/questions*` with `require_admin` (`401` anonymous, `403` regular user) and `verify_csrf` on mutations.
  - Filter `GET /api/published-forms` (and `POST /api/form-versions/{id}/sessions`) strictly to `FormVersion.origin == "predefined_template"` (and exclude `signature-demo` in production) so uploaded user PDFs (`dynamic_detection`) never leak across sessions.
- [x] **`S0-02` Cloud AI Credential Header Hardening**:
  - Transmit `GEMINI_API_KEY` exclusively via `x-goog-api-key` HTTP header in `GeminiAIProvider._post` and `health_check` (never in `?key=` URL query strings), separate `systemInstruction`, and pin `httpx` / `httpcore` loggers to `WARNING` in `app/main.py`.
- [x] **`S0-03` Production Secret Fail-Fast, Backdoor Removal & Constant-Time Login**:
  - Fail fast at startup when `ENVIRONMENT=production` if `SESSION_TOKEN_SECRET` or `AUTH_SECRET` is unset, `< 32` chars, or equals a dev fallback, or if `AUTH_COOKIE_SECURE` is `False`.
  - Remove legacy `REBIND_ON_NEXT_REQUEST` ownership-token branch in `SessionService.get_session`.
  - Equalize `AuthService.login` timing on unknown/inactive emails using `_DUMMY_PASSWORD_HASH`.
- [x] **`S0-04` Claimed Document Retention, Multi-Page AcroForm Export, Progress % & Console Cleanup**:
  - Restrict `SourceDocument` TTL cleanup in `cleanup_expired_exports.py` to anonymous documents (`user_id IS NULL`) unless explicitly marked `deleted`.
  - Update `PypdfRenderer.render` to populate AcroForm fields across all pages (`for page in writer.pages`) with `/DR` catalog fallback.
  - Compute application dashboard progress over `len(session.version.fields)` when `total_required_fields == 0` in `applications/services.py`.
  - Remove `console.log("FETCHED FIELD:", ...)` from `frontend/src/app/application/session/[sessionId]/page.tsx`.
- [x] All backend (`ruff`, `mypy`, `1,154` `pytest` tests on isolated `ai_form_assistant_test` DB) and frontend (`tsc`, `eslint`, `239` `vitest` tests) checks pass with new security regression tests.
- [x] **Workspace Agent Skills & Rule Budget Upgrade (Pre-`Phase S1`)**:
  - Installed `9` vetted, zero-script open-source GitHub skills (`vercel-react-best-practices`, `frontend-design`, `wcag-audit-patterns`, `supabase-postgres-best-practices`, `stripe-best-practices`, `differential-review`, `systematic-debugging`, `test-driven-development`, `verification-before-completion`) pinned with SHA-256 hashes in `.agents/skills/SOURCES.lock.json`.
  - Authored `6` custom AI Form Assistant project skills (`ai-form-architecture`, `multilingual-form-engine`, `pdf-processing-quality`, `ai-reliability`, `saas-readiness`, `release-quality-gate`) and `.agents/skills/README.md`.
  - Compacted `.agents/AGENTS.md` from `40,263` bytes to `12,699` bytes so Antigravity `<user_rules>` loads `100%` of project rules with zero trailing truncation.
