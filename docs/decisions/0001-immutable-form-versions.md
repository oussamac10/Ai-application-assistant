# ADR 0001: Immutable Form Versions

## Status
Approved

## Context
In our multilingual form assistant application, users fill out forms using potentially outdated versions of a form. If a form version gets modified after it is published, users' previously saved answers may become invalid or refer to deleted/modified fields. To prevent silent corruption of active user sessions, we need a robust approach to form updates.

## Decision
We will enforce complete **immutability** on published or archived form versions:
1. When a form template version status transitions to `published`, it becomes read-only.
2. Any API or service request to create, update, or delete fields, options, or translations on a published/archived version must be rejected immediately with an HTTP `409 Conflict`.
3. To update a published form version, the user must **clone** the version.
4. Cloning a version creates a brand-new, independent version record in `draft` status, incrementing the version number. This new draft can then be edited freely and eventually published.

## Consequences
- Active form filling sessions will never experience field changes or deletion while in progress, as they are pinned to a specific immutable form version.
- Allows audits and historic record-keeping of exactly how a form was structured when a user completed it.
- Editing published forms requires an explicit clone and publish workflow, which prevents accidental modification of live forms.
