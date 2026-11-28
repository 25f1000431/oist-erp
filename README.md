# OIST Mock ERP

A mock, role-scoped ERP for OIST Bhopal's CSE department. This repository is a development demo and does not contain the college's live ERP or real student data.

## Requirements

- Python 3.11 or newer and `uv`
- Docker Compose

## Start the database and API

```sh
cp .env.example .env
docker compose up -d db
uv sync
uv run alembic upgrade head
PYTHONPATH=backend uv run python -m app.seed
uv run uvicorn app.main:app --app-dir backend --reload
```

The API is at `http://localhost:8000`; OpenAPI is at `/docs` and the health check is `/health`. Set a unique `JWT_SECRET_KEY` in `.env` before sharing the service. SQLite is supported for local tests by setting `DATABASE_URL=sqlite:///./oist_erp.db`.

## Start the frontend

In another terminal:

```sh
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The frontend calls `http://localhost:8000/api/v1` by default. Set `VITE_API_BASE_URL` before `npm run dev` if the API is hosted elsewhere. The API's `FRONTEND_ORIGINS` setting controls allowed browser origins; the defaults include both `localhost` and `127.0.0.1` on port 5173. `pnpm` also works if installed.

To rebuild the demo data from scratch, run `PYTHONPATH=backend uv run python -m app.seed --reset`. Student logins use enrollment number when present, otherwise roll number; all demo accounts use `SEED_DEFAULT_PASSWORD` from `.env`.

## Tests and lint

```sh
uv run pytest
uv run ruff check backend
```

## Browser smoke test

The Playwright test starts an isolated SQLite API with fake sample students and a Vite server, then checks that a teacher can create a session, mark two students absent, save attendance, and see the changed course total after logging in as one of those students. It also uploads a fake PDF for a pending assignment and verifies the new submission status. It uses `SEED_DEFAULT_PASSWORD` from the project `.env`; it does not use or reset the normal development database.

Install the browser once, then run the test:

```sh
cd frontend
npm install
npx playwright install chromium
npm run test:e2e
```

## OpenAPI documentation

Regenerate `docs/API.md` from the FastAPI schema after changing routes or response models:

```sh
PYTHONPATH=backend uv run python scripts/export_api_docs.py
```

The API and recommended attendance-agent call sequence are documented in [docs/AGENT_HANDOFF.md](docs/AGENT_HANDOFF.md).

## Current milestone

M0–M5 provide the project scaffold, database schema, bearer authentication, role checks, synthetic seed data, student read APIs, teacher attendance workflows, student and teacher frontend, browser smoke test, and generated API reference. Student assignment uploads support PDF, ZIP, and DOCX files up to 5 MB. A published student timetable is not available because the current data model has no timetable source.
