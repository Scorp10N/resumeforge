# ResumeForge — Claude Code Project Setup v2.0

## 1. CLAUDE.md (Root)

```markdown
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
```

---

## 2. Sub-directory CLAUDE.md files

### engine/resumeforge/api/CLAUDE.md

```markdown
# Engine API Module

FastAPI REST API — the single interface between all clients and the engine.

## Key files
- `app.py` — FastAPI application, CORS, middleware, OpenAPI config
- `routes/build.py` — Resume build endpoint + SSE streaming
- `routes/tailor.py` — AI tailoring endpoint + SSE streaming
- `routes/analyze.py` — Analysis endpoints
- `routes/data.py` — CRUD for all data sections
- `routes/templates.py` — Template list and preview

## Rules
- All responses use Pydantic response models — no raw dicts
- Streaming responses use SSE (Server-Sent Events) via `StreamingResponse`
- Errors return structured JSON: `{"detail": "message", "code": "ERROR_CODE"}`
- OpenAPI tags match component names (Build, Tailor, Analyze, Data, Templates)
- CORS allows localhost ports for CLI and web dev server
- Test with: `uv run pytest tests/test_api.py -x`
```

### engine/resumeforge/data/CLAUDE.md

```markdown
# Data Store Module

JSON-based storage with Pydantic validation. Files live in `engine/data/`.

## Key files
- `schema.py` — ALL Pydantic models (Profile, Experience, Skills, Education, Meta, JobDescription)
- `store.py` — Read/write operations, handles schema_version migration
- `migrations.py` — Schema version upgrade functions

## Rules
- Every JSON field maps to a Pydantic model field — no loose dicts
- All dates use ISO 8601 strings (YYYY-MM or YYYY-MM-DD)
- `store.py` must never import from ai/, export/, or analysis/
- Test with: `uv run pytest tests/test_data.py -x`
```

### engine/resumeforge/ai/CLAUDE.md

