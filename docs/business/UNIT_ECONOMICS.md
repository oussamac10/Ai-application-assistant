# Unit Economics, Cloud Cost Model & API Optimization Playbook

**Last Updated:** 2026-10-26  
**Owner:** CFO / Principal Architect (`saas-business-advisor`)  
**Status:** Verified Provider Rates (`2026-10-26`); Demand & Conversion Inputs Marked `[ASSUMPTION]`

---

## 1. Accounting Principles & Fact-vs-Assumption Separation

1. **Gross Customer Payments != Net Revenue (EU VAT Discipline):**
   - B2C prices in Germany include **19% MwSt (VAT)**: `Net Revenue = Gross Payment / 1.19` (e.g., `€4.99` gross = **`€4.19` net revenue** + `€0.80` VAT remitted to *Finanzamt*).
   - Stripe percentage fees are charged on the **Gross Customer Payment** (`€4.99`), not the net ex-VAT figure — ignoring this inflates unit margins by ~`19%`.
2. **Gemini Antigravity != Deployed Gemini API Billing:**
   - Developer IDE sessions in **Gemini Antigravity** do not reflect production runtime billing.
   - Deployed runtime calls (`backend/app/ai/gemini_provider.py` -> `generativelanguage.googleapis.com/v1beta`) are billed per 1M input/output tokens via Google Cloud Billing. Under the [Gemini API Additional Terms of Service](https://ai.google.dev/gemini-api/terms) (Effective March 23, 2026), **only Paid Services** may be used when serving users in the EEA, Switzerland, or the UK.
3. **MRR Purity:**
   - **MRR / ARR** counts **only recurring subscriptions** (`Personal €12.99/mo`, `Professional €39/mo`, `Business €99/mo`). One-time passes (`€4.99` Single Doc, `€16.99` 5-Doc Pack) are tracked separately as **Transactional Net Revenue**.
4. **Free-Tier Funnel Drag Included:**
   - Variable AI/API COGS explicitly includes **non-paying active users** who upload a form, run guided Q&A, and inspect the watermarked preview without buying.

---

## 2. Verified Official Provider Pricing (`2026-10-26`)

*(USD-denominated API meters converted at `1 USD = €0.92` `[ASSUMPTION]`.)*

| Cost Category | Service / Meter | Verified Official Rate (`2026-10-26`) | Fixed vs. Variable | Source & Date |
| :--- | :--- | :--- | :--- | :--- |
| **AI Extraction / Q&A** | `gemini-2.5-flash-lite` (Paid Tier) | **\$0.10 / 1M input**, **\$0.40 / 1M output** (`€0.092 / €0.368`) | Variable | [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing) (`2026-10-26`) |
| **AI Extraction / Q&A** | `gemini-3.1-flash-lite` (Paid Tier) | **\$0.25 / 1M input**, **\$1.50 / 1M output** (`€0.23 / €1.38`) | Variable | [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing) (`2026-10-26`) |
| **AI Extraction / Q&A** | `gemini-3.5-flash-lite` & `gemini-2.5-flash` | **\$0.30 / 1M input**, **\$2.50 / 1M output** (`€0.276 / €2.30`) | Variable | [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing) (`2026-10-26`) |
| **AI Complex Fallback** | `gemini-3.6-flash` / `gemini-3.8-flash` | **\$0.75 / 1M input**, **\$3.75 / 1M output** *(doubles Jan 1, 2027 to \$1.50/\$7.50)* | Variable | [ai.google.dev/gemini-api/docs/pricing](https://ai.google.dev/gemini-api/docs/pricing) (`2026-10-26`) |
| **Document Detection** | Azure Doc Intelligence `S0 Read` (`germanywestcentral`) | **\$1.50 / 1,000 pages** (`€0.00138 / page`) | Variable | [Azure Document Intelligence Pricing](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/) (`2026-10-26`) |
| **Document Detection** | Azure Doc Intelligence `S0 Layout` (`prebuilt-layout`) | **\$10.00 / 1,000 pages** (`€0.00920 / page`; `F0` 500p free capped at 2p/PDF) | Variable | [Azure Document Intelligence Pricing](https://azure.microsoft.com/en-us/pricing/details/document-intelligence/) (`2026-10-26`) |
| **Label Translation** | Azure AI Translator (`F0` / `S1`) | **`F0`: 2M chars/mo €0**; **`S1`: \$10.00 / 1M chars** (`€0.0092 / 1k chars`) | Step-Variable | [Azure Translator Pricing](https://azure.microsoft.com/en-us/pricing/details/translator/) (`2026-10-26`) |
| **Local OCR & PDF** | `PyMuPDF` (`fitz`) + `pytesseract` + `pypdf` | **€0.00 external API fee** (runs on Hetzner worker vCPU) | Absorbed in Infra | Codebase (`backend/app/ocr/`, `app/pdf/`) |
| **App & Worker VPS** | Hetzner Cloud Germany (`CX23` / `CX33`, Falkenstein/Nuremberg) | `CX23` (2 vCPU/4GB): **€5.49/mo**; `CX33` (4 vCPU/8GB): **€8.49/mo** (ex-VAT) | Step-Fixed | [hetzner.com/cloud](https://www.hetzner.com/cloud/) (`2026-10-26`) |
| **Object Storage & Backups** | Hetzner S3 Object Storage (FSN1/NBG1) + VM Backups | **€6.49/mo base** (includes **1 TB storage + 1 TB egress**); VM Backups `+20%` | Step-Fixed | [hetzner.com/storage/object-storage](https://www.hetzner.com/storage/object-storage/) (`2026-10-26`) |
| **Email & Monitoring** | Postmark EU Transactional Email + Sentry EU | Postmark: **\$15/mo (`€13.80`)** for 10k emails (100/mo dev free); Sentry Dev `€0` -> Team `€26/mo` | Step-Fixed | Official vendor pricing (`2026-10-26`) |
| **Payment Processing** | Stripe Germany (Cards + Billing + Tax) | EEA standard: **`1.5% + €0.25`**; Non-EEA newcomer cards: **`3.15% + €0.25`**; Billing: **`0.7%`**; Tax: **`0.5%`** | Variable | [stripe.com/en-de/pricing](https://stripe.com/en-de/pricing) (`2026-10-26`) |

---

## 3. Infrastructure & Fixed Overhead Step-Ladder

| Registered Users Tier | Hosting (App + Worker) | Database + Redis | S3 Storage + Backups | Monitoring + Email + Domain/LB | Support Tooling + German Bookkeeping | Total Fixed Infra (`COGS`) | Total Fixed Admin (`OpEx`) | Combined Monthly Fixed Floor |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **10 – 50 users** | `€8.49` (`1× CX33`) | `€0.00` (co-hosted) | `€8.19` (`€6.49 + €1.70`) | `€1.50` (free email/Sentry dev) | `€18.00` (Lexoffice starter) | **`€18.18`** | **`€18.00`** | **`€36.18 / mo`** |
| **100 users** | `€8.49` (`1× CX33`) | `€0.00` (co-hosted) | `€8.19` | `€15.30` (Postmark `€13.80` + domain) | `€18.00` | **`€31.98`** | **`€18.00`** | **`€49.98 / mo`** |
| **500 – 1,000 users** | `€8.49` (`1× CX33`) | `€8.49` (`1× CX33` DB/Worker) | `€9.89` (`€6.49 + €3.40`) | `€15.30` | `€83.00` (`€19` helpdesk + `€64` accounting) | **`€42.17`** | **`€83.00`** | **`€125.17 / mo`** |
| **5,000 users** | `€16.98` (`2× CX33`) | `€15.49` (`CX43` 16GB) | `€12.99` (`€6.49 + €6.50`) | `€50.89` (Sentry `€26` + Postmark `€18` + LB `€5.39` + domain) | `€169.00` (`€29` helpdesk + `€140` *Steuerberater*) | **`€96.35`** | **`€169.00`** | **`€265.35 / mo`** |
| **10,000 users** | `€33.96` (`4× CX33`) | `€30.98` (Primary + Standby) | `€22.50` (`€9.50 + €13.00`) | `€102.49` (Sentry/Logs `€45` + Postmark 50k `€50.60` + LB/domain) | `€269.00` (`€49` helpdesk + `€220` *Steuerberater*) | **`€189.93`** | **`€269.00`** | **`€458.93 / mo`** |

---

## 4. Scenario Assumptions (`[ASSUMPTION]` Register)

All user-behavior, conversion, card-mix, and churn parameters below are **explicit planning assumptions** until validated by `EXP-01`–`EXP-04` in [`BUSINESS_EXPERIMENTS.md`](BUSINESS_EXPERIMENTS.md):

| Input Parameter `[ASSUMPTION]` | Conservative Stress Case | Base Case (Target) | Optimistic Case |
| :--- | :--- | :--- | :--- |
| **MAU % of Registered Users** | `30%` | `38%` | `45%` |
| **Monthly Paid Conversion (% of MAU)** | `6.0%` (`1.8%` of reg) | `10.0%` (`3.8%` of reg) | `14.0%` (`6.3%` of reg) |
| **Payer Tier Mix (`€4.99` / `€16.99 Pack` / `€12.99` / `€39` / `€99`)** | `55% / 15% / 22% / 6% / 2%` | `38% / 27% / 20% / 10% / 5%` | `28% / 30% / 20% / 14% / 8%` |
| **Fields Calling Gemini (% of Form Fields)** | `80%` *(unoptimized today)* | `35%` *(deterministic bypass)* | `28%` *(bypass + Vault pre-fill)* |
| **Gemini Model Routing** | `100%` `3.5-flash-lite` (`\$0.30/\$2.50`) | `80%` `2.5-flash-lite` + `20%` `2.5-flash` | `85%` `2.5-flash-lite` + `15%` `2.5-flash` |
| **Retry / Repair Multiplier** | `1.18×` (`18%` overhead) | `1.08×` (`8%` overhead) | `1.05×` (`5%` overhead) |
| **Azure Escalation Rate (Paid / Free Docs)** | `35%` paid / `20%` free (`Layout \$10/1k`) | `18%` paid / `5%` free (`Layout \$10/1k`) | `10%` paid / `0%` free (blended `Read/Layout \$6.50/1k`) |
| **Non-EEA Card Share (Newcomer Cards)** | `60%` (`2.49% + €0.25` blended card) | `45%` (`2.24% + €0.25` blended card) | `35%` (`2.08% + €0.25` blended card) |
| **Refund & Chargeback Reserve (% Net Rev)** | `4.0%` | `2.5%` | `1.5%` |
| **Monthly Subscription Churn (Personal / Pro / Biz)** | `32%` / `12%` / `7%` | `22%` / `8%` / `5%` | `15%` / `6%` / `3.5%` |
| **Blended CAC per New Paying Customer** | `€14.00` (`65%` new/mo) | `€9.50` (`45%` new/mo) | `€6.00` (`35%` new/mo) |

---

## 5. Multi-Scale Financial Projections (`10` -> `10,000` Registered Users)

### 5.1 Base-Case Projection (Optimized Pipeline + 5-Doc Pack + Early B2B2C Mix)

| Reg. Users | Active Users (MAU) | Paying Subs | One-Time Buyers | Total Docs (Paid / Free) | Gross Payments (incl. VAT) | Net Revenue (ex-VAT) | Net MRR (`ARR`) | Fixed Infra | AI & APIs (`€/doc`) | Stripe + Billing + Tax | Contrib. Margin (`%`) | SaaS Gross Margin | CAC + Refunds + Admin + Sup. | Monthly Operating Profit |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **10** | `3.8` | `0.2` | `0.3` | `8.5` (`5.2 / 3.3`) | `€9.55` | `€8.02` | `€5.23` (`€63`) | `€18.18` | `€0.06` (`€0.0072`) | `€0.43` | `€7.10` (`88.5%`) | `-132.8%` | `€20.61` | **`-€31.26`** |
| **50** | `19.0` | `0.7` | `1.2` | `34.3` (`17.2 / 17.1`) | `€34.50` | `€28.99` | `€18.69` (`€224`) | `€18.18` | `€0.23` (`€0.0066`) | `€1.58` | `€25.61` (`88.3%`) | `31.1%` | `€27.70` | **`-€18.69`** |
| **100** | `38.0` | `1.3` | `2.5` | `67.9` (`33.7 / 34.2`) | `€68.19` | `€57.30` | `€36.56` (`€439`) | `€31.98` | `€0.45` (`€0.0066`) | `€3.12` | `€50.59` (`88.3%`) | `38.0%` | `€37.39` | **`-€15.64`** |
| **500** | `190.0` | `6.7` | `12.3` | `343.3` (`172.3 / 171.0`) | `€345.04` | `€289.95` | `€186.94` (`€2,243`) | `€42.17` | `€2.28` (`€0.0066`) | `€15.77` | `€256.11` (`88.3%`) | `79.2%` | `€180.03` | **`+€49.71`** |
| **1,000** | `380.0` | `13.3` | `24.7` | `679.1` (`337.1 / 342.0`) | `€681.88` | `€573.01` | `€365.57` (`€4,387`) | `€42.17` | `€4.49` (`€0.0066`) | `€31.25` | `€505.85` (`88.3%`) | `86.4%` | `€276.87` | **`+€218.23`** |
| **5,000** | `1,900.0` | `66.5` | `123.5` | `3,394.9` (`1,684.9 / 1,710.0`) | `€3,406.98` | `€2,863.01` | `€1,827.83` (`€21,934`) | `€96.35` | `€47.72` (`€0.0141`*) | `€156.16` | `€2,502.05` (`87.4%`) | `89.5%` | `€1,138.33` | **`+€1,424.45`** |
| **10,000** | `3,800.0` | `133.0` | `247.0` | `6,789.8` (`3,369.8 / 3,420.0`) | `€6,813.97` | `€5,726.03` | `€3,655.66` (`€43,868`) | `€189.93` | `€95.44` (`€0.0141`*) | `€312.32` | `€5,004.11` (`87.4%`) | `89.6%` | `€2,207.66` | **`+€2,920.68`** |

*\*Note on the `€0.0066 -> €0.0141/doc` step at `5,000` users: Total monthly translated characters cross Azure Translator's `2,000,000` char/month `F0` free tier, activating `S1` pay-as-you-go (`\$10 / 1M chars`).*

### 5.2 Conservative Stress Case (Unoptimized Pipeline + `€4.99`-Heavy Mix + High Churn)

| Reg. Users | MAU | Paying Subs | One-Time Buyers | Gross Payments | Net Revenue (ex-VAT) | Net MRR (`ARR`) | Fixed Infra + Admin | AI & APIs (`€/doc`) | Stripe Fees | Contrib. Margin | SaaS Gross Margin | Monthly CAC Spend | Monthly Operating Profit |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **10** | `3.0` | `0.1` | `0.3` | `€6.18` | `€5.19` | `€3.02` (`€36`) | `€36.18` | `€0.25` (`€0.0440`) | `€0.33` | `80.4%` | `-261.6%` | `€4.55` | **`-€36.56`** |
| **50** | `15.0` | `0.3` | `0.6` | `€11.18` | `€9.40` | `€5.49` (`€66`) | `€36.18` | `€0.87` (`€0.0419`) | `€0.60` | `76.0%` | `-109.2%` | `€8.10` | **`-€37.13`** |
| **100** | `30.0` | `0.6` | `1.3` | `€22.97` | `€19.31` | `€11.30` (`€136`) | `€49.98` | `€1.76` (`€0.0420`) | `€1.23` | `76.3%` | `-81.2%` | `€16.47` | **`-€51.73`** |
| **500** | `150.0` | `2.7` | `6.3` | `€112.32` | `€94.38` | `€54.86` (`€658`) | `€125.17` | `€8.73` (`€0.0419`) | `€6.07` | `76.0%` | `39.6%` | `€81.90` | **`-€135.31`** |
| **1,000** | `300.0` | `5.5` | `12.6` | `€229.73` | `€193.05` | `€112.99` (`€1,356`) | `€125.17` | `€17.59` (`€0.0420`) | `€12.34` | `76.3%` | `62.7%` | `€164.71` | **`-€142.62`** |
| **5,000** | `1,500.0` | `27.0` | `63.0` | `€1,122.37` | `€943.17` | `€542.86` (`€6,514`) | `€265.35` | `€86.95` (`€0.0419`) | `€60.58` | `76.1%` | `74.1%` | `€819.00` | **`-€366.94`** |
| **10,000** | `3,000.0` | `54.0` | `126.0` | `€2,244.74` | `€1,886.34` | `€1,085.72` (`€13,029`) | `€458.93` | `€173.90` (`€0.0419`) | `€121.16` | `76.1%` | `74.3%` | `€1,638.00` | **`-€662.10`** |

> [!WARNING]
> **Critical CFO Lesson from the Conservative Table:** Even with `76%` contribution margin, a business where `55%` of buyers purchase only a `€4.99` single pass (`€3.80` net after VAT & Stripe) while spending `€14.00` CAC per new buyer **loses money at every scale (`-€662/mo` at 10,000 users)**. Paid ads for `€4.99` single-form buyers are **strictly forbidden** — B2C acquisition must come from organic SEO/referrals/communities, and checkout must anchor users on the **`€16.99` 5-Document Pack** while founder outreach builds **`€39–€99/mo` Pro/Business** accounts.

### 5.3 Optimistic Case (Strong Template Reuse + Organic SEO + Agency Portal Traction)

| Reg. Users | MAU | Paying Subs | One-Time Buyers | Gross Payments | Net Revenue (ex-VAT) | Net MRR (`ARR`) | Fixed Infra + Admin | AI & APIs (`€/doc`) | Stripe Fees | Contrib. Margin | SaaS Gross Margin | Monthly CAC Spend | Monthly Operating Profit |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **10** | `4.5` | `0.3` | `0.4` | `€14.27` | `€12.00` | `€8.53` (`€102`) | `€36.18` | `€0.03` (`€0.0026`) | `€0.60` | `90.9%` | `-56.8%` | `€1.34` | **`-€26.62`** |
| **50** | `22.5` | `1.3` | `1.8` | `€70.63` | `€59.35` | `€42.10` (`€505`) | `€36.18` | `€0.14` (`€0.0026`) | `€2.96` | `90.9%` | `64.2%` | `€6.61` | **`+€11.15`** |
| **100** | `45.0` | `2.6` | `3.6` | `€141.08` | `€118.56` | `€84.19` (`€1,010`) | `€49.98` | `€0.27` (`€0.0026`) | `€5.91` | `90.9%` | `67.8%` | `€13.21` | **`+€44.57`** |
| **500** | `225.0` | `13.2` | `18.3` | `€706.25` | `€593.49` | `€420.96` (`€5,051`) | `€125.17` | `€1.36` (`€0.0026`) | `€29.59` | `90.9%` | `87.7%` | `€66.15` | **`+€348.14`** |
| **1,000** | `450.0` | `26.4` | `36.5` | `€1,410.81` | `€1,185.55` | `€841.91` (`€10,103`) | `€125.17` | `€2.73` (`€0.0026`) | `€59.10` | `90.9%` | `91.2%` | `€132.09` | **`+€820.38`** |
| **5,000** | `2,250.0` | `132.3` | `182.7` | `€7,078.74` | `€5,948.52` | `€4,229.47` (`€50,754`) | `€265.35` | `€36.88` (`€0.0069`) | `€296.44` | `90.5%` | `92.8%` | `€661.50` | **`+€4,457.38`** |
| **10,000** | `4,500.0` | `264.6` | `365.4` | `€14,157.49` | `€11,897.05` | `€8,458.94` (`€101,507`) | `€458.93` | `€73.75` (`€0.0069`) | `€592.87` | `90.5%` | `92.8%` | `€1,323.00` | **`+€8,986.54`** |

---

## 6. Summary Unit-Economics KPIs Across Scenarios

| KPI | Conservative | Base Case | Optimistic |
| :--- | ---: | ---: | ---: |
| **Pure Variable API Cost / Processed Document** | `€0.0419` | **`€0.0066 – €0.0141`** | `€0.0026 – €0.0069` |
| **Fully-Loaded API Cost / *Paid* Document (incl. Free Funnel)** | `€0.1616 – €0.1663` | **`€0.0132 – €0.0283`** | `€0.0038 – €0.0103` |
| **Net Revenue per Paying Customer (`ARPPU` ex-VAT)** | `€10.48 / mo` | **`€15.07 / mo`** | `€18.88 / mo` |
| **Contribution Margin (`%` of Net Revenue)** | `76.1%` | **`87.4% – 88.3%`** | `90.5% – 90.9%` |
| **Blended Customer Lifetime Value (`LTV`, margin-adjusted)** | `€48.44` | **`€130.22`** | `€267.26` |
| **Blended `LTV : CAC` Ratio** | `3.5×` | **`13.7×`** | `44.5×` |
| **Break-Even Paying Customers (`<= 1,000` user infra floor `€125/mo`)** | `16` payers (pre-CAC) / Never post-CAC | **`10` payers (`14` incl. CAC)** | `8` payers (`9` incl. CAC) |

---

## 7. AI & Microsoft API Cost-Optimization Evaluation (12 Levers)

Every optimization was evaluated against **document correctness** and **GDPR privacy** — we never cut costs by guessing user data or weakening validation:

| # | Optimization Lever | Codebase Status Today | Est. Savings on API COGS | Accuracy Impact | Privacy Impact | Decision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Deterministic AI Bypass for `email`, `phone`, `iban`, `integer`/`decimal`, ISO/EU `date`, & same-script proper nouns** | **Missing!** Only `choice`, `boolean`, `signature` bypass [`AnswerService.submit_answer`](../../backend/app/answers/services.py) | **`-55%` to `-65%` Gemini calls** | **Improves accuracy** (zero digit/character LLM mangling) | **Major upgrade** (fixes mismatch with [`docs/privacy.md`](../privacy.md) L106!) | **Build Now (`S4-01`)** |
| **2** | **Seed `PDFFingerprintRegistry` for Top 10–20 Official German Forms** (*Anmeldung*, *Wohnungsgeberbestätigung*, *Kindergeld*, *SEPA*) | Mechanism built ([`registry.py`](../../backend/app/documents/registry.py)), **only 1 demo fingerprint registered** | **`-100%` Azure & translation COGS** on matched uploads | **Improves accuracy** (human-verified field coordinates) | **Major upgrade** (zero 3rd-party transfer) | **Build Now (`S3-03`)** |
| **3** | **Skip Azure When Local Extraction Is Reliable (`HybridFieldDetectionProvider`)** | Built ([`hybrid.py`](../../backend/app/field_detection/providers/hybrid.py)) using arithmetic quality `< 0.55` & coverage floor | **`-70%` to `-85%` Azure pages** vs. always-Azure | **Neutral/Safe** (returns local if Azure scores lower) | **Positive** (digital PDFs stay 100% local) | **Enable for Paid/Preview (`<= 5p` anon, `<= 15p` paid)** |
| **4** | **Route Simple Extraction & Batch Label Translation to `gemini-2.5-flash-lite` (`\$0.10/\$0.40`) or `3.1-flash-lite`** | Currently `gemini-3.5-flash-lite` (`\$0.30/\$2.50`) in Docker; broken `gemini-3.5-flash` in `config.py` | **`-67%` input / `-84%` output token cost** | **Safe** for structured JSON schema tasks (verify via eval fixtures) | Neutral | **Build Now (`S4-01`)** |
| **5** | **Reserve Stronger Flash Model (`gemini-2.5-flash` / `3.6-flash`) Only for Ambiguous Free-Text Clarifications** | Single static model today | Keeps 80%+ calls on Lite tier | **Preserves accuracy** on nuanced multilingual prose | Neutral | **Build Now (`S4-01`)** |
| **6** | **Cache Non-Personal Catalog & Label Translations** (`QuestionTranslation` DB + LRU `_cache`) | **Already Implemented** ([`translation/service.py`](../../backend/app/translation/service.py) 8-step pipeline + `protected.py`) | **`-50%` to `-90%` repeat label chars** | Neutral | **Safe** (caches blank form labels only, **never** user answers; keep `AIResponseCache` off for PII!) | **Keep Active** |
| **7** | **Batch Translation Calls & Deduplicate Repeated Labels** | **Already Implemented** (`AI_TRANSLATION_BATCH_SIZE` + `dict.fromkeys` dedup) | **`-85%` HTTP/system-prompt overhead** | Neutral | Safe | **Keep Active** |
| **8** | **Avoid Repeated Document Extraction (Idempotent Session & Detection Reuse)** | **Already Implemented** ([`orchestration.py`](../../backend/app/field_detection/orchestration.py) reuses completed detection/sessions) | Eliminates double-billing on browser refresh | Neutral | Safe | **Keep Active** |
| **9** | **Capture `usageMetadata` Tokens + Persist Per-Document Cost (`ai_usage_events`)** | **Missing!** [`GeminiAIProvider._post`](../../backend/app/ai/gemini_provider.py) drops `usageMetadata`; `estimated_cost=NULL` | Prevents silent margin leaks | Neutral | Safe (counts & costs only, zero PII) | **Build Now (`S4-01`)** |
| **10** | **Bounded Retries (`max_retries=2` + max `1` JSON repair retry)** | **Already Implemented** in `GeminiAIProvider` & `AzureTranslatorProvider` | Caps worst-case failure cost at `<= 3×` | Preserves reliability | Safe | **Keep Active (never raise `max_retries > 2`)** |
| **11** | **Endpoint Rate Limiting on `submit_answer` + Per-Session Spend Cap (`€0.25`) + Plan Quotas** | Upload/prepare/auth rate-limited; **`submit_answer` rate limit & `€0.25` cap missing** | Eliminates bot wallet-drain risk | Neutral for real humans | Safe | **Build Now (`S4-01`)** |
| **12** | **Automated Cloud Billing & Internal Daily Spend Alerts (`€5/day`, `€50/mo` early thresholds)** | Not configured yet | Caps catastrophic runaway spend | Neutral | Safe | **Configure Before Public Launch (`S6`)** |
