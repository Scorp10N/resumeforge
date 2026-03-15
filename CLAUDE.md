# ResumeForge

Polyglot resume automation platform with standalone clients and a central Python engine.

## Components
- `engine/` — Python (FastAPI): core engine, AI, export, analysis, REST API
- `cli/` — Go (Cobra + Bubble Tea): CLI and TUI client
- `web/` — TypeScript (SvelteKit): web frontend client

## Architecture
- Clients communicate with engine via HTTP REST API + SSE streaming
- Engine runs locally (auto-spawned by CLI) or remotely (cloud edition)
- See DESIGN.md for full architecture, data model, and API contract

## Engine Commands (run from engine/)
- `uv run pytest` — run all tests
- `uv run pytest tests/{module}/ -x` — run one module, stop on first fail
- `uv run ruff check .` — lint
- `uv run ruff format .` — format
- `uv run mypy resumeforge/` — type check
- `uv run uvicorn resumeforge.api.app:app --reload` — start engine dev server

## CLI Commands (run from cli/)
- `go build ./...` — build
- `go test ./...` — run tests
- `go run main.go --help` — run CLI
- `goreleaser build --snapshot --clean` — build all platform binaries

## Web Commands (run from web/)
- `npm install` — install deps
- `npm run dev` — start dev server
- `npm run build` — production build
- `npm run check` — Svelte type check

## Code Style — Engine (Python)
- Type hints on ALL functions (mypy strict)
- Pydantic v2 models for all data schemas
- ABC base classes for exporters, analyzers, providers
- Docstrings: Google style
- Imports: stdlib → third-party → local, separated by blank line
- No `Any` types. No bare `except`. No mutable defaults.

## Code Style — CLI (Go)
- Follow standard Go fmt/vet conventions
- Cobra command structs in individual files under cmd/
- All engine calls go through the client package — never raw HTTP in cmd/
- Errors returned, not panicked

## Code Style — Web (TypeScript/Svelte)
- Svelte 5 Runes syntax (`$state`, `$derived`, `$effect`)
- All engine API calls through `src/lib/api/engine.ts` — never inline fetch
- TailwindCSS utility classes for styling
- Components in `src/lib/components/`

## Important Rules
- NEVER commit engine/data/profile.json (PII) — gitignored
- All exporters inherit from `BaseExporter` in engine/export/base.py
- All analyzers inherit from `BaseAnalyzer` in engine/analysis/base.py
- AI is always optional — everything must work with `ai.enabled: false`
- Go CLI must never import Python engine code — only HTTP calls
- Engine API is the single source of truth for all business logic
