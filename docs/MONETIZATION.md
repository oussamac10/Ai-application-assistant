# AI Form Assistant — Monetization, Pricing & Unit Economics

## 1. Pricing Psychology & Market Fit

Administrative form completion has a distinct purchasing dynamic compared to daily productivity SaaS:

1. **High Acute Urgency, Episodic Frequency (B2C)**:
   - An expat or newcomer moving to Germany faces an immediate, high-stress cluster of `4–8` bureaucratic forms in their first 90 days (`Anmeldung`, `Wohnungsgeberbestätigung`, health insurance registration, `Kindergeld`, `SEPA` mandates, Kita/school enrollment), followed by `2–4` forms per year.
   - Pure monthly subscriptions (`EUR 20/mo`) create **subscription fatigue and high churn** for episodic B2C users, whereas **Free Guided Preview + Low-Friction Pay-Per-Form (`EUR 5.90`) or a Newcomer 5-Form Pack (`EUR 19.90`)** matches exact willingness-to-pay at the moment of peak relief — costing **90% less** than a EUR 60–150 human translator/consultant appointment.
2. **High-Frequency, Predictable Recurring Volume (B2B2C)**:
   - Relocation agencies, international HR onboarding teams, and funded migrant counseling associations (`Vereine` / Wohlfahrtsverbände) process `30–300+` client forms every month. They gladly pay **`EUR 89–229 / month`** for a branded portal (`/org/[slug]`) that saves `25–45 minutes` of bilingual counselor time per client.

---

## 2. Evaluation of Candidate Monetization Models

| Model | Conversion Friction | Revenue Predictability | Fit for B2C Newcomers | Fit for Agencies / Associations | Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **A. B2C Subscription Only** | High (users resist recurring billing for 1 urgent PDF) | Medium (high Month-1 cancellation) | Poor | Moderate | **Reject as sole B2C gate** |
| **B. Transactional Pay-Per-Form Only** | Very Low (impulse buy when PDF preview looks right) | Low (one-off spikes) | Excellent | Poor (expense-report friction) | **Keep as B2C entry tier** |
| **C. Hybrid: Free Preview + Single Pass + Multi-Form Pack + Pro/Org Subscriptions** | **Very Low** ("Aha!" moment happens before paywall) | **High** (packs boost AOV 3.4x; B2B2C builds MRR) | **Excellent** | **Excellent** | **Selected Architecture** |
| **D. Usage-Based B2B API** | High (long integration cycle, enterprise sales) | High at scale | None | Low initially | **Defer until >EUR 5k MRR** |

---

## 3. Production Pricing Architecture

All tiers use **EUR** as primary currency (with automatic Stripe multi-currency display where applicable) and include **19% German MwSt / EU VAT** handling via **Stripe Tax**.

| Tier | Price | Included Entitlements | Target Buyer & Upgrade Trigger |
| :--- | :--- | :--- | :--- |
| **Free Guided Preview** | **EUR 0** | - Upload any PDF (up to 10 pages) or select predefined form<br/>- Automatic language & field detection<br/>- Complete first **3 guided questions** in `userLanguage` with plain-language explanations<br/>- Watermarked Page-1 visual preview showing answers placed on the form | Eliminates cold-start skepticism; proves the assistant actually understands the user's PDF before asking for payment. |
| **Single Form Pass** | **EUR 5.90** *(one-time)* | - Unlock full guided question flow for **1 form session**<br/>- Unlimited edits & re-downloads of the clean, unwatermarked completed PDF for **7 days**<br/>- Personalized Final Submission & Attachment Checklist | Urgent one-off user (e.g., needs `Wohnungsgeberbestätigung` or `Anmeldung` tonight). |
| **Newcomer Pack (5 Forms)** *(Default Highlighted Option)* | **EUR 19.90** *(one-time, EUR 3.98/form)* | - **5 full form credits** valid for **12 months**<br/>- **Reusable Personal Profile Vault** enabled (1-click pre-fill of name, birth date, address, IBAN, passport country across all 5 forms)<br/>- Persistent saved applications dashboard | Newly arrived expat, international student, or family completing relocation paperwork (`3.4x` higher upfront cash flow than Single Pass). |
| **Household / Pro Monthly** | **EUR 12.90 / month** | - **15 completed form exports / month**<br/>- Reusable Personal Profile Vault (up to 4 family members in Phase `S4+`)<br/>- Priority Hybrid OCR & AI processing | Power users, freelance community helpers, and multi-person households. |
| **Organization Starter Portal** | **EUR 89 / month** *(or EUR 890 / yr)* | - **50 completed client forms / month**<br/>- Dedicated branded `/org/[slug]` Document Portal with custom logo & pre-uploaded official PDFs<br/>- Up to **3 counselor/staff seats** | Boutique relocation agencies, international university welcome desks, local migrant `Vereine`. |
| **Organization Growth Portal** | **EUR 229 / month** *(or EUR 2,290 / yr)* | - **200 completed client forms / month** (`EUR 0.90` per extra form)<br/>- Unlimited portal templates + **10 staff seats**<br/>- Organization usage & compliance audit log export | Mid-size relocation firms, employers hiring international talent, regional integration centers. |

---

## 4. Week-2 Pre-Stripe Pricing Validation Smoke Test

Before spending engineering days building full subscription lifecycle management, run a **48-hour Fake-Door / Early-Access Checkout Smoke Test** in Week 2 (`Phase S2` kick-off):

