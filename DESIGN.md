# DESIGN.md — AI Form Assistant Design System ("Warm Civic Daylight — Paper & Ink")

## 1. Design Identity & Philosophy

**Product Archetype**: Universal Multilingual Civic & Administrative Document Studio  
**Aesthetic Direction**: **Warm Civic Daylight (Paper & Ink)** — inspired by official paper documents, modern European/International civic portals, Stripe Press clarity, and Notion/Linear typographic precision.

### Core Principles
1. **Paper-First Trust & Legibility**: Administrative forms require calm, high-contrast daylight surfaces (`#f8fafc` warm paper canvas, `#ffffff` pure crisp document sheets, `#0f172a` deep ink text) so applicants feel confident and never intimidated.
2. **Flag-Free Universal Language Representation**: Languages are never tied to a single country flag. Every language is represented by its **ISO 639-1 code** (`EN`, `DE`, `FR`, `AR`, `ES`, `TR`, `UK`, `FA`, `UR`, etc.), its **native script name** (`العربية`, `Deutsch`, `Français`, `فارسی`, `Українська`), its English reference name, and an explicit `RTL` indicator when right-to-left.
3. **3-Dimensional Document Taxonomy & Visual PDF Previews**: When selecting a form manually, users filter by:
   - **Document Language** (`sourceLanguage` / `supportedOutputLanguages`)
   - **Document Category** (Civil & Municipal Registration, Residence & Housing, Family & Social Benefits, Employment & Tax, Legal Declarations)
   - **Issuing Country / Authority** (`INT`, `DE`, `FR`, `MA`, `EU`)
   Each form card includes a **miniature PDF sheet preview** displaying the official form code, simulated section blocks, field count, and signature box indicator.

---

## 2. Color Tokens

| Token | Value | Purpose |
| :--- | :--- | :--- |
| `--bg-canvas` | `#f8fafc` | Warm alabaster paper background |
| `--bg-surface-1` | `#ffffff` | Primary document sheet / panel surface |
| `--bg-surface-2` | `#f1f5f9` | Secondary muted card / filter bar surface |
| `--bg-surface-3` | `#e2e8f0` | Control group / subtle divider fill |
| `--border-subtle` | `#e2e8f0` | Hairline card and table borders |
| `--border-strong` | `#cbd5e1` | Input and interactive control borders |
| `--text-primary` | `#0f172a` | Deep ink headings and primary values |
| `--text-secondary` | `#334155` | Body copy and form labels |
| `--text-muted` | `#64748b` | Metadata, helper text, and captions |
| `--accent-primary` | `#4f46e5` | Civic Indigo primary interactive accent |
| `--accent-primary-hover` | `#4338ca` | Primary button hover state |
| `--status-success` | `#059669` | Confirmed answers & ready-for-export badges |
| `--status-warning` | `#d97706` | Clarification prompts & manual signature notices |
| `--status-danger` | `#e11d48` | Validation errors & required indicators |
