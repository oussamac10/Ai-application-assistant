# Business & Growth Experiment Backlog

**Last Updated:** 2026-10-26  
**Owner:** Growth Strategist / CFO (`ab-testing` + `pricing` + `cro` + `saas-business-advisor`)  
**Statistical Discipline Rule (`ab-testing` skill):** Do **not** run classical 50/50 split A/B tests when weekly traffic is `< 500` sessions per variant (underpowered tests produce false positives). Use **structured qualitative interviews, fake-door intent thresholds, and sequential cohort comparisons** first; graduate to randomized split tests only once traffic supports `>= 80%` statistical power.

---

## 1. Prioritized Experiment Matrix (ICE Scored)

*ICE Score = `(Impact × Confidence × Ease) / 10` on a 1–10 scale.*

| ID | Experiment Name | Funnel / Business Risk Tested | Method | Cash Cost | Duration | ICE | Status |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: | :--- |
| **`EXP-01`** | **Newcomer Mom-Test + Van Westendorp WTP (`n = 15`)** | Will newcomers pay `€4.99` / `€16.99`, and which 5 forms hurt most? | 15-min live silent demo + 4 Van Westendorp questions | `€0` | `5 days` | **81.0** | **Next Up (P0)** |
| **`EXP-02`** | **Watermarked Preview Paywall Smoke Test (`Single` vs `5-Pack` vs `Monthly`)** | Real click-to-pay conversion & pack attachment rate before overbuilding billing tiers | Summary Studio paywall modal telemetry (`>= 100` preview views) | `€0` | `7–10 days` | **72.9** | **Planned (`S3-01`)** |
| **`EXP-03`** | **Relocation Consultant & *Verein* Loom Pilot Test (`50` Outreaches -> `10` Calls)** | Will solo consultants pay `€39/mo` & agencies pay `€99/mo` for `/p/[orgSlug]`? | 60s personalized Loom + concierge pilot LOI before coding `Phase S5` | `€0` | `10 days` | **72.0** | **Next Up (P0)** |
| **`EXP-04`** | **1-Click Sample Template vs. Blank Upload Hero Dropzone** | Cold visitors hesitate to upload private PDFs before trusting the tool | Cohort comparison on homepage (`>= 300` visitors) | `€0` | `10 days` | **64.0** | **Planned (`S3-02`)** |
| **`EXP-05`** | **Post-Export `€12.00` "Upgrade Single Pass to 5-Pack" Offer** | `€4.99` buyers realize 3 days later they also need *Kindergeld* & *Krankenkasse* | In-app + transactional receipt banner within 14 days of `€4.99` purchase | `€0` | `14 days` | **57.6** | **Planned (`S4`)** |
| **`EXP-06`** | **Top-5 Bilingual "Form Rescue" SEO Pages (`ar, en, tr, uk`)** | Can organic form-name searches drive `< €1` CAC high-intent sessions? | Publish 20 localized static pages (`5 forms × 4 languages`) + Search Console tracking | `€0` | `30 days` | **56.0** | **Planned (`S3/S7`)** |
| **`EXP-07`** | **Price Point Elasticity Test (`€4.99 / €16.99` vs. `€5.90 / €19.90`)** | Reconcile `€4.99/€16.99` vs earlier `€5.90/€19.90` net revenue per visitor | Randomized Stripe Checkout price test **only after `>= 600` preview sessions** | `€0` | `21 days` | **44.8** | **Gated on Traffic** |
| **`EXP-08`** | **1-for-1 Free Form Credit Referral Prompt at Clean PDF Download** | Can peak-relief newcomer word-of-mouth drive `< €0.10` CAC viral loops? | Post-download referral link (`+1` export credit on friend completion) | `< €5` API | `30 days` | **43.2** | **Planned (`Post-S4`)** |

---

## 2. Detailed Experiment Specifications (`Pass / Pivot / Kill` Criteria)

### `EXP-01` — Newcomer Problem & Willingness-to-Pay Discovery (`n = 15`)
- **Hypothesis:** *If we watch 15 newcomers in Germany (`<= 12` months in country, speaking `ar, en, tr, uk, fr`) complete a real German form in the Dual-Pane Verification Studio, then `>= 10/15` will complete the flow without human hints, their Van Westendorp optimal price point for 1 form will fall between `€4.50` and `€6.50`, and `>= 6/15` will prefer the `€16.99` 5-Document Relocation Pack over a `€12.99/mo` recurring subscription because they dislike auto-renewing subscriptions.*
- **Execution:** Recruit from Berlin/Munich/NRW expat & student groups (`r/germany`, Telegram/Facebook newcomer groups, university welcome desks) using Script A in [`CUSTOMER_RESEARCH.md`](CUSTOMER_RESEARCH.md).
- **Decision Thresholds:**
  - **Pass:** `>= 60%` unassisted completion + median acceptable single-doc price `>= €4.50` + `>= 35%` preference for `€16.99` 5-Pack -> Lock `€4.99` / `€16.99` / `€12.99` for `Phase S4` Stripe launch.
  - **Pivot:** Users love the output but strongly resist `€4.99` for short 1-page forms (e.g., *Wohnungsgeberbestätigung*) -> Make 1-page *Wohnungsgeberbestätigung* a free watermarked/lead-magnet hook that upsells the `€16.99` 5-Form Relocation Pack for multi-page *Anmeldung* / *Kindergeld*.
  - **Kill / Redesign UX:** `< 50%` understand the Dual-Pane Verification Studio without explanation -> Fix UX clarity in `Phase S3` before spending time on Stripe billing.

