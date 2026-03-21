# ResumeForge — Roadmap

**Status:** Phase 6 in progress

Legend: ✅ Complete · 🔄 In Progress · ⬜ Planned

---

## Phase 1 — Engine Foundation ✅

Core Python engine with data store, build pipeline, REST API, and first template.

- [x] Pydantic v2 data models (`schema.py`) + JSON store (`store.py`)
- [x] Core resume builder (`core/builder.py`) assembles `ResumeContext`
- [x] Export engine: Markdown + DOCX exporters
- [x] FastAPI REST API — build, analyze, data, templates, jobs, config endpoints
- [x] "classic" template (HTML/MD/DOCX)
- [x] Basic ATS keyword analysis

---

## Phase 2 — Go CLI ✅

Single-binary Go client with all Cobra commands and engine auto-spawn.

- [x] Go module + Cobra CLI (`cmd/`: build, tailor, analyze, data, templates, config)
- [x] Typed HTTP client for engine API (`client/client.go`, `client/models.go`)
- [x] Engine auto-spawn — starts local engine if not running (`client/engine.go`)
- [x] GoReleaser config for cross-platform distribution (`.goreleaser.yml`)
- [x] Unit tests for client package

---

## Phase 3 — AI + Full Analysis ✅

LiteLLM AI integration and complete 5-analyzer quality suite.

- [x] LiteLLM provider wrapper (`ai/provider.py`) — any OpenAI-compatible API
- [x] AI rewriter, tailor, style controller
- [x] 6 Jinja2 prompt templates (rewrite, tailor, translate, analyze, suggest_bullets, gap_fill)
- [x] 5 analyzers: ATS score, gap analysis, quantification, readability, grammar (AI-assisted)
- [x] Report generator — aggregates all analyzer results into markdown
- [x] PDF export (WeasyPrint HTML → PDF)

---

## Phase 4 — Go TUI ✅

Bubble Tea TUI with 4 screens and live SSE streaming.

- [x] `tui/app.go` — main Bubble Tea application
- [x] Dashboard screen — data overview and quick actions
- [x] Editor screen — section editor with Markdown preview
- [x] Job Matcher screen — paste JD, live ATS score via SSE
- [x] Analysis screen — full report with expandable sections

---

## Phase 5 — SvelteKit Web Frontend ✅

Full SvelteKit web client with typed API client and all routes.

- [x] SvelteKit 2 + Svelte 5 Runes + TailwindCSS 4 + TypeScript
- [x] Typed engine API client (`src/lib/api/engine.ts`) + types (`types.ts`)
- [x] 8 routes: Dashboard, Builder, Preview, Analyze, Data, Templates, Jobs, Settings
- [x] 4 components: ATSScore, TemplatePicker, SectionEditor, ResumePreview
- [x] SSE streaming for build progress and live ATS scoring

---

## Phase 6 — Templates + i18n 🔄

Additional templates and multi-language support.

- [ ] `modern` template — two-column layout, accent color sidebar
- [ ] `minimal` template — clean single-column, maximum whitespace
- [ ] `executive` template — premium single-column for senior roles
- [ ] Babel i18n infrastructure — `.po` message catalogs for en and he
- [ ] Locale-aware date formatting (`format_date` utility)
- [ ] Section label translations integrated into all templates

---

## Phase 7 — Cloud Edition Foundation ⬜

Authentication, cloud storage, and plugin system.

- [ ] JWT authentication layer
- [ ] PostgreSQL backend (replaces JSON files)
- [ ] Plugin system interface
- [ ] DB Connector plugin
- [ ] RAG Connector plugin (retrieval-augmented resume generation)
- [ ] Multi-user isolation and team features

---

## Infrastructure ✅

Testing, CI, and developer tooling.

- [x] Root `Makefile` — unified `make test / make dev / make lint` interface
- [x] `Procfile` + honcho — `make dev` starts all services, `Ctrl+C` stops cleanly
- [x] `tests/integration/` — cross-component E2E tests (auto-starts engine)
- [x] `.github/workflows/ci.yml` — parallel CI jobs for engine, CLI, web
- [x] Component READMEs with interactive + non-interactive testing guides
