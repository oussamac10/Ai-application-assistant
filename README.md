# AI Form Assistant

A multilingual AI form assistant that helps users understand and complete forms written in languages they may not speak.

## Project Purpose

The AI Form Assistant bridges the language gap by allowing users to complete forms in three separate language concepts:
* `sourceLanguage`: The language of the original form.
* `userLanguage`: The language used for questions, clarifications, and explanations.
* `outputLanguage`: The language used in the completed form.

It guides the user through the form one field at a time, normalizing, validating, and confirming answers.

## Current MVP Phase: MVP Phase 4 — Mock Question and Answer Workflow

This repository contains the implementation of MVP Phase 4. It establishes:
* Multilingual Q&A workflow supporting 14 distinct field types.
* `MockAIProvider` executing mock extraction rules locally without external API calls.
* Deterministic normalizers and validators running server-side for strict schema conformance.
* Temporary `FormAnswer` data model with cascade deletion upon session removal.
* Ordered field selection tracking current position dynamically.
* API endpoints:
  - `GET /api/form-sessions/{session_id}/current-field` (Get current Q&A field)
  - `POST /api/form-sessions/{session_id}/answers` (Submit original answer text)
  - `POST /api/form-sessions/{session_id}/answers/{answer_id}/clarify` (Submit missing details for clarification)
  - `POST /api/form-sessions/{session_id}/answers/{answer_id}/confirm` (Confirm extracted/normalized value)
  - `PUT /api/form-sessions/{session_id}/fields/{field_id}/answer` (Edit answer)
  - `POST /api/form-sessions/{session_id}/previous-field` (Navigate backwards)
  - `GET /api/form-sessions/{session_id}/summary` (List all fields and their answers)
  - `POST /api/form-sessions/{session_id}/confirm-summary` (Submit final confirmation)
* Dynamic progress tracking based on confirmed required fields.
* Full test coverage and static analysis verification.

*Note: In Phase 4, OCR, uploads, and PDF templates mapping/exports are omitted.*

---

## Prerequisites

Before starting, ensure you have the following installed on your host system:
* **Docker** & **Docker Compose**
* **Node.js** (v20 or higher) & **npm**
* **Python** (v3.11 or v3.12)
* **Git**

---

## Environment Configuration

Copy the example environment file:
```bash
cp .env.example .env
```
Safe defaults are provided for local development.

---

## Running Locally

### Starting with Docker Compose

To build and start the complete local development environment (postgres database, FastAPI backend, and Next.js frontend):
```bash
docker compose up --build
```

### Service URLs

Once running, services are accessible at:
* **Frontend Application**: `http://localhost:3003`
* **FastAPI Backend Application**: `http://localhost:8000`
* **Backend API Docs (Swagger)**: `http://localhost:8000/docs`
* **PostgreSQL Database**: `localhost:5432`

---

## Service Verification & Health Checks

You can verify service status using:
* **Backend Status API**: `curl -i http://localhost:8000/api/health`
* **Backend Database Status API**: `curl -i http://localhost:8000/api/health/database`

---

## Local Development Commands

### Backend Commands (from `./backend`)

Before running commands, initialize the virtual environment:
```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

* **Run Server**: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
* **Run Tests**: `PYTHONPATH=. pytest`
* **Format Check**: `ruff format --check .`
* **Auto-format**: `ruff format .`
* **Lint Check**: `ruff check .`
* **Auto-fix Lint**: `ruff check --fix .`
* **Type Check**: `mypy app`
* **Initialize alembic**: Already initialized. To run migrations: `alembic upgrade head`
* **Load Fixture**: `python -m app.commands.load_fixture` (loads the Basic Registration multilingual template version 1 and publishes it)
* **Cleanup Expired Sessions**: `python -m app.commands.cleanup_expired_sessions` (scans and marks expired open sessions as expired)

### Frontend Commands (from `./frontend`)

Before running commands, install node modules:
```bash
cd frontend
npm install
```

* **Run Dev Server**: `npm run dev`
* **Run Tests**: `npm test`
* **Lint Check**: `npm run lint`
* **Type Check**: `npm run typecheck`
* **Build Project**: `npm run build`

---

## Decisions & Important Assumptions

1. **Port Configuration**: Due to common host port collisions (e.g. DDEV mapping ports 3000-3001), the frontend port on the host has been mapped to `3003`. Internally, the container exposes port `3000`.
2. **API Proxying**: Next.js uses client-side proxy rewrites in `next.config.js` to route all `/api/*` calls from the browser to the backend (`http://backend:8000`). This completely eliminates CORS issues.
3. **Database Health Failures**: In `/api/health/database`, we return a `503 Service Unavailable` status code with `{"status":"error", "database":"unavailable"}` if database connections fail, which is handled gracefully by the frontend.
4. **Python Version**: Development virtual environment was set up with Python 3.12 on the host to avoid source compilations of pre-wheels packages on Python 3.14.

---

## Common Troubleshooting

### Port 3000/3003 is already in use
If Docker fails to bind ports, run:
```bash
lsof -i :3003
```
and terminate any process occupying the port, or edit `ports` inside `docker-compose.yml`.

### Database Connection Failure
If the frontend shows `Database Connection: Unavailable` or backend health check logs connection errors, ensure the database container is fully initialized and healthy. You can verify it via `docker compose ps`.
To force recreate DB volumes, run:
```bash
docker compose down -v
docker compose up --build
```
