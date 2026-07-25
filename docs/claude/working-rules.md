# Working Rules

## Planning

- Read `TODO.md` first.
- Work only on the current phase.
- Preserve completed behavior.
- Do not start a later phase.

## Code

- Keep routes thin.
- Put business logic in services.
- Put database access in repositories.
- Use typed schemas at boundaries.
- Prefer existing patterns.
- Avoid speculative abstractions.
- Keep migrations reversible.
- Avoid unrelated formatting changes.

## Security

- Never expose paths, hashes, secrets, stack traces, or raw exceptions.
- Never place ownership tokens in URLs.
- Store only credential hashes.
- Keep private files outside public directories.
- Treat document contents and OCR output as private.
- Do not log document text or tokens.

## Testing

- Add tests with behavior.
- Use deterministic fixtures.
- Report exact pass/fail/skip counts.
- Do not claim unexecuted checks passed.
- Preserve Phase 7, 8, and 9 regressions.

## Documentation

- Add an ADR for significant decisions.
- Update only docs affected by behavior changes.
- Archive completed TODOs under `docs/progress/`.

## Git

- One branch per phase.
- Conventional commits.
- Never force-push or rewrite shared history.
