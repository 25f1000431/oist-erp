# AGENTS.md — OIST Mock ERP (Agentic ERP project)

## What this repo is
A **mock college ERP** for OIST Bhopal (CSE department first) with separate **student** and **teacher** logins.
It is the system of record that a later **MCP server + AI agent** will wrap. So the API must be clean, typed,
role-scoped, and safe. This is NOT the real college ERP and must not imitate any vendor's branding or text.

## Stack (do not swap without asking)
- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, PostgreSQL (docker-compose). SQLite allowed only for quick local tests via `DATABASE_URL`.
- Auth: JWT bearer tokens, password hashing with argon2 (or bcrypt). No sessions in cookies for now.
- Frontend: React + Vite + TypeScript, react-router, TanStack Query, plain CSS with design tokens (CSS variables). **No Tailwind, no UI kit (no MUI/Chakra/shadcn defaults).**
- Tooling: `uv` + `pyproject.toml` for Python, `pnpm` (or npm) for frontend, `pytest`, `ruff`, `vitest`.

## Repo layout
```
backend/   app/ (api, core, models, schemas, services, seed)  alembic/  tests/  seed/private/ (gitignored)  seed/sample/
frontend/  src/ (pages, components, styles, lib)  public/
docs/      reference/ (screenshots)  API.md  DESIGN.md
AGENTS.md  docker-compose.yml  .env.example  README.md
```

## Hard rules
1. **Identity comes from the token, never from request bodies or query params.** Student routes live under `/api/v1/me/...` and take no student id.
2. **Every query is scoped.** Students see only their own rows. Teachers see only their own teaching assignments and the sections attached to them. Every teacher/class/student row carries `department_id`; filter by it in one shared dependency so future departments work.
3. **Writes are transactional, validated, and audited.** Each write inserts an `audit_log` row (actor, action, entity, before, after, timestamp) in the same transaction.
4. **No sensitive personal data.** Never create columns for Aadhaar, PAN, bank, address, DOB, blood group, or phone numbers. The seed loader reads only the whitelisted columns `enrollment_no, roll_no, full_name, gender, email`.
5. **Secrets and real data stay out of git.** `.env`, `backend/seed/private/`, uploaded files are gitignored. Commit only fake sample data in `backend/seed/sample/`.
6. **Timezone:** store UTC, display and reason in `Asia/Kolkata`.
7. **Every endpoint has Pydantic request/response models and appears in OpenAPI** with clear summaries (an LLM tool layer will be generated from them).
8. **Tests are required** for auth, scoping (horizontal privilege escalation), attendance saving, percentage math, and seed idempotency. Run `ruff` and `pytest` before declaring a milestone done.
9. Keep changes small and reviewable. Do not leave TODO stubs that pretend to work. If something is out of scope, say so in the final report.

## Design rules (frontend) — it must NOT look AI-generated
Full spec is in `docs/DESIGN.md` (copy of the DESIGN section of the prompt). Non-negotiables:
- **Banned fonts:** Inter, Roboto, Open Sans, Lato, Poppins, Montserrat, Nunito, DM Sans, Space Grotesk, Plus Jakarta Sans, Manrope, `system-ui` as the main face.
- **Use:** headings *Newsreader*, UI/body *Atkinson Hyperlegible Next*, numerals/roll numbers *Spline Sans Mono*. Self-host via `@fontsource` packages (no CDN). If a package is unavailable, tell me and propose a similarly uncommon fallback; do not silently use a banned font.
- **Palette from the OIST crest only:** navy `#353A7C`, vermilion `#E2332F`, marigold `#F9D20A` (small accents only), warm paper background `#FAF7F0`, ink `#15162B`, hairline `#E2DDD0`.
- **Banned looks:** gradients, glassmorphism, blurred blobs, glow/neon, emoji as icons, purple/indigo-blue "SaaS" defaults, big rounded-2xl soft-shadow cards, centered hero + pill badges, "Welcome back 👋" copy, stock illustrations.
- **Do:** 1px hairline borders, max 4px radius, dense left-aligned tables, tabular numerals, asymmetric layouts, generous whitespace, real college-voice microcopy, Phosphor icons (regular weight).
- Status is never color-only: always pair color with a letter/label (P / A, "Short", "Safe").
- Favicon: generate from `docs/reference/oist-logo.png` (32, 180 apple-touch, 192, 512) into `frontend/public/`.