```markdown
# AI Provider Module

LiteLLM-based AI integration. All prompts are Jinja2 templates in prompts/.

## Key files
- `provider.py` — LiteLLM wrapper, reads config from meta.json
- `rewriter.py` — Section rewriting with style control
- `tailor.py` — Match resume to job description
- `style.py` — StyleController class (tone, bullet format, etc.)
- `prompts/*.j2` — Prompt templates

## Rules
- NEVER hardcode model names — always read from config
- Every AI call must have a non-AI fallback (return input unchanged)
- Prompt templates receive a context dict — document expected keys in each .j2
- Temperature, max_tokens controlled via meta.json, never hardcoded
- Test with: `uv run pytest tests/test_ai.py -x` (uses mock provider)
```

### engine/resumeforge/export/CLAUDE.md

```markdown
# Export Engine

Renders resume data into MD, PDF, DOCX formats via templates.

## Key files
- `base.py` — BaseExporter ABC
- `markdown.py` — Jinja2 markdown rendering
- `pdf.py` — WeasyPrint (HTML → PDF)
- `docx_export.py` — python-docx programmatic builder

## Rules
- All exporters implement `export(context, template, output_path) -> Path`
- Templates live in `resumeforge/templates/{name}/`
- DOCX: NEVER use unicode bullets, use python-docx numbering
- PDF: all styling via CSS, no inline styles
- Test with: `uv run pytest tests/test_export.py -x`
```

### engine/resumeforge/analysis/CLAUDE.md

```markdown
# Analysis Engine

Quality checks on generated resumes producing a unified report.

## Key files
- `base.py` — BaseAnalyzer ABC + AnalysisResult model
- `ats_score.py` — Keyword matching against job description
- `gap_analysis.py` — Missing skills detector
- `quantification.py` — Counts metrics/numbers in bullets
- `readability.py` — Length, structure, formatting checks
- `grammar.py` — AI-assisted language quality (optional)
- `report.py` — Aggregates all results into markdown report

## Rules
- Every analyzer returns `AnalysisResult(score, max_score, findings, severity)`
- Non-AI analyzers must work offline — no network calls
- grammar.py is the ONLY analyzer that uses the AI provider
- Test with: `uv run pytest tests/test_analysis.py -x`
```

### cli/CLAUDE.md

```markdown
# CLI / TUI Client

Go application. Cobra CLI + Bubble Tea TUI. Communicates with engine via HTTP.

## Key packages
- `cmd/` — Cobra command definitions (one file per command group)
- `tui/` — Bubble Tea TUI application and screens
- `client/` — Typed HTTP client for engine REST API

## Rules
- ALL engine communication goes through the `client` package
- Never use raw http.Get/Post in cmd/ or tui/ — always client.Client methods
- CLI spawns the Python engine if not running, via `client.EnsureEngine()`
- Cobra commands return errors — never os.Exit() inside a command
- SSE streaming: use `client.StreamBuild()` which returns a channel of events
- Build with: `go build -o resumeforge ./...`
- Test with: `go test ./...`
```

### web/CLAUDE.md

```markdown
# Web Frontend Client

SvelteKit application. Communicates with engine via REST API + SSE.

## Key directories
- `src/routes/` — SvelteKit file-based pages
- `src/lib/components/` — Reusable Svelte components
- `src/lib/api/engine.ts` — Typed engine API client (all fetch calls here)
- `src/lib/api/types.ts` — TypeScript types matching engine OpenAPI schema

## Rules
- ALL engine API calls go through `src/lib/api/engine.ts` — never inline fetch
- Use Svelte 5 Runes: `$state()`, `$derived()`, `$effect()` — NOT legacy stores
- SSE handled via `engine.streamBuild()` which returns an async iterable
- Engine base URL read from `VITE_ENGINE_URL` env var (defaults to localhost:8080)
- TailwindCSS only — no custom CSS unless absolutely necessary
- Run type check with: `npm run check`
```

---

## 3. Custom Commands

### .claude/commands/phase.md
```markdown
Check DESIGN.md for the current build phase and summarize:
1. What's been completed across engine/, cli/, and web/
2. What remains for this phase
3. Suggested next task and which component it affects
Do NOT start coding — just report status.
```

### .claude/commands/engine-route.md
```markdown
Create a new engine API route for $ARGUMENTS:
1. Read engine/resumeforge/api/CLAUDE.md for conventions
2. Add route file in engine/resumeforge/api/routes/$ARGUMENTS.py
3. Register in engine/resumeforge/api/app.py
4. Add Pydantic request/response models
5. Write tests in engine/tests/test_api.py
6. Run tests and fix until green
```

### .claude/commands/cli-command.md
```markdown
Create a new CLI command for $ARGUMENTS:
1. Read cli/CLAUDE.md for conventions
2. Create cli/cmd/$ARGUMENTS.go with Cobra command
3. Add any required client methods to cli/client/client.go
4. Register command in cli/cmd/root.go
5. Write tests
6. Run: go test ./...
```

### .claude/commands/new-exporter.md
```markdown
Create a new engine exporter for format $ARGUMENTS:
1. Read engine/resumeforge/export/CLAUDE.md
2. Read base.py for the interface
3. Create engine/resumeforge/export/$ARGUMENTS.py
4. Add tests in engine/tests/test_export.py
5. Register in export/__init__.py
```

### .claude/commands/new-analyzer.md
```markdown
Create a new engine analyzer called $ARGUMENTS:
1. Read engine/resumeforge/analysis/CLAUDE.md
2. Read base.py for the interface
3. Create engine/resumeforge/analysis/$ARGUMENTS.py
4. Add tests in engine/tests/test_analysis.py
5. Register in analysis/__init__.py
```

### .claude/commands/lint-fix.md
```markdown
Run the full quality suite for all components:
Engine: uv run ruff check . --fix && uv run ruff format . && uv run mypy resumeforge/
CLI: go fmt ./... && go vet ./...
Web: npm run check
Report remaining issues that need manual attention.
```

---

## 4. Sub-Agents

### Agent: engine-data-architect
**Purpose:** Build data layer — Pydantic models, JSON store, migrations

```
0. Use find-docs to fetch current Pydantic v2 docs (field validators, model_config, model_validator) before writing any models.
Read DESIGN.md sections "Data Model" and "Repository Structure"
- Create all Pydantic models in engine/resumeforge/data/schema.py
- Create engine/resumeforge/data/store.py with CRUD operations
- Create sample data files in engine/data/
- Write tests in engine/tests/test_data.py
- Run tests and fix until green
Output: schema.py, store.py, sample JSON, passing tests
```

---

### Agent: engine-api-builder
**Purpose:** Build FastAPI REST API layer

```
0. Use find-docs to fetch current FastAPI docs (StreamingResponse, SSE patterns, Depends, response_model) and Pydantic v2 response model patterns before writing any routes.
Read DESIGN.md section "Engine API Contract"
- Create engine/resumeforge/api/app.py (FastAPI app, CORS, OpenAPI)
- Implement all routes from DESIGN.md: build, tailor, analyze, data, templates
- SSE streaming for build and tailor endpoints
- Write tests using FastAPI TestClient in engine/tests/test_api.py
- Run tests and fix until green
Output: app.py, all route files, passing API tests
```

---

### Agent: engine-export
**Purpose:** Build export pipeline

```
0. Use find-docs to fetch current python-docx docs (Document, Paragraph, Run, styles) and WeasyPrint docs (HTML/CSS to PDF) before implementing exporters.
Read DESIGN.md sections "Export Engine" and "Template System"
- Create BaseExporter ABC in engine/resumeforge/export/base.py
- Implement MarkdownExporter, PdfExporter, DocxExporter
- Create the "classic" template in engine/resumeforge/templates/classic/
- Write snapshot tests in engine/tests/test_export.py
- Run tests and fix until green
Output: base.py, 3 exporters, classic template, passing tests
```

---

### Agent: engine-ai
**Purpose:** Build AI provider layer

```
0. Use find-docs to fetch current LiteLLM docs (completion(), acompletion(), provider routing, model name formats) before writing the provider wrapper.
Read DESIGN.md section "AI Provider Layer"
- Create engine/resumeforge/ai/provider.py wrapping LiteLLM
- Create all prompt templates in engine/resumeforge/ai/prompts/
- Implement rewriter.py, tailor.py, style.py
- Ensure every function works with ai.enabled=false
- Write tests with mocked LiteLLM in engine/tests/test_ai.py
Output: provider.py, prompt templates, rewriter/tailor/style, passing tests
```

---

### Agent: engine-analysis
**Purpose:** Build all 5 analyzers and report generator

```
Read DESIGN.md section "Analysis Engine"
- Create BaseAnalyzer ABC in engine/resumeforge/analysis/base.py
- Implement: ats_score.py, gap_analysis.py, quantification.py, readability.py, grammar.py
- Create report.py to aggregate all results
- Write tests for each analyzer independently
Output: base.py, 5 analyzers, report.py, passing tests
```

---

### Agent: cli-builder
**Purpose:** Build the Go CLI (Cobra commands + engine client)

```
Read DESIGN.md sections "CLI" and "Engine API Contract"
Read cli/CLAUDE.md for conventions
- Set up Go module in cli/go.mod
- Implement cli/client/client.go — typed HTTP client for all engine endpoints
- Implement cli/client/engine.go — EnsureEngine() to auto-spawn Python engine
- Create all Cobra commands in cli/cmd/ (build, tailor, analyze, data, templates, config)
- Wire commands to client package
- Write tests using Cobra's command testing helpers
Output: go.mod, client package, cmd package, goreleaser.yml, passing tests
```

---

### Agent: tui-builder
**Purpose:** Build the Go TUI (Bubble Tea screens)

```
0. Use find-docs to fetch current Bubble Tea v1.1.0 docs (Model interface, Update/View/Init, Cmd, Msg patterns) and Lip Gloss v0.13.0 docs (Style, NewStyle, rendering) — the project uses these specific versions which have breaking changes from earlier releases.
Read DESIGN.md section "TUI"
Read cli/CLAUDE.md for conventions
- Create cli/tui/app.go as main Bubble Tea application
- Implement screens: dashboard.go, editor.go, jobmatcher.go, analysis.go
- Wire to cli/client/ for all engine data
- SSE streaming for live ATS score updates
- Manual testing instructions (no automated TUI tests for v1)
Output: tui app.go, screen modules, manual test guide
```

---

### Agent: web-builder
**Purpose:** Build the SvelteKit web frontend

```
0. Use find-docs to fetch current Svelte 5 Runes docs ($state, $derived, $effect, $props syntax) and SvelteKit docs (routing, load functions, SSE/streaming) before writing any components or pages — Svelte 5 Runes are a post-training-cutoff API and will be hallucinated incorrectly without docs.
Read DESIGN.md sections "Web Frontend" and "Engine API Contract"
Read web/CLAUDE.md for conventions
- Set up SvelteKit project in web/ (npm create svelte@latest)
- Create src/lib/api/engine.ts — typed fetch wrappers for all engine endpoints
- Generate TypeScript types from engine OpenAPI spec
- Implement all routes from DESIGN.md
- Build components: ResumePreview, SectionEditor, ATSScore, TemplatePicker
- SSE streaming for build progress and live ATS scoring
- Write tests using Playwright or Vitest
Output: full SvelteKit app, typed API client, components, passing tests
```

---

### Agent: qa-reviewer
**Purpose:** Cross-cutting quality review after each phase

```
Run full test suites:
  Engine: uv run pytest -x -v
  CLI: go test ./...
  Web: npm run check && npm run test

Run linters:
  Engine: uv run ruff check . && uv run mypy resumeforge/
  CLI: go vet ./...

Security checks:
  - engine/data/profile.json is in .gitignore
  - No API keys hardcoded anywhere
  - All AI functions have ai.enabled=false fallbacks
  - Go CLI uses only client package for engine calls

Report: passing/failing tests, lint issues, type errors, security concerns
```

---

## 5. Recommended Build Order

```
Phase 1 — Engine Foundation:
  1. engine-data-architect    ← schemas and store
  2. engine-api-builder       ← REST API layer (depends on data)
  3. engine-export            ← can run in parallel with API
  4. qa-reviewer

Phase 2 — Go CLI:
  5. cli-builder              ← Cobra + engine HTTP client
  6. qa-reviewer

Phase 3 — AI + Analysis:
  7. engine-ai                ← can run in parallel
  8. engine-analysis          ← can run in parallel
  9. qa-reviewer

Phase 4 — Go TUI:
  10. tui-builder
  11. qa-reviewer

Phase 5 — Web Frontend:
  12. web-builder
  13. qa-reviewer

Phase 6 — Templates + i18n:
  14. i18n + additional templates
  15. qa-reviewer
```

Steps 7+8 can run in parallel. Steps 3+4 (from Phase 1) can run in parallel after data-architect completes.

---

## 6. Git Workflow

```
main                        ← stable, always passes all tests
├── phase-1/engine-data     ← engine-data-architect agent
├── phase-1/engine-api      ← engine-api-builder agent
├── phase-1/engine-export   ← engine-export agent (parallel)
├── phase-2/cli             ← cli-builder agent
├── phase-3/engine-ai       ← engine-ai agent (parallel)
├── phase-3/engine-analysis ← engine-analysis agent (parallel)
├── phase-4/tui             ← tui-builder agent
└── phase-5/web             ← web-builder agent
```

Each agent works on its own branch. Merge to main after qa-reviewer passes.
