# ResumeForge Engine

Python (FastAPI) core engine for ResumeForge. Exposes a REST API consumed by the Go CLI/TUI and SvelteKit web frontend.

**Modules:** data store · AI tailoring (LiteLLM) · export (MD/PDF/DOCX) · analysis (5 analyzers)

---

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Setup

```bash
cd engine
uv sync --extra dev    # install all deps including dev tools
```

Seed empty data files on first run:
```bash
uv run python -c "from resumeforge.data.store import init_data_dir; init_data_dir()"
```

> **Note:** `engine/data/profile.json` is gitignored (PII). Create it manually or via `resumeforge init`.

---

## Running

```bash
uv run uvicorn resumeforge.api.app:app --reload --port 8080
```

---

## Interactive Testing

Once running, open **http://localhost:8080/docs** for the live Swagger UI.

Key endpoints to exercise:
| Endpoint | What it does |
|----------|-------------|
| `GET /api/templates` | List available resume templates |
| `POST /api/build` | Build a resume (MD/PDF/DOCX) |
| `POST /api/analyze` | Run 5-analyzer quality suite |
| `GET /api/data/experience` | Read experience section |
| `PUT /api/data/experience` | Update experience section |
| `GET /api/jobs` | List saved job descriptions |

---

## Non-Interactive Testing

```bash
# Full test suite (5 modules, 243 tests)
uv run pytest -x -v

# Single module
uv run pytest tests/test_api.py -x -v
uv run pytest tests/test_analysis.py -x -v

# Lint
uv run ruff check .
uv run ruff format .

# Type check
uv run mypy resumeforge/
```

Test modules:
- `tests/test_data.py` — Pydantic models + data store
- `tests/test_api.py` — FastAPI endpoints (TestClient)
- `tests/test_export.py` — MD/DOCX exporters
- `tests/test_ai.py` — AI provider + style controller (mocked)
- `tests/test_analysis.py` — 5 analyzers + report generator

---

## Structure

```
resumeforge/
├── api/          — FastAPI routes (build, tailor, analyze, data, templates)
├── data/         — Pydantic models (schema.py) + JSON store (store.py)
├── ai/           — LiteLLM wrapper + rewriter + tailor + style controller
├── export/       — BaseExporter + MD/PDF/DOCX exporters
├── analysis/     — 5 analyzers + report generator
└── templates/    — Jinja2 resume templates (classic, ...)
```

---

## AI Configuration

AI is **always optional** — everything works with `ai.enabled: false` (default).

To enable, edit `engine/data/meta.json`:
```json
{
  "ai": {
    "provider": "openai",
    "model": "gpt-4o",
    "enabled": true
  }
}
```

Supports any OpenAI-compatible provider via [LiteLLM](https://litellm.ai).
