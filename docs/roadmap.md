# Roadmap

Completed foundation phases (`1–18`) are archived under `docs/progress/`. Active production SaaS transformation tasks (`Phases S0–S6`) are tracked in **[`docs/SAAS_ROADMAP.md`](SAAS_ROADMAP.md)**.

## Completed Foundation Phases (`1–18`)

| Phase | Title |
| :--- | :--- |
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
| 15 | Azure Translator Integration & Local Document-Language Detection |
| 16 | Three-State Requiredness & Hybrid Local-First Document Detection |
| 17 | Dynamic Coordinate-Overlay PDF Export, Live Form Highlighting & Voice Input |
| 18 | Plain-Language Field Explanations & Personalized Submission Checklist |

## Production SaaS Execution Phases (`S0–S6`)

See [`docs/SAAS_ROADMAP.md`](SAAS_ROADMAP.md) for ticket-level scope, files, tests, and completion criteria:

| Phase | Title | Focus |
| :--- | :--- | :--- |
| **S0** | P0 Security, Privacy & Production Blockers Remediation | Admin RBAC (`require_admin`), dynamic form catalog isolation, Gemini header auth, prod secret fail-fast, claimed document retention fix |
| **S1** | EU Cloud Storage, Async Processing & GDPR Compliance Hardening | S3-compatible EU object storage (`StorageProvider`), Vertex AI `europe-west3`, GDPR account erasure & export |
| **S2** | Monetization, Watermarked Free Preview & Stripe Billing | Free 3-question preview + watermarked Page-1 PDF, Single Pass (`EUR 5.90`), 5-Form Newcomer Pack (`EUR 19.90`), Pro (`EUR 12.90/mo`) |
| **S3** | Production PDF Quality, Font Coverage & AI Evaluation Harness | Full CJK/RTL/Latin font fallback, multi-page visual regression suite, golden multilingual AI benchmark |
| **S4** | Reusable Personal Profile Vault ("1-Click Pre-Fill") | Encrypted canonical profile (`personal.*`, `address.*`, `contact.*`) with explicit per-session review |
| **S5** | B2B2C Association & Relocation Agency Document Portals | Branded `/org/[slug]` portals (`docs/association-document-portal.md`), team seats, `EUR 89–229/mo` org plans |
| **S6** | Production Deployment, Monitoring & Launch GTM Execution | Hetzner DE + Caddy + CI/CD + encrypted 6h backups + Sentry EU + first 10 -> 100 paying customers |
