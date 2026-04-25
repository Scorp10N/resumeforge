# ResumeForge — Copilot Context

Open-source resume automation platform. Polyglot stack: Python/FastAPI engine (port 8080), Go/Cobra CLI, TypeScript/SvelteKit web frontend (port 5173 dev / 3000 prod). All clients are thin HTTP wrappers — the engine contains all business logic.

## Components

| Dir | Language | Purpose |
|-----|----------|---------|
| `engine/` | Python 3.12, FastAPI, Pydantic v2 | Core engine: API, AI, export, analysis |
| `cli/` | Go 1.22, Cobra + Bubble Tea | CLI + TUI binary |
| `web/` | TypeScript, SvelteKit, Svelte 5 | Web frontend |

## Non-Negotiable Rules

- Never commit `engine/data/profile.json` — it's PII and gitignored
- AI is always optional — everything works with `ai.enabled: false`
- Go CLI calls engine via HTTP only — no business logic in `cmd/`, all engine calls through `client/`
- Web API calls go through `src/lib/api/engine.ts` only — never inline `fetch()` in components
- Docker containers run as non-root `appuser` (UID 1000) — don't change Dockerfile USER lines
- `CORS_ORIGINS='*'` raises RuntimeError at engine startup — use explicit origin lists

## Test Commands

```bash
# Engine (Python)
cd engine && uv run pytest -x -v

# CLI (Go)
cd cli && go test ./... && go build ./...

# Web (TypeScript)
cd web && npm run check

# All
make test && make lint
```

## Code Style

**Python:** Type hints on all functions (mypy strict), Pydantic v2 models, no `Any`, no bare `except`, Google-style docstrings.

**Go:** `go fmt` / `go vet`, Cobra commands in `cmd/`, errors returned not panicked.

**TypeScript/Svelte:** Svelte 5 Runes (`$state`, `$derived`, `$effect`), TailwindCSS utility classes.

## Key File Paths

- `engine/resumeforge/api/app.py` — FastAPI app, CORS, routers, lifespan
- `engine/resumeforge/data/schema.py` — all Pydantic models
- `engine/resumeforge/data/store.py` — JSON data store (reads `engine/data/*.json`)
- `engine/resumeforge/export/base.py` — BaseExporter ABC
- `engine/resumeforge/analysis/base.py` — BaseAnalyzer ABC
- `cli/client/` — typed HTTP client for engine API
- `web/src/lib/api/engine.ts` — all web → engine API calls

For full context: see `CLAUDE.md`, `AGENTS.md`, and `ResumeForge_DESIGN.md`.