---

### `EXP-02` — Watermarked Preview Paywall Smoke Test (`n >= 100` Completed Previews)
- **Hypothesis:** *If anonymous users complete `>= 3` guided questions and inspect their watermarked German PDF preview before seeing any price, then `>= 8%` of preview viewers will click to unlock the clean PDF, and `>= 35%` of unlock clicks will select the highlighted `€16.99` 5-Document Relocation Pack over the `€4.99` Single Pass.*
- **Metrics Recorded (Zero PII):** `session_started` -> `preview_rendered` -> `paywall_opened` -> `plan_selected (single_499 | pack_1699 | personal_1299)`.
- **Decision Thresholds:**
  - **Pass (`>= 8%` preview-to-checkout click, `>= 30%` pack share):** Proceed immediately with `S4-02` Stripe Checkout + `credit_ledger`.
  - **Pivot (`< 4%` preview-to-checkout click):** Inspect drop-off — either the watermark hides too much of the PDF (users cannot verify accuracy) or cold visitors are testing toy uploads rather than real German forms.

---

### `EXP-03` — B2B2C Relocation Consultant & *Verein* Concierge Pilot (`50` Looms -> `10` Calls)
- **Hypothesis:** *If we send 50 personalized 60-second Loom demos to boutique German relocation consultants (`25`) and migrant counseling associations/international HR desks (`25`), then `>= 10` will book a 15-minute workflow call and `>= 2` will commit to a paid `€39/mo` (solo) or `€99/mo` (Organization Portal) 30-day pilot.*
- **Why This Gates `Phase S5` (`5` Dev Days):** Per [`BUSINESS_STRATEGY.md`](BUSINESS_STRATEGY.md) Decision Test 2, we **refuse to build multi-tenant `organizations` tables blind**.
- **Decision Thresholds:**
  - **Pass (`>= 2` paid pilot commitments at `€39–€99/mo`):** Build `Phase S5` (`/p/[orgSlug]` + `/org/[slug]/admin`) immediately.
  - **Pivot (Consultants want to fill forms *themselves* on calls rather than sending links to clients):** Skip public `/p/[orgSlug]` portal complexity and ship the 1.5-day **`€39/mo` Solo Professional Mode** (`client_ref` isolated sessions) first!
  - **Defer B2B (`0` replies/commitments after `50` targeted Looms):** Focus 100% on self-serve B2C SEO + `€16.99` Relocation Packs until organic inbound arrives.

---

### `EXP-04` — Homepage Instant Sample Form vs. Upload-Only Hero (`n >= 300` Visitors)
- **Hypothesis:** *If the homepage offers 1-click "Try Official Wohnungsgeberbestätigung / Anmeldung Now (No Upload Needed)" buttons directly beside the PDF/photo upload dropzone, then `visitor -> Question 1` activation will exceed `25%` (`1.6×` higher than upload-only), because mobile visitors on social/search links often do not have the blank PDF saved on their phone yet.*
- **Pass Criterion:** `>= 25%` visitor-to-Question-1 start rate and `>= 15%` of sample-template starters completing the full preview.

---

### `EXP-05` — Post-Purchase "Apply Your `€4.99` Toward the `€16.99` 5-Pack" (`+€12.00` Upsell)
- **Hypothesis:** *If `€4.99` Single Document buyers see a 1-click post-export banner ("Need Anmeldung, Kindergeld, or Krankenkasse next? Upgrade to the 5-Document Pack + 1-Click Profile Vault for just `€12.00` more within 14 days"), then `>= 18%` of Single Pass buyers will upgrade — lifting realized B2C net revenue per customer by `+€2.10` without penalizing first-purchase impulse conversion.*
- **Unit-Economics Guardrail:** Charge `+€12.00` gross (`€10.08` net ex-VAT, `-€0.52` second Stripe fee = `+€9.56` net margin on `4` extra credits costing `<= €0.06` API COGS).

---

## 3. Experiment Hygiene Log Template

Whenever an experiment completes, append a 6-line record below (never overwrite failed experiments — failed hypotheses save months of wasted engineering):

```markdown
### [EXP-ID] — Completed YYYY-MM-DD
- **Sample Size & Window:** e.g., n = 16 interviews (2026-11-01 to 2026-11-06)
- **Observed Result:** Exact numbers vs. threshold
- **Decision Taken:** Pass / Pivot / Kill
- **Docs Updated:** Link to PRICING.md / UNIT_ECONOMICS.md / SAAS_ROADMAP.md diff
```
