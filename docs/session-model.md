# Form Session Model

This document outlines the design and attributes of the Form Session entity introduced in Phase 3.

## Entity Schema

```
                  +--------------------------------+
                  |          FormSession           |
                  +--------------------------------+
                  | - id: UUID (PK)                |
                  | - public_id: UUID (Unique)     |
                  | - ownership_token_hash: string |
                  | - form_version_id: UUID (FK)   |
                  | - user_language: string        |
                  | - source_language: string      |
                  | - output_language: string      |
                  | - status: string               |
                  | - current_field_position: int  |
                  | - total_required_fields: int   |
                  | - expires_at: datetime         |
                  | - created_at: datetime         |
                  | - updated_at: datetime         |
                  | - completed_at: datetime?      |
                  | - cancelled_at: datetime?      |
                  +--------------------------------+
```

### Table Properties

| Property | Type | Description |
| :--- | :--- | :--- |
| `id` | `String(36)` | Internal primary key (UUID v4). Used for database relations and indexing. |
| `public_id` | `String(36)` | External public identifier (UUID v4) exposed in URLs and client-facing API responses. |
| `ownership_token_hash` | `String(64)` | The HMAC-SHA256 hex digest of the cryptographically random token generated for session authorization. |
| `form_version_id` | `String(36)` | Foreign Key linking to `form_versions.id`. Restricts deletions to preserve session audit logs. |
| `user_language` | `String(10)` | ISO 639-1 code of the user language (used for questions and annotations). |
| `source_language` | `String(10)` | ISO 639-1 code of the form's native language, inherited automatically from the `FormVersion`. |
| `output_language` | `String(10)` | ISO 639-1 code of the targeted translation output language, validated against supported languages of the version. |
| `status` | `String(50)` | Current lifecycle state of the session (`session_created`, `in_progress`, `expired`, `cancelled`). |
| `current_field_position`| `Integer` | Current question index. Defaults to `0`. |
| `total_required_fields` | `Integer` | Count of required fields in the linked form version, calculated deterministically during creation. |
| `expires_at` | `DateTime` | Timezone-aware UTC timestamp when the session expires. |
| `created_at` | `DateTime` | Timezone-aware UTC timestamp when the session was created. |
| `updated_at` | `DateTime` | Timezone-aware UTC timestamp of the last database update. |
| `completed_at` | `DateTime` | Optional timestamp set when the session is finalized. |
| `cancelled_at` | `DateTime` | Optional timestamp set when the session is cancelled. |

## Verification Check Constraint Rules

- `ck_session_current_field_position`: `current_field_position >= 0`
- `ck_session_total_required_fields`: `total_required_fields >= 0`
