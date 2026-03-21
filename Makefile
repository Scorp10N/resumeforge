# ResumeForge — Unified command interface
# Usage: make <target>   e.g.  make test   make dev   make lint

PYTHON := cd engine && uv run
GO     := cd cli && go
NODE   := cd web && npm run

.PHONY: help setup dev dev-engine dev-web \
        test test-engine test-engine-fast test-engine-watch test-engine-module \
        test-cli test-web test-integration \
        lint lint-engine lint-cli lint-web fmt \
        build-cli build-web

.DEFAULT_GOAL := help

# ── Help ──────────────────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Setup ─────────────────────────────────────────────────────────────────────
setup: ## Install all dependencies (engine + web; Go fetches on build)
	cd engine && uv sync --extra dev
	cd web && npm install

# ── Dev servers ───────────────────────────────────────────────────────────────
dev: ## Start engine + web together (Ctrl+C stops both)
	cd engine && uv run honcho start -f ../Procfile

dev-engine: ## Start engine only (http://localhost:8080)
	$(PYTHON) uvicorn resumeforge.api.app:app --reload --port 8080

dev-web: ## Start web frontend only (http://localhost:5173)
	$(NODE) dev

# ── Unit Tests ────────────────────────────────────────────────────────────────
test: test-engine test-cli test-web ## Run all unit test suites

test-engine: ## Engine: pytest -x -v (243 tests)
	$(PYTHON) pytest -x -v

test-engine-fast: ## Engine: pytest -x -q (fast, quiet)
	$(PYTHON) pytest -x -q

test-engine-watch: ## Engine: re-run last-failed tests (TDD mode)
	$(PYTHON) pytest --lf -v

test-engine-module: ## Engine: one module — make test-engine-module M=test_api
	$(PYTHON) pytest tests/$(M).py -x -v

test-cli: ## CLI: go test ./...
	$(GO) test ./...

test-web: ## Web: svelte-check (TypeScript + Svelte 5)
	$(NODE) check

# ── Integration Tests ─────────────────────────────────────────────────────────
test-integration: ## Integration: E2E cross-component tests (auto-starts engine)
	$(PYTHON) pytest ../tests/integration/ -x -v

# ── Lint / Type Check ────────────────────────────────────────────────────────
lint: lint-engine lint-cli lint-web ## Run all linters + type checks

lint-engine: ## Engine: ruff + mypy
	$(PYTHON) ruff check .
	$(PYTHON) mypy resumeforge/

lint-cli: ## CLI: go vet
	$(GO) vet ./...

lint-web: ## Web: svelte-check
	$(NODE) check

fmt: ## Auto-format engine (ruff) + CLI (go fmt)
	$(PYTHON) ruff format .
	$(GO) fmt ./...

# ── Build ────────────────────────────────────────────────────────────────────
build-cli: ## CLI: build binary (./resumeforge)
	$(GO) build -o resumeforge .

build-web: ## Web: production build
	$(NODE) build
