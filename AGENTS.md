# ResumeForge — Agent Handoff Guide

Open-source resume automation platform. Polyglot stack: Python engine (FastAPI, port 8080), Go CLI/TUI (Cobra + Bubble Tea), TypeScript web (SvelteKit, port 5173 dev / 3000 prod). All clients communicate with the engine over HTTP — the engine is the single source of truth for all business logic.

---

## Quick Start

```bash
git clone https://github.com/Scorp10N/resumeforge.git
cd resumeforge
make setup        # install engine + web deps (Go fetches on build)
make dev          # start engine (8080) + web (5173) together
curl http://localhost:8080/health   # → {"status":"ok","version":"0.2.0"}
```

---

## Components

| Directory | Language | Purpose | Port |
|-----------|----------|---------|------|
| `engine/` | Python 3.12 (FastAPI, Pydantic v2) | Core engine: REST API, AI tailoring, export, analysis | 8080 |
| `cli/` | Go 1.22 (Cobra + Bubble Tea) | Standalone CLI and TUI — single binary | — |
| `web/` | TypeScript (SvelteKit + Svelte 5) | Web frontend | 5173 (dev) / 3000 (prod) |

---

## Engine Commands (run from `engine/`)

```bash
uv run uvicorn resumeforge.api.app:app --reload --port 8080   # dev server
uv run pytest                      # all tests (265+)
uv run pytest tests/<module>.py -x # one module, stop on first fail
uv run ruff check .                # lint
uv run ruff format .               # format
uv run mypy resumeforge/           # type check
```

## CLI Commands (run from `cli/`)

```bash
go build ./...         # build
go test ./...          # run tests
go run main.go --help  # run CLI without building
```

## Web Commands (run from `web/`)

```bash
npm install    # install deps
npm run dev    # start dev server (http://localhost:5173)
npm run build  # production build
npm run check  # TypeScript + Svelte type check
```

## All-in-one (run from repo root)

```bash
make test          # engine + CLI + web tests
make lint          # ruff + mypy + go vet + svelte-check
make test-engine   # engine only (pytest)
make test-cli      # CLI only (go test)
make test-web      # web only (svelte-check)
```

---

## Architecture Rules

- **Engine is the single source of truth** — all business logic lives in the engine. Clients are thin HTTP wrappers.
- **AI is always optional** — every feature must work with `ai.enabled: false` in config.
- **Go CLI never contains business logic** — all engine calls go through `cli/client/` package, never raw HTTP in `cmd/`.
- **Web never calls the engine directly in components** — all API calls go through `web/src/lib/api/engine.ts`.
- **No circular imports** — clients import nothing from the engine Python package.

---

## Code Style — Engine (Python)

- Type hints on ALL functions (mypy strict)
- Pydantic v2 models for all data schemas (in `engine/resumeforge/data/schema.py`)
- ABC base classes for exporters (`BaseExporter`) and analyzers (`BaseAnalyzer`)
- Imports: stdlib → third-party → local, separated by blank lines
- No `Any` types. No bare `except`. No mutable defaults.
- Docstrings: Google style

## Code Style — CLI (Go)

- Standard `go fmt` / `go vet` conventions
- Cobra command structs in individual files under `cmd/`
- All engine calls through `client/` package — never raw `http.Get` in `cmd/`
- Return errors, don't panic

## Code Style — Web (TypeScript/Svelte)

- Svelte 5 Runes syntax (`$state`, `$derived`, `$effect`) — not Svelte 4 stores
- All engine API calls through `src/lib/api/engine.ts` — never inline `fetch()`
- TailwindCSS utility classes for styling
- Components in `src/lib/components/`

---

## Data Files

All resume data lives in `engine/data/` as JSON:

| File | Content |
|------|---------|
| `profile.json` | Name, title, email, LinkedIn, GitHub, summary — **PII, gitignored** |
| `experience.json` | Work positions with bullets, dates, tags, priority |
| `skills.json` | Skill categories + items; `exploring` array |
| `education.json` | Education entries |
| `projects.json` | Projects with `technologies` array (not `tags`) |
| `certifications.json` | Certifications |
| `meta.json` | Engine settings (port, AI config, locale) |

---

## Key API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check → `{"status":"ok","version":"0.2.0"}` |
| `POST` | `/api/build` | Build resume (returns job_id for SSE streaming) |
| `GET` | `/api/build/stream?job_id=<id>` | SSE stream of build progress |
| `POST` | `/api/analyze` | Run quality analysis (ATS score, skill gap, readability) |
| `GET` | `/api/templates` | List available templates |
| `GET` | `/api/data/{section}` | Read a data section (experience, skills, etc.) |
| `PUT` | `/api/data/{section}` | Overwrite a data section |
| `GET/POST` | `/api/jobs` | Manage job descriptions |
| `GET` | `/docs` | Swagger UI (full API reference) |

---

## Security Rules

- **Never commit `engine/data/profile.json`** — it contains PII (name, email, phone). It is gitignored.
- **`CORS_ORIGINS` must never contain `'*'`** — the engine raises `RuntimeError` at startup if it detects a wildcard.
- **Docker containers run as non-root `appuser` (UID 1000)** — do not change `USER` instructions in Dockerfiles.
- **No bare `except` in Python** — always catch specific exceptions.

---

## Important Rules

- All exporters inherit from `BaseExporter` in `engine/resumeforge/export/base.py`
- All analyzers inherit from `BaseAnalyzer` in `engine/resumeforge/analysis/base.py`
- Engine port is configurable via `meta.json` → `engine.port` (default: 8080)
- Streaming responses use Server-Sent Events (SSE) via FastAPI `StreamingResponse`
- Errors return structured JSON: `{"detail": "message", "code": "ERROR_CODE"}`

---

## Testing

```bash
make test          # all components
make lint          # all linters + type checks
make test-engine   # uv run pytest -x -v (265+ tests)
make test-cli      # go test ./...
make test-web      # npm run check (svelte-check)
```

---

## References

- `CLAUDE.md` — Claude Code-specific agent instructions (module-level files in each subdirectory)
- `ResumeForge_DESIGN.md` — full architecture, data model, API contract (699 lines)
- `docs/SECURITY.md` — STRIDE threat model, Docker security, known CVEs
- `CONTRIBUTING.md` — setup, branching, PR conventions, Docker dev workflow
