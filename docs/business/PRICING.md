# SaaS Monetization & Pricing Architecture

**Last Updated:** 2026-10-26  
**Owner:** CPO / CFO (`saas-business-advisor` + `pricing` skill)  
**Validation Status:** `[HYPOTHESIS]` — All price points require validation via `EXP-01` & `EXP-02` ([`BUSINESS_EXPERIMENTS.md`](BUSINESS_EXPERIMENTS.md)) before locking long-term contracts.

---

## 1. Core Monetization Philosophy: "Experience Clarity First, Pay for Clean Submission"

Immigrants, international students, and relocation clients do not trust black-box paywalls before knowing whether an AI tool actually understands their official German PDF.

Our highest-trust, highest-converting value gate (`paywalls` *"Value Before Ask"* pattern) is:
1. **Free Value Proof (Strictly Cost-Bounded):** Upload 1 document (`<= 5` pages on local extraction) -> complete the guided Q&A in your native language -> inspect the **4-column Dual-Pane Verification Studio** and **watermarked PDF preview**.
2. **Paid Unlock Moment:** Pay to export the **clean, unwatermarked, print-and-submission-ready official PDF** (with 7-day unlimited typo fixes/re-exports on that document), or unlock multi-document credits + **1-Click Encrypted Profile Vault Pre-Fill** for future forms.

---

## 2. Comparison of All 8 Monetization Models

| Monetization Model | Target Buyer | Commercial Pros | Structural Cons / Risks | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **1. Pay-Per-Document (`€4.99`)** | Urgent 1-off newcomer (*Wohnungsgeberbestätigung*, *Anmeldung*) | Zero subscription anxiety; highest first-time conversion rate. | Low AOV (`€4.19` net ex-VAT -> `€3.80` after Stripe); **cannot fund paid ads**. | **Adopt as Entry Impulse Hook** |
| **2. Credit Packages (`€16.99` / 5 Forms)** | Newly arrived immigrant/student/family facing 4–7 forms in 90 days | Matches real *episodic* newcomer journey; **`3.4×` AOV** on a single Stripe `€0.25` fixed fee; zero monthly churn resentment. | Recognized as transactional revenue rather than MRR; requires `credit_ledger` expiry rules (`12 months`). | **Adopt as Primary B2C Anchor** |
| **3. Monthly Subscription (`€12.99/mo`)** | Heavy individual/household filers (*Bürgergeld*, *Elterngeld*, ongoing letters) | Predictable self-serve MRR; pairs naturally with Encrypted Profile Vault. | High structural B2C churn (`22%–35%/mo` `[ASSUMPTION]`) once initial arrival paperwork finishes. | **Adopt (with Clear Fair-Use Cap)** |
| **4. Annual Subscription (`€79/yr` Personal, `€390/yr` Pro)** | Expat families & solo relocation/admin consultants | Eliminates monthly B2C churn; collects 12 months cash upfront on 1 Stripe fee. | Harder impulse sell on Day 1 than `€4.99` or `€16.99` pack (best offered as post-first-export upsell). | **Adopt (`2 months free` vs. monthly)** |
| **5. Professional Plan (`€39/mo`)** | Solo relocation consultants, social workers, freelance admin helpers | **High-margin bridge tier (`91%+` margin)**; recurring multi-client need (`20–50 docs/mo`); low churn (`6%–10%/mo` `[ASSUMPTION]`). | Needs lightweight client-session separation / labeling so Vault entries don't mix across clients. | **Adopt (Validate in `EXP-03`)** |
| **6. Business / Organization Portal (`€99/mo`)** | Relocation agencies, international HR desks, *Migrantenvereine e.V.* | Strongest B2B2C MRR engine; distributes `/p/[orgSlug]` link to dozens of end-applicants at `€0` B2C CAC! | Requires multi-tenant `organizations` + `/p/[orgSlug]` portal (`Phase S5`, ~5 dev days). | **Adopt After 10 Agency Interviews** |
| **7. Public REST API Access** | HRIS / PropTech / GovTech platforms | High theoretical volume at scale. | Requires API keys, versioned public docs, webhook SLAs, sandbox support, and security reviews — fatal distraction for a solo founder at `€0` MRR. | **Defer Until `>= €5k MRR`** |
| **8. White-Label Solutions** | Enterprise relocation firms / municipalities | High ACV (`€300–€1,000+/mo`). | Custom domains, CSS theming, custom DPAs, and **`PyMuPDF` AGPL-3.0 commercial licensing** risk. | **Defer / Reject Pre-PMF** |

---

## 3. Unit-Level Tier Breakdown (`[HYPOTHESIS]` Pricing Table)

*Accounting basis: German 19% VAT (`Net = Gross / 1.19`), blended Stripe fee (`2.24% + €0.25` assuming 55% EEA / 45% non-EEA cards + `0.5%` Stripe Tax + `0.7%` Stripe Billing on subscriptions), and optimized Base-Case variable API COGS (`€0.014/doc` incl. Azure hybrid escalation).*

