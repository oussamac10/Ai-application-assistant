# Current Phase Workflow

## 1. Orient

- Resolve repository and branch.
- Read project instruction files.
- Read root `TODO.md`.
- Read the latest short handoff.
- Inspect the current diff and recent commit when useful.

## 2. Choose the next slice

Select one coherent unchecked unit that can be implemented and tested together. Prefer this order:

1. contracts and domain model
2. migration and repository
3. service logic
4. API integration
5. frontend integration
6. tests
7. documentation

Adapt to the repository's existing order rather than forcing this sequence.

## 3. Implement

- Inspect analogous completed modules first.
- Reuse conventions.
- Keep changes narrowly scoped.
- Add or update tests with behavior.
- Avoid broad refactors during feature work.

## 4. Verify

Typical backend checks:

```bash
ruff check .
ruff format --check .
mypy app
pytest
```

Typical migration checks:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

Typical frontend checks:

```bash
npm run lint
npm run typecheck
npm test
npm run test:e2e
```

Read package and project configuration before assuming exact commands.

## 5. Update project state

- Update only verified TODO entries.
- Include exact test counts.
- Update affected docs and ADRs.
- Update the short handoff with current state and next action.

## 6. Publish only when requested

Do not commit, push, open a pull request, or merge unless the user explicitly requests it or repository instructions clearly authorize it.
