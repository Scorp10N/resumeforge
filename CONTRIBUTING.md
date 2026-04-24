# Contributing to ResumeForge

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.12+ | [python.org](https://python.org) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Go | 1.22+ | [go.dev/dl](https://go.dev/dl/) |
| Node.js | 20+ | [nodejs.org](https://nodejs.org) |
| gh CLI | latest | [cli.github.com](https://cli.github.com) |

## Setup

```bash
git clone https://github.com/Scorp10N/resumeforge.git
cd resumeforge

# Install all dependencies
cd engine && uv sync --extra dev && cd ..
cd cli && go mod tidy && cd ..
cd web && npm install && cd ..
```

## Running Services

```bash
make dev          # start engine (8080) + web (5173) together
make dev-engine   # engine only
make dev-web      # web only
```

## Testing

```bash
make test         # all components
make test-engine  # engine pytest (258 tests)
make test-cli     # go test
make test-web     # svelte-check
```

## Linting

```bash
make lint         # all
make lint-engine  # ruff + mypy
make lint-cli     # go vet
make lint-web     # svelte-check
```

## Branch and PR Conventions

- Branch from `main`
- One logical change per PR
- PR title: imperative present tense (`Add X`, `Fix Y`, `Refactor Z`)
- Include test coverage for new features

## Architecture

- **Engine** (`engine/`) owns all business logic — the CLI and web are thin clients
- Never put business logic in `cli/` or `web/` — call the engine API instead
- All exporters extend `BaseExporter`, all analyzers extend `BaseAnalyzer`
- AI is always optional — every feature must work with `ai.enabled: false`

## Reporting Vulnerabilities

See [docs/SECURITY.md](docs/SECURITY.md).