1. Show the watermarking preview card on the Summary screen with the 3 B2C options (`EUR 5.90 Single`, `EUR 19.90 5-Pack`, `EUR 12.90/mo`).
2. Record anonymous aggregate conversion events (`preview_viewed -> unlock_clicked -> tier_selected`) with zero PII.
3. **Success Criterion**:
   - **`>= 5%` click-through to checkout** from users who complete 3+ fields validates pricing immediately.
   - **`>= 35%` selection share on the `EUR 19.90` Newcomer Pack** confirms bundle anchor positioning.

---

## 5. Per-Document Unit Economics & Gross Margin

Because the architecture uses **local-first PyMuPDF detection**, **approved reusable question catalogs**, and **deterministic validation**, paid cloud AI/OCR calls occur only on uncached/ambiguous fields and scanned pages:

| Cost Component (Average 3-Page Form, 22 Fields) | Provider & Rate | Blended Usage Assumption | Avg Cost / Completed Form |
| :--- | :--- | :--- | :--- |
| **Field Detection** | Local PyMuPDF (`75%` of PDFs = `EUR 0.00`) + Azure Doc Intelligence Layout (`25%` scanned escalation @ `~EUR 0.009/page`) | `0.75 * 0 + 0.25 * 3 * 0.009` | **EUR 0.0068** |
| **Label & Option Translation** | Catalog cache hit (`45%` = `EUR 0.00`) + Azure Translator (`~1,200` uncached chars @ `EUR 9.30 / 1M chars`) | `1,200 * 0.0000093` | **EUR 0.0112** |
| **Free-Text Extraction & Clarification** | Vertex AI Gemini 2.5 Flash (`europe-west3`) on ~6 non-deterministic fields (`~4,500` input + `~900` output tokens) | Blended Flash token cost | **EUR 0.0045** |
| **PDF Rendering & Object Storage** | Local PyMuPDF/pypdf + EU S3 (`~450 KB` stored 7–30 days) | Compute + S3 negligible | **EUR 0.0045** |
| **Total AI + Cloud Variable COGS / Form** | | | **~EUR 0.027 / form** |

### Payment Processing Overhead (Stripe EU)
- **Single Form Pass (`EUR 5.90` gross -> `EUR 4.96` net of 19% VAT)**:
  - Stripe EU standard card/Apple Pay/SEPA fee (`1.5% + EUR 0.25`): **`EUR 0.34`**
  - AI/OCR variable COGS: **`EUR 0.027`**
  - **Net Contribution Margin per Single Form**: **`EUR 4.59` (`92.5%` net margin after Stripe & AI COGS!)**
- **Newcomer 5-Form Pack (`EUR 19.90` gross -> `EUR 16.72` net of 19% VAT)**:
  - Stripe EU fee (`1.5% + EUR 0.25`): **`EUR 0.55`** (`3.3%` effective fee vs `6.9%` on micro-ticket!)
  - AI/OCR variable COGS (assuming 4.0 of 5 credits used): **`EUR 0.11`**
  - **Net Contribution Margin per 5-Pack**: **`EUR 16.06` (`96.0%` net margin!)**

---

## 6. Realistic Revenue Projections & Break-Even Analysis

### 6.1 Fixed Infrastructure Baseline (Solo Developer)
- Hetzner Cloud `CPX31` (`EUR 16.50`) + Hetzner EU Object Storage & Backups (`EUR 5.50`) + Domain/Email (`EUR 4.00`) + Sentry/Monitoring free-tier + Baseline AI/Staging buffer (`EUR 32.00`) = **`~EUR 58 / month` total fixed burn**.
- **Break-Even Point**:
  - **Just `13` Single Form Passes (`EUR 5.90`) per month**, OR
  - **Just `4` Newcomer Packs (`EUR 19.90`) per month**, OR
  - **Just `1` Organization Starter Portal (`EUR 89/mo`)** makes the entire business cash-flow positive!

### 6.2 Customer Milestone Revenue Table (Net Monthly Revenue in EUR, Excl. VAT)

Assumptions across milestones:
- **Conservative**: `70%` B2C Single Pass (`EUR 4.96` net), `25%` B2C 5-Pack (`EUR 16.72` net), `5%` Pro (`EUR 10.84/mo` net), `0–2%` Orgs.
- **Base (Hybrid B2C + Agency Portals)**: `45%` Single Pass, `35%` 5-Pack, `15%` Pro Monthly, `5%` Org Starter/Growth (`EUR 89–229/mo`).
- **Optimistic (Strong B2B2C Agency/Association Mix)**: `30%` Single Pass, `35%` 5-Pack, `20%` Pro Monthly, `15%` Org Starter/Growth (`blended EUR 135/mo` org ARPU).

| Paying Customers / Month | Conservative Net Revenue / Mo | Base Case Net Revenue / Mo | Optimistic Net Revenue / Mo | Est. Infra + AI + Stripe Costs (Base) | Net Solo Founder Profit / Mo (Base) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **10 Customers** | EUR 79 | **EUR 142** | EUR 295 | EUR 68 | **+EUR 74** *(Break-even achieved)* |
| **50 Customers** | EUR 395 | **EUR 760** | EUR 1,540 | EUR 115 | **+EUR 645** |
| **100 Customers** | EUR 790 | **EUR 1,590** | EUR 3,180 | EUR 185 | **+EUR 1,405** |
| **500 Customers** | EUR 3,950 | **EUR 8,250** | EUR 16,400 | EUR 710 | **+EUR 7,540** |
| **1,000 Customers** | EUR 7,900 | **EUR 16,800** | EUR 33,500 | EUR 1,390 | **+EUR 15,410** |
