# Agent integration handoff

This API is the system of record for the OIST Mock ERP. The companion agent or MCP server should call these HTTP endpoints; it should not query the database or duplicate attendance and authorization rules.

## Run locally

From the repository root:

```sh
cp .env.example .env
# Set SEED_DEFAULT_PASSWORD and a unique JWT_SECRET_KEY in .env.
docker compose up -d db
uv sync
uv run alembic upgrade head
PYTHONPATH=backend uv run python -m app.seed
uv run uvicorn app.main:app --app-dir backend --reload
```

The base URL is `http://localhost:8000/api/v1`; interactive OpenAPI is at `http://localhost:8000/docs` and the generated reference is [API.md](API.md). Seeded logins use `FAC001`…`FAC006` for faculty and student roll number or enrollment number. Read the demo password from the local `.env`; never include it in agent prompts, tool output, logs, or this repository.

## Agent call pattern

1. Authenticate with `POST /auth/login`; keep the returned bearer token in the agent's secret/session storage and attach it as `Authorization: Bearer …`.
2. Use `GET /auth/me` to confirm the active role. The API derives user and student identity from the token.
3. For a teacher attendance change, list only the actor's own classes with `GET /teacher/classes`, then create a session with `POST /teacher/sessions` if needed.
4. Read `GET /teacher/sessions/{id}/roster` and prepare a complete roster. Preview with `PUT /teacher/sessions/{id}/attendance?dry_run=true`.
5. Show the returned counts and per-student diff to the teacher. Call the same route without `dry_run` only after the teacher confirms the preview.
6. Verify with `GET /teacher/sessions/{id}` or `GET /me/attendance/summary` using a student credential when testing student-visible results.

The dry-run response does not write attendance or an audit row. The final write is atomic, upserts one result per student, and creates its audit event in the same transaction. Session and student scope checks remain in the API even if the agent filters its own choices.

## Available tool surfaces

- Student, token-scoped reads: profile, attendance summary and session history, fees, results, assignments.
- Student assignment submission: `POST /me/assignments/{assignment_id}/submission` with multipart field `file`. Only PDF, ZIP, and DOCX are accepted, up to 5 MB. Files are stored under `UPLOAD_DIR`, outside the frontend web root; the response contains no storage path. A later upload replaces the student's previous file and is audited.
- Teacher: own classes, filtered sessions, session create/read/edit/delete, roster, and attendance preview/save.
- `GET /health` and `/openapi.json` are public system routes.

See [API.md](API.md) for response shapes, parameters, and status codes. Errors follow `{ "error": { "code", "message", "details" } }`.

## Boundaries and known limitations

- The API has no MCP server or agent implementation yet; this handoff is the contract for that work.
- There is no published timetable model/API, so the student home screen currently has no authoritative recurring schedule to show.
- HOD/admin route stubs are not implemented. Teacher session edits follow the configured back-date window; HOD-wide editing is not exposed yet.
- Assignment submission uploads and replacement are supported. There is no file-download endpoint; submissions are private files on the API host.
- The demo seed is synthetic. Do not point agent development at a live institutional system or import real personal data.
