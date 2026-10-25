# Roadmap

Phase-by-phase plan. Completed phases are archived under `docs/progress/`; the active
phase is described in `docs/claude/current-phase.md`.

## Completed

| Phase | Title |
|---|---|
| 1 | Project Foundation |
| 2 | Form Definitions and Versioning |
| 3 | Temporary Anonymous Sessions |
| 4 | Mock Question and Answer Workflow |
| 5 | Local AI Integration with Ollama |
| 6 | Reusable Question Catalog and Hybrid Resolution |
| 7 | Frontend Guided Form Experience |
| 8 | PDF Template Mapping and Export |
| 9 | Form Upload and Document Analysis |
| 10 | OCR Integration |
| 11 | Dynamic Field Detection |
| 12 | User Accounts and Persistent Sessions |
| 13 | Automatic Upload-to-Questions User Flow |
| 14 | Azure Document Intelligence Provider |

## Planned

| Phase | Title | Notes |
|---|---|---|
| 15 | Hybrid Provider Fallback | Choose/combine local and Azure detection; Azure instead of OCR for scanned input |
| 16 | Administration and Content Review | Consumes the review metadata Phase 13/14 persist |
| 17 | Dynamic PDF Mapping, Filling, Preview, and Export | Export for arbitrary unknown PDFs |
| 18 | Plain-Language Field Explanations & Submission Checklist | Completed |
| 19 | Association & Organization Document Portals | Associations create their own space with their official documents; users browse an association's panel to pick and fill a document (`docs/association-document-portal.md`) |
| 20 | Security, Privacy, and Data Retention Hardening | |
| 19 | Background Jobs and Processing Queues | Makes orchestration asynchronous |
| 20 | Object Storage and Secure Downloads | |
| 21 | Production AI Provider Integration | |
| 22 | Payments and Subscription Plans | Defines real pricing for `provider_usage_records.estimated_cost` |
| 23 | Monitoring, Analytics, and Audit Logs | |
| 24 | Production Deployment and Release | |
