# Customer Research, Segmentation & Discovery Playbook

**Last Updated:** 2026-10-26  
**Owner:** Growth Strategist / CPO (`customer-research` + `saas-business-advisor`)  
**Geographic Beachhead:** **Germany** (expanding later to Austria/Switzerland and France/Belgium only after German PMF).

---

## 1. Validated Facts vs. Unvalidated Customer Hypotheses

| Statement | Classification | Source / How to Validate |
| :--- | :--- | :--- |
| Germany has substantial ongoing administrative PDF friction across municipal registration (*Anmeldung*), housing (*Wohnungsgeberbestätigung*, *Mieterselbstauskunft*), family benefits (*Kindergeld*, *Elterngeld*), and social/health insurance (*Krankenkasse*). | **Market Fact** | Official German federal/municipal PDF workflows (`bmi.bund.de`, `arbeitsagentur.de`) still require German-language form submission or signed paper/PDF handoffs in most municipalities. |
| Foreign-born residents, international students, and refugees in Germany frequently rely on Facebook/Telegram groups, friends, *Migrationsberatung*, or paid consultants to decode German compound bureaucratic terms. | **Market Observation** | Daily recurring posts in `r/germany`, `r/berlinsocialclub`, and Arabic/Turkish/Ukrainian newcomer communities in Germany. |
| Self-serve newcomers will pay `€4.99` for 1 clean PDF export or `€16.99` for a 5-Document Relocation Pack after seeing a watermarked preview. | **`[HYPOTHESIS]`** | Test via `EXP-01` (15 interviews + Van Westendorp) & `EXP-02` (checkout smoke test). |
| Boutique relocation consultants & *Migrantenvereine* will pay `€39–€99/mo` to save 30+ minutes of bilingual form intake per client. | **`[HYPOTHESIS]`** | Test via `EXP-03` (50 personalized Loom outreach messages -> 10 discovery calls). |

---

## 2. Evaluation of All 6 Candidate Customer Segments

