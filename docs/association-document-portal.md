# Association & Organization Document Portals (Planned Architecture)

## 1. Vision & Product Concept

Instead of a static "Select Manually" form picker on the main upload screen, associations, NGOs, housing providers, clubs, and community organizations will be able to create their own **Association Space / Portal** inside the application.

1. **Association Workspace Creation (Admin / Organization Side)**:
   - An association creates its own dedicated profile/panel in the app (with name, description, logo/badge, location, and contact details).
   - The association uploads and publishes the official PDF documents/forms that their members, tenants, or applicants need to complete (e.g., membership applications, housing confirmations, aid requests, registration forms).
   - When an association uploads a document template, the field mappings, questions, and approved translations are saved once for that association's document.

2. **Applicant Discovery & Completion Flow (User Side)**:
   - When a person needs to fill out a document for a specific association, they open the **Association Panel / Directory** in the app (or follow a direct link/QR code to that association's space).
   - They browse the documents published by that association, pick the document they need, choose their native `userLanguage`, and immediately start the guided one-question-at-a-time workflow.
   - Upon completion, the applicant reviews the summary and exports the filled official PDF (ready to print/sign or hand over to the association).

---

## 2. Core User Flows

### Flow A — Association Publishes a Form
```text
Association Admin signs in
→ creates or opens Association Space (e.g., "Stuttgart Mieterverein" or "Cultural Association e.V.")
→ uploads an official PDF form used by the association
→ reviews/confirms detected fields & questions once
→ publishes the document to the Association's public document list
```

### Flow B — Applicant Fills an Association Document
```text
User opens the App
→ navigates to "Associations" (or opens `/associations/{slug}`)
→ selects the Association
→ chooses the required document from the Association's published documents
→ selects their preferred userLanguage
→ answers questions step-by-step with plain-language explanations
→ confirms summary & downloads the completed PDF
```

---

## 3. Planned Domain Entities (Future Phase)

- `Association`:
  - `id` (UUID)
  - `slug` (unique URL-friendly identifier)
  - `name`
  - `description`
  - `country_code` / `city`
  - `owner_user_id`
  - `is_published`
  - `created_at` / `updated_at`
- `AssociationDocument` (links an `Association` to a published `FormTemplate` / `FormVersion` and its underlying `SourceDocument` PDF template):
  - `id` (UUID)
  - `association_id`
  - `form_template_id`
  - `published_version_id`
  - `category`
  - `visibility` (`public` | `unlisted` | `archived`)

---

## 4. Product & Privacy Boundaries

- All rules in `.agents/AGENTS.md` apply:
  - The app remains an assistant; it never auto-submits personal data to third parties without explicit user action.
  - Applicants retain full control over their session and final review confirmation before exporting the PDF.
  - Association admins manage blank document templates and questions — they do not automatically receive raw unconfirmed session answers unless an explicit submission/sharing consent flow is introduced in a future phase.
