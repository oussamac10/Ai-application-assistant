# Project Rules

## Context efficiency

- Use targeted searches and direct file reads.
- Do not dump full files into chat.
- Do not rescan unchanged directories.
- Prefer repository state over conversation summaries when they conflict.
- Keep plans and progress updates concise.

## Security and privacy

- Never expose internal storage paths, database IDs, credential hashes, secrets, stack traces, or raw exceptions.
- Never place ownership tokens in URLs.
- Store only secure token hashes.
- Treat uploaded documents, extracted text, and OCR output as private.
- Keep private files outside public directories.
- Never log document contents or raw credentials.
- Validate uploaded content independently from file extension and client MIME type.

## Code quality

- Follow existing naming and module structure.
- Use typed schemas at boundaries.
- Keep route handlers thin.
- Keep migrations reversible.
- Avoid unnecessary dependencies.
- Avoid unrelated formatting changes.
- Prefer deterministic fixtures and local providers in tests.

## Git safety

- One feature branch per phase.
- Use conventional commits.
- Never force-push or rewrite shared history.
- Do not delete branches or files without clear need.

## Response format

During work, provide brief status updates only when the task spans multiple tool calls.

At completion, report:

- implementation summary
- changed files or modules
- verification with exact results
- unresolved items
- next action
