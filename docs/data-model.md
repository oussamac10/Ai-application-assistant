# Data Model Summary

Persistence is managed via PostgreSQL 16, SQLAlchemy 2.0 repositories, and Alembic migrations (`backend/migrations/`).

## Key Domain Entities

- **Forms & Catalog**: `form_templates`, `form_versions` (`origin`: `predefined_template` vs `dynamic_detection`), `form_fields`, `question_definitions`, `question_translations`
- **Documents & Detection**: `source_documents`, `document_pages`, `ocr_results`, `field_detection_results`, `detected_fields`, `provider_usage_records`
- **Guided Sessions & Answers**: `form_sessions`, `form_answers`, `export_jobs`
- **Accounts & Security**: `users` (`role`: `user` | `org_admin` | `platform_admin`), `auth_sessions`

## Canonical References

- [Full Database Design, ER Diagram & SaaS Schema (`DATABASE_DESIGN.md`)](DATABASE_DESIGN.md)
- [Form Model](form-model.md)
- [Session Model](session-model.md)
- [Answer Model](answer-model.md)
- [User Accounts](user-accounts.md)