| Segment | Core Bureaucratic Pain | Frequency per Buyer | Ability & Willingness to Pay (`[HYPOTHESIS]`) | Acquisition Cost & Reachability (Solo Dev) | Verdict & Role |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Skilled Immigrants & Expat Families (B2C)** | Must complete `5–9` high-stakes German forms in first 90 days (*Anmeldung*, *Wohnungsgeberbestätigung*, *Steuer-ID*, *Krankenkasse*, *Kindergeld*, *Kita*, *SEPA*) with fear of delays or benefit loss. | **Clustered burst** (`5–9` forms in Months 1–3, then `2–3/yr`) | **Medium–High** for `€4.99` Single & **`€16.99` 5-Pack** (`90%` cheaper than a `€120` consultant). High churn on monthly subs. | **High reachability** via bilingual form-specific SEO & expat communities (`€0` ad spend). | **Primary B2C Beachhead (#1A)** |
| **2. International University Students (B2C)** | Semester arrival burst (*Anmeldung*, dorm *Wohnungsgeberbestätigung*, *Krankenkasse* exemption/enrollment, *Rundfunkbeitrag*, blocked-account/SEPA forms). | **Seasonal spikes** (Sept–Nov & Mar–Apr; `3–5` forms) | **Low–Moderate** (price-sensitive; strong fit for `€4.99` single pass or student referral credits, weak fit for `€12.99/mo`). | **Very easy concentration** via university *ASTA* / *Akademisches Auslandsamt* / WhatsApp semester groups. | **Secondary Viral / Referral Funnel** |
| **3. Corporate Expatriates (B2C)** | Same arrival paperwork + housing/school/insurance forms, higher income, zero patience for German bureaucracy. | **Episodic** (`4–7` forms on arrival) | **High** (`€16.99` 5-Pack or `€79/yr` Personal Annual without hesitation — often expensed). | Moderate via English expat forums, LinkedIn, international tech communities in Berlin/Munich. | **High-AOV B2C Segment** |
| **4. Boutique Relocation Agencies & Freelance Consultants (B2B2C)** | Manually collect client passport/address data via email/WhatsApp and copy-paste into the same 10 German PDFs 20–150 times/month. | **Daily / Weekly recurring** (`20–200` forms/mo) | **High & Recurring** (`€39/mo` solo Pro; **`€99/mo` Agency Portal**) — saves `€15–€40` of labor per client! | **Direct outbound reachable** (`< 300` boutique agencies in Germany on LinkedIn/Google Maps). | **Primary Recurring MRR Beachhead (#1B)** |
| **5. Administrative Support Services, Sworn Translators & *Migrantenvereine e.V.* (B2B2C)** | Overwhelmed counselors/helpers spending scarce appointment minutes writing basic names/dates/addresses onto routine forms. | **Daily recurring** (`30–300` forms/mo) | **Medium–High** (`€39/mo` freelance helpers; `€99/mo` funded *Vereine* / *Wohlfahrtsverbände*, though non-profits have slower grant approval). | Reachable via local city directories (*Migrationsberatung für erwachsene Zuwanderer*). | **Strong Partner & Trust Channel** |
| **6. Businesses Hiring International Employees (B2B HR)** | HR/People Ops teams onboarding non-EU engineers, nurses, hospitality, or logistics hires (*Anmeldung*, health insurance, tax questionnaire, bank/SEPA). | **Recurring per hire** (`5–50` hires/yr) | **High** (`€99/mo` Business Portal), **but** requires stricter GDPR/infosec vendor review than solo consultants. | Reachable via international healthcare/nursing recruiters & Berlin/Munich startup People Ops leads. | **Phase-2 Expansion (`Month 3+`)** |

---

## 3. Selected Initial Beachhead Niche (Where We Win First)

Do **not** launch horizontally as *"AI PDF filler for the world."* Launch on a **two-sided German Relocation Wedge**:

1. **Self-Serve B2C Cash & Validation Engine:** Newly arrived **Arabic (`ar`), English (`en`), Turkish (`tr`), Ukrainian (`uk`), and French (`fr`) speakers in Germany** searching in crisis for how to fill out **`Wohnungsgeberbestätigung`**, **`Anmeldung`**, **`Kindergeld (KG1 + Anlage Kind)`**, **`Mieterselbstauskunft`**, and **`Krankenkasse` member forms** -> monetized immediately via the **`€4.99` Single Document** and **`€16.99` 5-Document Relocation Pack**.
2. **Recurring B2B2C MRR Engine:** **Solo & boutique German relocation consultants (`1–10` staff)** onboarding skilled workers and nurses -> monetized at **`€39/mo` (Professional)** and **`€99/mo` (Organization Portal)**.

**Why this dual wedge beats single-segment alternatives:** Every B2C SEO guide ranks for the exact forms relocation consultants also hate filling manually, and every consultant sharing `/p/[orgSlug]` proves product-market fit across dozens of real documents per month without paid B2C ad spend.

---

## 4. Core Jobs-to-be-Done (JTBD) & Anxiety Map

- **Functional JTBD:** *"When an authority, landlord, or employer in Germany gives me an official German PDF with unfamiliar compound words, help me understand every box in my native language, check that my dates/IBAN/postal code are formatted properly, and give me back the official German PDF cleanly filled and ready to sign."*
- **Emotional JTBD:** *"Eliminate the fear that one misunderstood German checkbox will get my apartment application rejected, delay my city registration, or freeze my Kindergeld payment."*
- **Top 4 Buying Anxieties We Must Neutralize on Every Screen:**
  1. *"Will the Bürgeramt accept this PDF?"* -> **Proof:** Dual-Pane Verification Studio shows the **exact original official PDF** with clean typography, never an altered layout.
  2. *"Is my passport/IBAN data safe or sold to AI models?"* -> **Proof:** EU hosting, Fernet encryption at rest, zero-PII deterministic local validation for IBAN/dates/emails, and 1-click GDPR hard delete.
  3. *"What if I spot a typo after printing?"* -> **Proof:** Free 7-day unlimited typo edits & re-downloads included on every `€4.99` Single Document unlock.
  4. *"Am I getting trapped in a sneaky subscription?"* -> **Proof:** Default B2C options (`€4.99` Single & `€16.99` 5-Pack) are **one-time payments with zero auto-renewal**.

---

## 5. Mom-Test Customer Interview & WTP Scripts (Ready to Run)

Follow the [`customer-research`](../../.agents/skills/customer-research/SKILL.md) rule: **never pitch your AI product in the first 10 minutes — interrogate past behavior, wasted money, and failed workarounds.**

### 5.1 Script A — Newcomer / Expat / Student in Germany (`15 minutes`, Target `n = 15`)
1. **Past Context:** *"Tell me about the last official German form you had to fill out. Which form was it, and when did you receive it?"*
2. **Actual Workaround:** *"Step by step, how did you translate it and get your answers onto the page? Did you use Google Translate, ChatGPT, a friend, or print it out?"*
3. **Pain Spike:** *"Which specific question or box made you stop and worry you might write the wrong thing?"*
4. **Consequence / Past Spend:** *"Have you ever had a German form rejected, delayed, or paid someone to help fill it out? What did that cost you in time or Euros?"*
5. **Live Silent Demo (`3 mins`):** Watch them upload or pick *Anmeldung* / *Kindergeld*, answer 3 questions in their native language, and view the Dual-Pane Verification Studio (say nothing while they click!).
6. **Van Westendorp + Tier Choice (`pricing` skill):**
   - *"At what price for unlocking this finished, print-ready PDF would it feel so cheap you'd question its quality?"*
   - *"At what price would it feel like a great deal?"*
   - *"At what price does it start feeling expensive, though you'd still consider paying on an urgent deadline?"*
   - *"At what price is it too expensive to ever use?"*
   - *"If you arrived in Germany last week knowing you had 5 forms ahead of you, which of these three options would you actually pick right now: `€4.99` for just this 1 PDF, `€16.99` one-time for 5 PDFs + 1-click auto-fill, or `€12.99/month`?"*

### 5.2 Script B — Relocation Consultant / *Verein* Caseworker (`15 minutes`, Target `n = 10`)
1. **Current Intake Workflow:** *"Walk me through what happens from the moment a new international hire/family signs with you to the moment their Anmeldung, Wohnungsgeberbestätigung, and Krankenkasse PDFs are ready."*
2. **Time & Error Cost:** *"How many minutes per client do you or your staff spend chasing missing fields, translating German boxes, or re-typing passport/address details into PDFs?"*
3. **Top-5 Forms Inventory:** *"Which 5 exact PDF documents account for 80% of your repetitive client paperwork?"*
4. **Software Budget & Privacy Bar:** *"What tools do you currently pay for every month (`€30–€200/mo`) to run client onboarding, and what GDPR/data rules do your corporate HR clients require?"*
5. **Pilot Commitment Test:** *"If we pre-loaded your top 5 official PDFs into a private EU-hosted link where your clients answer in Arabic/English/Turkish on their phone and you download the clean German PDF in 2 minutes, would you pilot that next week at `€39/mo` (solo) or `€99/mo` (agency portal)?"*
