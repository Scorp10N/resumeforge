# ResumeForge

Open-source resume automation platform — build, tailor, and export resumes for specific roles, with optional AI assistance.

**Stack:** Python engine · Go CLI/TUI · SvelteKit web frontend

---

## Components

| Directory | Language | Description |
|-----------|----------|-------------|
| `engine/` | Python 3.12 (FastAPI, Pydantic v2) | Core engine: REST API, AI tailoring, export (MD/PDF/DOCX), analysis |
| `cli/` | Go (Cobra + Bubble Tea) | Standalone CLI and terminal TUI — single binary distribution |
| `web/` | TypeScript (SvelteKit + Svelte 5) | Web frontend — communicates with engine via REST + SSE |

All clients talk to the engine over HTTP. See [DESIGN.md](ResumeForge_DESIGN.md) for full architecture.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | [python.org](https://python.org) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Go | 1.21+ | [go.dev/dl](https://go.dev/dl/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) or `nvm install 20` |

---

## Quick Start

```bash
# 1. Engine
cd engine
uv sync --extra dev
uv run uvicorn resumeforge.api.app:app --reload --port 8080

# 2. Web frontend (new terminal)
cd web
npm install
npm run dev   # http://localhost:5173

# 3. CLI (new terminal)
cd cli
go build -o resumeforge ./...
./resumeforge build --template classic --format md
```

---

## Interactive Testing

Start all services together:
```bash
make dev   # engine (port 8080) + web (port 5173) — Ctrl+C stops both
```

Or individually:
```bash
make dev-engine   # http://localhost:8080
make dev-web      # http://localhost:5173
```

### Engine — Swagger UI
Open **http://localhost:8080/docs** in your browser.
- `POST /api/build` — build a resume
- `GET /api/templates` — list available templates
- `POST /api/analyze` — run quality analysis
- `GET /api/jobs` — list saved job descriptions

### Web Frontend
Open **http://localhost:5173**. Routes:
- `/` — Dashboard
- `/builder` — Build resume with template/format/job selector and SSE progress
- `/analyze` — Analysis report with ATS score
- `/data/[section]` — Edit resume sections (experience, skills, education...)
- `/templates` — Template gallery
- `/jobs` — Saved job descriptions
- `/settings` — AI and engine configuration

### CLI
```bash
./resumeforge --help
./resumeforge build --template classic --format md
./resumeforge build --template classic --format docx --job <slug>
./resumeforge analyze
./resumeforge analyze --job <slug>
./resumeforge templates list
./resumeforge data show experience
./resumeforge data export --output backup.zip
./resumeforge config set ai.enabled false
```

### TUI
```bash
./resumeforge tui
```
Screens: **Dashboard -> Editor -> Job Matcher -> Analysis**. Press `q` or `Ctrl+C` to quit.

---

## Non-Interactive Testing (CI)

```bash
make test       # all components
make lint       # ruff + mypy + go vet + svelte-check
```

Or individually:
```bash
make test-engine    # pytest (243 tests)
make test-cli       # go test
make test-web       # svelte-check
make test-integration  # E2E cross-component (auto-starts engine)
```

See [tests/README.md](tests/README.md) for the full testing guide.

---

## Development

See component READMEs for detailed dev guides:
- [engine/README.md](engine/README.md)
- [cli/README.md](cli/README.md)
- [web/README.md](web/README.md)

See [DESIGN.md](ResumeForge_DESIGN.md) for architecture, data model, and API contract.

---

## License

MIT
