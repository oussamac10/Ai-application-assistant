# Project TODO

## Completed Phases

Archived under `docs/progress/`:

1–18. Core MVP & Hybrid Multilingual Pipeline (`phase-1` through `phase-18-explanations-and-checklist.md`)
- **SaaS Phase S0**: P0 Security, RBAC, Dynamic-Form Isolation, Credential Hardening & Retention (`docs/progress/phase-s0-security-and-hardening.md`)
- **SaaS Phase S1**: Storage Provider, Smartphone Camera Scan Normalization, Multi-Script OCR + Async Jobs & Rate Limiting, Scanned Box Detection, and Embedded Unicode/RTL PDF + Watermarked Preview (`docs/progress/phase-s1-storage-camera-async-unicode.md`)
- **SaaS Phase S2**: Account Lifecycle, GDPR Art. 17/20 Self-Service Controls, Encrypted Reusable Profile Vault (1-Click Pre-Fill), and Dual-Pane Verification Studio (`docs/progress/phase-s2-accounts-gdpr-vault-studio.md`)
- **Business-Driven SaaS Partner Upgrade (Stage A & B)**: Vetted SaaS marketing/pricing/research skills (`pricing`, `customer-research`, `competitor-profiling`, `cro`, `paywalls`, `ab-testing`), permanent `saas-business-advisor` Co-Founder skill + `.agents/product-marketing.md`, `10`–`10,000` user CFO unit economics & 7-doc `docs/business/` suite (`docs/progress/stage-b-saas-business-partner-upgrade.md`)

---

## Current Task

**Business-Driven SaaS Engineering Partner Upgrade (Stage B — Completed & Verified)**: Ready for next founder-approved execution milestone (`EXP-01` / `EXP-03` customer & pricing validation alongside `S4-01` deterministic AI bypass & `€0.25/session` spend cap, or committing completed `Phase S2` + `Stage B` changes).

## Goal

Operate permanently as an evidence-based Technical Co-Founder & CFO partner that protects gross margins, separates validated facts from `[ASSUMPTION]`s, challenges premature engineering complexity, and evaluates customer value, unit economics, and technical impact before major product/architecture investments.

## Acceptance Criteria

- [x] **External Business Skills Installed & Pinned**: Installed the 6 approved MIT pure-Markdown skills (`pricing`, `customer-research`, `competitor-profiling`, `cro`, `paywalls`, `ab-testing`) from `coreyhaines31/marketingskills@17772c7a80b7` into `.agents/skills/` (zero executable scripts or sponsored tool files) with exact SHA-256 hashes recorded in `.agents/skills/SOURCES.lock.json` and `.agents/skills/README.md`.
- [x] **Custom `saas-business-advisor` Skill & Shared Positioning Context**: Created `.agents/skills/saas-business-advisor/SKILL.md` (11 activation triggers, proportionate bug-fix fast path, 4-pillar Business Evaluation Framework, 7-line Business Decision Summary, German VAT/Stripe/COGS guardrails, Co-Founder pushback rules) and `.agents/product-marketing.md`.
- [x] **Antigravity Skill Discovery & Workflow Integration**: Validated all `22` `.agents/skills/*/SKILL.md` frontmatter and `SOURCES.lock.json` integrity (`173` locked files); integrated `saas-business-advisor` and the Business Decision Summary workflow into `.agents/AGENTS.md` (`14,391` bytes < `22,000` bytes).
- [x] **Persistent Business Documentation & Multi-Scale CFO Model (`docs/business/`)**: Created `BUSINESS_STRATEGY.md`, `PRICING.md`, `UNIT_ECONOMICS.md` (`10, 50, 100, 500, 1,000, 5,000, 10,000` users across conservative/base/optimistic scenarios with 2026-10-26 official provider pricing, 19% VAT, Stripe EEA/non-EEA fees, and 12 API cost optimizations), `CUSTOMER_RESEARCH.md`, `COMPETITOR_ANALYSIS.md`, `GROWTH_STRATEGY.md`, and `BUSINESS_EXPERIMENTS.md`, harmonized with existing `docs/*.md`.
- [x] **Live Skill Dry-Run Verification**: Evaluated 3 real product/architecture roadmap decisions (`S4-01` -> `Build now`, `S5-01` -> `Validate with customers first`, Public API / White-Label -> `Defer / Reject`) in `docs/business/BUSINESS_STRATEGY.md`.

