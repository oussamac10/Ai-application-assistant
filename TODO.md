# TODO

## Completed Phases

Archived under `docs/progress/`:

1. Project Foundation
2. Form Definitions and Versioning
3. Temporary Anonymous Sessions
4. Mock Question and Answer Workflow
5. Local AI Integration with Ollama
6. Reusable Question Catalog and Hybrid Resolution
7. Frontend Guided Form Experience
8. PDF Template Mapping and Export
9. Form Upload and Document Analysis
10. OCR Integration
11. Dynamic Form Field Detection
12. User Accounts and Saved Applications
13. Automatic Upload-to-Questions User Flow
14. Azure Document Intelligence Provider
15. Azure Translator Integration
16. Hybrid Document Detection

## Current Task

**None. Phase 16 is complete and Phase 17 has not been started.**

Full Phase 16 record: `docs/progress/phase-16-hybrid-document-detection.md`
and `docs/phases/phase-16-hybrid-document-detection.md`.

## Phase 16 closing state

| Gate | Result |
|---|---|
| backend `pytest` | 1110 passed |
| `ruff check` / `ruff format --check` | clean |
| `mypy app` | clean, 167 source files |
| frontend `npm test` | 237 passed |
| `npm run lint` / `typecheck` | clean |
| offline Playwright | 20 passed |
| live Azure requests in the default suite | **0** |

Routing across every committed document fixture, local-only:

```
rental-contract-de.pdf                n=19  label coverage 1.00  -> local
required-optional-validation-fr.pdf   n=27  label coverage 1.00  -> local
```

## Carried into a later phase

Deliberately out of scope for the Phase 16 MVP, and unbuilt:

- **Advanced visual tables** — reconstruction from ruled-line geometry, merged
  visual cells, purely visual repeated rows (the repeated-row model still keys
  on AcroForm widget positions), and scanned-image OCR table structure.
- **Repeated-row editing UI** — the guided flow asks row fields one at a time
  with a heading and a row counter; there is no table editor.
- **Per-field admin override of requiredness** — the three states are carried
  and reviewable end to end, but not editable.
- **Per-tenant or per-period provider spend caps**, and escalation-rate
  visibility beyond the routing log line (Phase 23 territory).
- **Background jobs / progress polling** — preparation is still synchronous
  (Phase 20).
- The translation cache is process-local and dropped on restart.
- `guided-flow.spec.ts` default-tab gap, pre-existing since Phase 9.
- Azure Document Intelligence F0 rate-limits the live E2E specs; the offline
  suite is the default and makes no Azure request at all.

## Operational notes

- Playwright needs `PLAYWRIGHT_BASE_URL=http://localhost:3003` — the config
  defaults to 3000 while the compose frontend publishes 3003.
- Never run backend pytest and Playwright against the same dev database at
  once; pytest `TRUNCATE`s `form_templates`.
- `docker compose restart` does **not** re-read `.env`; use
  `up -d --force-recreate`.
- Development fixtures:
  `python -m app.commands.load_fixture` and
  `python -m app.commands.load_signature_demo` (refuses to run in production).

## Next phase

Phase 17 has not been started. See `docs/claude/project-overview.md` for the
roadmap.
