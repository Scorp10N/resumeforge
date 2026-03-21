# ResumeForge — Testing Guide

Central reference for all testing scopes. Run all tests from the project root using `make`.

---

## Quick Reference

| Goal | Command |
|------|---------|
| Run everything | `make test` |
| Run + lint | `make lint && make test` |
| Integration tests | `make test-integration` |
| Start dev environment | `make dev` |
| List all commands | `make help` |

---

## Scopes

### 1. Unit Tests

Non-interactive automated tests. Run without a live server.

| Component | Command | Files | Count |
|-----------|---------|-------|-------|
| Engine | `make test-engine` | `engine/tests/test_*.py` | 243 |
| CLI | `make test-cli` | `cli/client/*_test.go` | ~10 |
| Web | `make test-web` | TypeScript + Svelte check | — |

**Engine test modules:**
- `test_data.py` — Pydantic models + JSON store
- `test_api.py` — FastAPI endpoints (TestClient, no real server)
- `test_export.py` — MD/DOCX exporters
- `test_ai.py` — AI provider + style controller (mocked LiteLLM)
- `test_analysis.py` — 5 analyzers + report generator

**TDD mode (re-run on change):**
```bash
make test-engine-watch
```

**Single module:**
```bash
make test-engine-module M=test_api
```

---

### 2. Lint & Type Checking

Static analysis — no running code needed.

```bash
make lint           # all components
make lint-engine    # ruff (style) + mypy (types, strict mode)
make lint-cli       # go vet
make lint-web       # svelte-check (TypeScript + Svelte 5)
```

Auto-fix formatting:
```bash
make fmt            # ruff format + go fmt
```

---

### 3. Integration Tests

Cross-component E2E tests. The engine starts automatically via a pytest fixture — no manual server start needed.

```bash
make test-integration
```

**What they test:**
- Engine API is reachable and returns valid responses
- `GET /api/templates` returns the classic template
- `POST /api/build` builds a resume successfully
- `POST /api/analyze` returns a valid analysis report

**Location:** `tests/integration/`
- `conftest.py` — pytest session fixture that starts engine on port 8089
- `test_e2e.py` — E2E test cases

**Port:** 8089 (avoids conflicts with the dev server on 8080)

---

### 4. Interactive / Manual Testing

Start all services together:

```bash
make dev            # engine (port 8080) + web (port 5173)
# Ctrl+C stops both cleanly
```

Or start individually:

```bash
make dev-engine     # engine only — http://localhost:8080
make dev-web        # web only   — http://localhost:5173
```

**Service URLs:**

| Service | URL | Notes |
|---------|-----|-------|
| Engine API | http://localhost:8080 | REST API |
| Swagger UI | http://localhost:8080/docs | Interactive API browser |
| Web Frontend | http://localhost:5173 | SvelteKit dev server |

**CLI manual testing:** see [`cli/README.md`](../cli/README.md)

---

### 5. CI (GitHub Actions)

Runs automatically on push and pull requests.

**Workflow:** `.github/workflows/ci.yml`

**Jobs (parallel):**
- `engine` — lint-engine + test-engine
- `cli` — lint-cli + test-cli
- `web` — test-web (npm install + svelte-check)

---

## Adding New Tests

- **Engine unit tests:** add to `engine/tests/test_*.py`
- **CLI unit tests:** add `*_test.go` files alongside the code
- **Integration tests:** add to `tests/integration/test_*.py`
- **Future web E2E (Playwright):** add to `tests/playwright/` (not yet configured)