## Planned Steps

- [x] 1. Vendor the 6 pure-Markdown MIT skills from `coreyhaines31/marketingskills@17772c7a80b7` into `.agents/skills/` and update `.agents/skills/SOURCES.lock.json` with SHA-256 checksums.
- [x] 2. Create `.agents/skills/saas-business-advisor/SKILL.md` and `.agents/product-marketing.md`.
- [x] 3. Update `.agents/skills/README.md` and `.agents/AGENTS.md` (`< 22,000` bytes), and run automated skill-discovery + SHA-256 lockfile verification.
- [x] 4. Author `docs/business/UNIT_ECONOMICS.md` (programmatically verified `10`–`10,000` user financial tables + 12 API cost optimizations) and `docs/business/PRICING.md`.
- [x] 5. Author `docs/business/BUSINESS_STRATEGY.md`, `CUSTOMER_RESEARCH.md`, `COMPETITOR_ANALYSIS.md`, `GROWTH_STRATEGY.md`, and `BUSINESS_EXPERIMENTS.md`.
- [x] 6. Harmonize `docs/MONETIZATION.md`, `docs/PRODUCT_STRATEGY.md`, `docs/GO_TO_MARKET.md`, and `docs/SAAS_ROADMAP.md` so zero pricing or strategy contradictions exist, test `saas-business-advisor` on 3 real decisions, and archive progress.

## Files Expected to Change

- `.agents/skills/{pricing,customer-research,competitor-profiling,cro,paywalls,ab-testing}/**`
- `.agents/skills/saas-business-advisor/SKILL.md`
- `.agents/skills/SOURCES.lock.json`, `.agents/skills/README.md`
- `.agents/product-marketing.md`, `.agents/AGENTS.md`
- `docs/business/{BUSINESS_STRATEGY,PRICING,UNIT_ECONOMICS,CUSTOMER_RESEARCH,COMPETITOR_ANALYSIS,GROWTH_STRATEGY,BUSINESS_EXPERIMENTS}.md`
- `docs/{MONETIZATION,PRODUCT_STRATEGY,GO_TO_MARKET,SAAS_ROADMAP}.md`, `docs/progress/stage-b-saas-business-partner-upgrade.md`, `TODO.md`

## Decisions and Assumptions

- Only pure Markdown (`SKILL.md`, `references/*.md`, and `LICENSE.txt`) is vendored from `coreyhaines31/marketingskills@17772c7a80b7` (`MIT`); `evals/evals.json`, `tools/integrations/*`, and all `.js`/`.py`/`.sh` files are omitted per workspace security policy.
- Official cloud/payment pricing verified on `2026-10-26`; USD-denominated API meters converted at `1 USD = €0.92` (`[ASSUMPTION]`), and German B2C gross prices account for `19%` MwSt (`Net = Gross / 1.19`).

## Blockers

- None

## Verification

- [x] All 22 workspace skills in `.agents/skills/` pass YAML frontmatter, directory-name match, line-count (`<= 500`), zero-script, and `SOURCES.lock.json` SHA-256 verification (`173` locked files)
- [x] `.agents/AGENTS.md` verified `< 22,000` bytes (`14,391` bytes)
- [x] Financial tables in `docs/business/UNIT_ECONOMICS.md` verified mathematically across all 7 user scales × 3 scenarios, with zero broken relative links across `docs/business/*`
