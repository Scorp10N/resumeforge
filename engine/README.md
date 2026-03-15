# ResumeForge Engine

Python core engine for the ResumeForge platform. Exposes a REST API consumed by the Go CLI/TUI and SvelteKit web frontend.

## Setup

```bash
cd engine
uv sync
uv run uvicorn resumeforge.api.app:app --reload --port 8080
```

## Development

```bash
uv run pytest              # run tests
uv run ruff check .        # lint
uv run ruff format .       # format
uv run mypy resumeforge/   # type check
```

## API

Once running, visit http://localhost:8080/docs for interactive API documentation.
