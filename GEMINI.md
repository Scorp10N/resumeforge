# ResumeForge

Open-source resume automation platform — build, tailor, and export resumes for specific roles, with optional AI assistance.

**Stack:** Python engine · Go CLI/TUI · SvelteKit web frontend

## Components

- `engine/` — Python 3.12 (FastAPI, Pydantic v2): core engine, AI tailoring, PDF/MD export, analysis, REST API
- `cli/` — Go 1.22 (Cobra + Bubble Tea): standalone CLI and TUI — single binary distribution
- `web/` — TypeScript (SvelteKit + Svelte 5): web frontend — communicates with engine via REST + SSE

All clients communicate with the engine over HTTP. See `ResumeForge_DESIGN.md` for full architecture.

## Engine Commands (run from `engine/`)

```bash
uv run uvicorn resumeforge.api.app:app --reload   # dev server (http://localhost:8080)
uv run pytest                      # run all tests
uv run pytest tests/<module>.py -x # one module, stop on first fail
uv run ruff check .                # lint
uv run ruff format .               # format
uv run mypy resumeforge/           # type check
```

## CLI Commands (run from `cli/`)

```bash
go build ./...         # build binary
go test ./...          # run tests
go run main.go --help  # run without building
```

## Web Commands (run from `web/`)

```bash
npm install    # install dependencies
npm run dev    # start dev server (http://localhost:5173)
npm run build  # production build
npm run check  # TypeScript + Svelte 5 type check
```

## Code Style — Engine (Python)

- Type hints on ALL functions (mypy strict)
- Pydantic v2 models for all data schemas
- ABC base classes for exporters and analyzers
- Imports: stdlib → third-party → local, blank-line separated
- No `Any` types. No bare `except`. No mutable defaults.

## Code Style — CLI (Go)

- Standard `go fmt` / `go vet` conventions
- Cobra command structs in individual files under `cmd/`
- All engine calls through `client/` package — never raw HTTP in `cmd/`
- Return errors, don't panic

## Code Style — Web (TypeScript/Svelte)

- Svelte 5 Runes syntax (`$state`, `$derived`, `$effect`)
- All engine API calls through `src/lib/api/engine.ts`
- TailwindCSS utility classes for styling

## Important Rules

- NEVER commit `engine/data/profile.json` — contains PII (name, email, phone) and is gitignored
- AI is always optional — everything must work with `ai.enabled: false`
- Go CLI must never contain business logic — HTTP calls to engine only, through `client/` package
- All exporters inherit from `BaseExporter` in `engine/resumeforge/export/base.py`
- All analyzers inherit from `BaseAnalyzer` in `engine/resumeforge/analysis/base.py`
- Docker containers run as non-root `appuser` (UID 1000)

For full agent handoff context and API reference, see `AGENTS.md`.