| Plan (`[HYPOTHESIS]`) | Gross Price | Net Revenue (ex-VAT) | Included Allowance & Page Limits | Stripe + Billing + Tax | Max Expected API COGS (at Avg Usage) | Net Contribution (`€` / `%`) | Target Customer |
| :--- | ---: | ---: | :--- | ---: | ---: | ---: | :--- |
| **Free Preview** | `€0.00` | `€0.00` | `1` active form, `<= 5` pages, local detection, **watermarked preview only** | `€0.00` | `€0.007` | `-€0.007` *(funnel cost)* | First-time skeptical visitor |
| **Single Document** | **`€4.99`** | `€4.19` | **`1` clean PDF export** (+ 7-day typo re-exports), `<= 10` pages | `€0.39` | `€0.02` (`1.2` docs) | **`€3.78` (`90.2%`)** | Urgent 1-form filer (*Anmeldung*) |
| **5-Doc Relocation Pack** *(Recommended B2C Highlight)* | **`€16.99`** | `€14.28` | **`5` clean PDF exports** (valid 12 mo) + Vault 1-click pre-fill, `<= 15` pages/doc | `€0.72` | `€0.07` (`5.0` docs) | **`€13.49` (`94.5%`)** | Newcomer / student / family arriving in Germany |
| **Personal Monthly** | **`€12.99 / mo`** | `€10.92` | **`15` docs/mo**, `<= 15` pages/doc, Encrypted Profile Vault + Document History | `€0.70` | `€0.07` (`4.5` avg / `€0.21` max) | **`€10.15` (`92.9%`)** | Active expat household |
| **Personal Annual** | **`€79.00 / yr`** | `€66.39` | **`100` docs/yr**, `<= 15` pages/doc, Vault + 1-year encrypted document archive | `€2.97` | `€0.35` (`25` docs/yr) | **`€63.07` (`95.0%`)** | Long-term expat resident |
| **Professional** | **`€39.00 / mo`** | `€32.77` | **`50` client docs/mo**, `<= 25` pages/doc, separate client sessions (no Vault bleed) | `€1.59` | `€0.31` (`22` avg / `€0.70` max) | **`€30.87` (`94.2%`)** | Solo relocation consultant, translator, social worker |
| **Business / Portal** | **`€99.00 / mo`** *(or `€99 + VAT` B2B)* | `€83.19` *(`€99.00` if ex-VAT)* | **`200` docs/mo**, `<= 30` pages/doc, branded `/p/[orgSlug]` intake portal + org admin studio | `€3.65` | `€1.12` (`80` avg / `€2.80` max) | **`€78.42` (`94.3%`)** | Relocation agency (2–10 staff), employer HR, *Verein e.V.* |

### Reconciling Earlier `docs/MONETIZATION.md` Hypotheses
Earlier planning in [`docs/MONETIZATION.md`](../MONETIZATION.md) proposed `€5.90` Single / `€19.90` 5-Pack / `€12.90/mo` Pro / `€89–€229/mo` Org Portals. Rather than guessing between `€4.99` vs `€5.90` or `€16.99` vs `€19.90`, **both sit inside the same profitable `>90%` contribution-margin band** — we will test price elasticity empirically in **`EXP-02`** once baseline checkout conversion is measured. Crucially, adding the **`€39/mo` Professional** tier closes the gap between `€12.99` individuals and `€99` multi-client organizations.

---

## 4. Abuse Prevention & Margin Protection Rules

1. **Never Offer "Unlimited" AI/Azure Processing:** Every plan has an explicit monthly document cap (`15 / 50 / 200`) and per-document page cap (`10 / 15 / 25 / 30`) so a single `€12.99` account can never run an automated 5,000-document agency operation on your Azure/Gemini bill.
2. **Per-Session Spend Circuit Breaker (`€0.25`):** Even if a user edits answers 50 times in a session, `ai_usage_events` switches the session to deterministic-only validation once cumulative session API spend hits `€0.25`, guaranteeing positive unit margin on every single `€4.99` pass.
3. **Failed-Export Auto-Refund Credit:** If our PDF export or detection pipeline fails technically, automatically refund the `CreditLedgerEntry` (`+1`) without forcing the user to email support — protecting trust and preventing `€15` Stripe chargeback disputes.

---

## 5. Willingness-to-Pay (WTP) Validation Roadmap

Before writing complex subscription-tier branching, execute these three lean experiments (detailed in [`BUSINESS_EXPERIMENTS.md`](BUSINESS_EXPERIMENTS.md)):
1. **`EXP-01` — Van Westendorp + Pack-vs-Subscription Choice in 15 Newcomer Interviews (Days 1–5):** Ask the 4 Van Westendorp price-sensitivity questions after a live demo on a real German *Anmeldung* / *Kindergeld* PDF, then force a choice between `€4.99` Single, `€16.99` 5-Pack, and `€12.99/mo`.
2. **`EXP-02` — Fake-Door / Stripe Checkout Smoke Test (Days 5–10):** Measure actual click-to-checkout intent on the watermarked summary page across `Single (€4.99)` vs. `5-Pack (€16.99, pre-selected)` vs. `Personal (€12.99/mo)`.
3. **`EXP-03` — B2B Concierge Pilot Pitch (`€39` Pro vs. `€99` Agency Portal):** Pitch 25 boutique German relocation consultants and 25 *Migrantenvereine* via personalized 90-second Loom videos; validate whether solo consultants prefer `€39/mo` self-serve while agencies pay `€99/mo` for `/p/[orgSlug]`.
