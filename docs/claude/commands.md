# Commands

## State

```bash
git status --short --branch
git diff --stat
git diff
```

## Backend

```bash
cd backend
ruff check .
ruff format --check .
mypy app
pytest
```

Prefer targeted tests during development:

```bash
cd backend
pytest path/to/test_file.py -q
```

## Migrations

```bash
cd backend
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

## Frontend

Read `frontend/package.json` before assuming scripts.

```bash
cd frontend
npm run lint
npm run typecheck
npm test
npm run test:e2e
```

## Docker

```bash
docker compose up --build -d
docker compose ps
docker compose logs --tail=200 backend
docker compose logs --tail=200 frontend
```

## Search

```bash
rg "SearchTerm" backend frontend docs
find backend/app -maxdepth 3 -type f | sort
find frontend/src -maxdepth 5 -type f | sort
```
