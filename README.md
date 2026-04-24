# ResumeForge

[![CI](https://github.com/Scorp10N/resumeforge/actions/workflows/ci.yml/badge.svg)](https://github.com/Scorp10N/resumeforge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v0.1.0-blue)](https://github.com/Scorp10N/resumeforge/releases/tag/v0.1.0)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://python.org)

Open-source resume automation platform — build, tailor, and export resumes for specific roles, with optional AI assistance.

**Stack:** Python engine · Go CLI/TUI · SvelteKit web frontend

---

## Features

- **5 resume templates** — classic, modern, minimal, executive (PDF/MD), web/cyber (browser + GitHub Pages)
- **AI tailoring** via LiteLLM — any provider: OpenAI, Anthropic, Ollama, LM Studio
- **PDF + Markdown export** — WeasyPrint-powered, print-ready
- **5 analysis modules** — ATS keyword score, skill gap, quantification, readability, grammar
- **GitHub profile import** — pinned repos, stats, readme → projects section
- **GitHub Pages deploy** — one-command publish of the `web` template
- **Bilingual support** — English + Hebrew (RTL aware)
- **CLI + TUI** — Go binary, auto-spawns engine; Bubble Tea terminal UI
- **Web UI** — SvelteKit frontend with SSE streaming for build/analyze progress
- **REST API** — FastAPI engine at `localhost:8080`; full Swagger UI at `/docs`

---

## Components

| Directory | Language | Description |
|-----------|----------|-------------|
| `engine/` | Python 3.12 (FastAPI, Pydantic v2) | Core engine: REST API, AI tailoring, export (MD/PDF), analysis |
| `cli/` | Go (Cobra + Bubble Tea) | Standalone CLI and terminal TUI — single binary distribution |
| `web/` | TypeScript (SvelteKit + Svelte 5) | Web frontend — communicates with engine via REST + SSE |

All clients talk to the engine over HTTP. See [DESIGN.md](ResumeForge_DESIGN.md) for full architecture.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | [python.org](https://python.org) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Go | 1.22+ | [go.dev/dl](https://go.dev/dl/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) or `nvm install 20` |

---

## Installation

### Docker (recommended — no local installs needed)

```bash
git clone https://github.com/Scorp10N/resumeforge.git
cd resumeforge
cp .env.example .env          # edit VITE_ENGINE_URL for remote deploys
docker compose up             # builds images and starts everything

# Engine API + Swagger UI → http://localhost:8080/docs
# Web UI                  → http://localhost:3000
```

Data persists in Docker volumes (`engine_data`, `engine_output`). Use `make docker-clean` to wipe.

### From Source

```bash
git clone https://github.com/Scorp10N/resumeforge.git
cd resumeforge

# Engine (Python)
cd engine
uv sync --extra dev
uv run uvicorn resumeforge.api.app:app --port 8080

# CLI (Go) — in a separate terminal, from repo root
cd cli
go build -o resumeforge ./...
./resumeforge --help

# Web (Node) — in a separate terminal, from repo root
cd web
npm install
npm run dev   # http://localhost:5173
```

Or start engine + web together:

```bash
make dev   # engine (8080) + web (5173) — Ctrl+C stops both
```

---

## Testing All Features

### 1. Engine API (Swagger UI)

```bash
# Start engine
cd engine && uv run uvicorn resumeforge.api.app:app --port 8080
```

Open **http://localhost:8080/docs** and exercise:
- `POST /api/build` — build resume to Markdown/PDF
- `GET /api/templates` — list all 5 templates
- `POST /api/analyze` — run quality analysis (ATS score, gaps, readability)
- `GET/POST /api/jobs` — manage job descriptions
- `PUT /api/data/profile` — update resume profile
- `GET /api/data/export` — export all data as ZIP backup

### 2. Web UI

```bash
cd web && npm run dev   # http://localhost:5173
```

Routes to exercise:
- `/` — Dashboard with data overview
- `/builder` — build with template selector, format picker, SSE progress
- `/analyze` — ATS score and section breakdown
- `/data/experience` — edit experience bullets inline
- `/templates` — template gallery
- `/jobs` — save and manage job descriptions
- `/settings` — configure AI provider (OpenAI, Anthropic, Ollama)

### 3. CLI

```bash
cd cli && go build -o resumeforge ./...

./resumeforge build --template classic --format md
./resumeforge build --template executive --format pdf --job <slug>
./resumeforge analyze
./resumeforge analyze --job <slug>
./resumeforge templates list
./resumeforge data show experience
./resumeforge data export --output backup.zip
./resumeforge config set ai.enabled false
./resumeforge github import --username <handle>
./resumeforge github deploy --pages --repo owner/repo --template web
```

### 4. TUI

```bash
./resumeforge tui
```

Navigate: **Dashboard → Editor → Job Matcher → Analysis**. Press `q` or `Ctrl+C` to quit.

### 5. GitHub Pages Deploy

```bash
curl -X POST http://localhost:8080/api/integrations/github/pages/deploy \
  -H "Content-Type: application/json" \
  -d '{"repo":"owner/resume","branch":"gh-pages","template":"web","locale":"en"}'
```

---

## Non-Interactive Testing (CI)

```bash
make test       # all components
make lint       # ruff + mypy + go vet + svelte-check
```

Or individually:

```bash
make test-engine    # pytest (258 tests)
make test-cli       # go test
make test-web       # svelte-check
make test-integration  # E2E cross-component (auto-starts engine)
```

See [tests/README.md](tests/README.md) for the full testing guide.

---

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup, branching, and PR conventions.

See [DESIGN.md](ResumeForge_DESIGN.md) for architecture, data model, and API contract.

---

## Security

See [docs/SECURITY.md](docs/SECURITY.md) for the STRIDE threat model and vulnerability reporting.

---

## License

[MIT](LICENSE) — Copyright © 2026 Yarin M (Scorp10N)
