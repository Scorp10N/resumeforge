# ResumeForge — Claude Code Project Setup

## 1. CLAUDE.md (Root)

```markdown
# ResumeForge

Python CLI/TUI/Web tool for automated resume building with AI-powered tailoring.

## Project
- Python 3.12+, managed with uv
- Monorepo: single package `resumeforge/`
- Design spec: see DESIGN.md for full architecture

## Commands
- `uv run pytest` — run all tests
- `uv run pytest tests/{module}/ -x` — run one module, stop on first fail
- `uv run ruff check .` — lint
- `uv run ruff format .` — format
- `uv run mypy resumeforge/` — type check
- `uv run resumeforge --help` — run CLI

## Code Style
- Type hints on ALL functions (mypy strict)
- Pydantic v2 models for all data schemas
- ABC base classes for pluggable interfaces (exporters, analyzers, providers)
- Docstrings: Google style, one-liner for simple functions
- Imports: stdlib → third-party → local, separated by blank line
- No `Any` types. No bare `except`. No mutable default args.
- Tests: pytest + pytest-snapshot. Every public function needs a test.

## Architecture
- `resumeforge/core/` — shared engine (builder, sections, templates, i18n)
- `resumeforge/data/` — JSON store + Pydantic schemas
- `resumeforge/ai/` — LiteLLM wrapper + prompt templates
- `resumeforge/export/` — MD/PDF/DOCX exporters
- `resumeforge/analysis/` — ATS scoring, gap analysis, quality checks
- `resumeforge/cli/` — Typer CLI
- `resumeforge/tui/` — Textual TUI
- `resumeforge/web/` — FastAPI + HTMX web UI

## Important
- NEVER commit data/profile.json (PII) — it is gitignored
- All exporters inherit from `BaseExporter` in export/base.py
- All analyzers inherit from `BaseAnalyzer` in analysis/base.py
- AI is optional — everything must work with `ai.enabled: false`
- JSON schema versions: always check `schema_version` field
- When compacting, preserve: list of modified files, failing tests, current phase goal
```

---

## 2. Sub-directory CLAUDE.md files

### resumeforge/data/CLAUDE.md

```markdown
# Data Store Module

JSON-based storage with Pydantic validation. Files live in `data/` at project root.

## Key files
- `schema.py` — ALL Pydantic models (Profile, Experience, Skills, Education, Meta, JobDescription)
- `store.py` — Read/write operations, handles schema_version migration
- `migrations.py` — Schema version upgrade functions

## Rules
- Every JSON field maps to a Pydantic model field — no loose dicts
- All dates use ISO 8601 strings (YYYY-MM or YYYY-MM-DD), parsed via `date` or `Optional[date]`
- `store.py` must never import from ai/, export/, or analysis/
- Test with: `uv run pytest tests/test_data.py -x`
```

### resumeforge/ai/CLAUDE.md

```markdown
# AI Provider Module

LiteLLM-based AI integration. All prompts are Jinja2 templates in `prompts/`.

## Key files
- `provider.py` — LiteLLM wrapper, reads config from meta.json
- `rewriter.py` — Section rewriting with style control
- `tailor.py` — Match resume to job description
- `style.py` — StyleController class (tone, bullet format, etc.)
- `prompts/*.j2` — Prompt templates

## Rules
- NEVER hardcode model names — always read from config
- Every AI call must have a non-AI fallback (return input unchanged)
- Prompt templates receive a `context` dict — document expected keys in each .j2 file
- Temperature, max_tokens controlled via meta.json, never hardcoded
- Test with: `uv run pytest tests/test_ai.py -x` (uses mock provider)
```

### resumeforge/export/CLAUDE.md

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
- DOCX builder: NEVER use unicode bullets, use python-docx numbering
- PDF: all styling via CSS, no inline styles
- Test with: `uv run pytest tests/test_export.py -x`
- Validate DOCX output opens correctly in LibreOffice
```

### resumeforge/analysis/CLAUDE.md

```markdown
# Analysis Engine

Runs quality checks on generated resumes and produces reports.

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

---

## 3. Custom Commands

### .claude/commands/phase.md
```markdown
Check DESIGN.md for the current build phase and summarize:
1. What's been completed
2. What remains for this phase
3. Suggested next task
Do NOT start coding — just report status.
```

### .claude/commands/test-module.md
```markdown
Run tests for $ARGUMENTS module:
1. `uv run pytest tests/test_$ARGUMENTS.py -x -v`
2. If failures, show the failing test and the relevant source
3. Suggest a fix but do NOT apply it without my approval
```

### .claude/commands/lint-fix.md
```markdown
Run the full quality suite and fix issues:
1. `uv run ruff check . --fix`
2. `uv run ruff format .`
3. `uv run mypy resumeforge/`
4. Report remaining issues that need manual attention
```

### .claude/commands/new-exporter.md
```markdown
Create a new exporter for the $ARGUMENTS format:
1. Read `resumeforge/export/base.py` for the interface
2. Read an existing exporter (markdown.py) for the pattern
3. Create `resumeforge/export/$ARGUMENTS.py`
4. Add tests in `tests/test_export.py`
5. Register in export/__init__.py
```

### .claude/commands/new-analyzer.md
```markdown
Create a new analyzer called $ARGUMENTS:
1. Read `resumeforge/analysis/base.py` for the interface
2. Read an existing analyzer for the pattern
3. Create `resumeforge/analysis/$ARGUMENTS.py`
4. Add tests in `tests/test_analysis.py`
5. Register in analysis/__init__.py
```

---

## 4. Sub-Agents

Sub-agents keep the main context clean by delegating focused tasks. Each agent has a specific role, skills, and output contract.

### Agent: data-architect

**Purpose:** Build and maintain the data layer (Pydantic models, JSON store, migrations)

**Skills needed:**
- Pydantic v2 (model_validator, field_validator, discriminated unions)
- JSON schema design
- Data migration patterns

**Trigger:**
```
Use a subagent to build the data layer:
- Read DESIGN.md sections "Data model" and "Directory structure"
- Create all Pydantic models in resumeforge/data/schema.py
- Create resumeforge/data/store.py with CRUD operations
- Create sample data files in data/
- Write tests in tests/test_data.py
- Run tests and fix until green
```

**Output contract:** schema.py, store.py, sample JSON files, passing tests

---

### Agent: export-engine

**Purpose:** Build the export pipeline (base class + MD/PDF/DOCX exporters)

**Skills needed:**
- python-docx (programmatic document building, NOT template-based)
- WeasyPrint (HTML/CSS → PDF)
- Jinja2 template rendering
- ABC pattern in Python

**Trigger:**
```
Use a subagent to build the export engine:
- Read DESIGN.md section "Export engine" and "Template system"
- Create BaseExporter ABC in resumeforge/export/base.py
- Implement MarkdownExporter, PdfExporter, DocxExporter
- Create the "classic" template in resumeforge/templates/classic/
- Write tests in tests/test_export.py using snapshot testing
- Run tests and fix until green
```

**Output contract:** base.py, 3 exporters, classic template, passing tests

---

### Agent: ai-integrator

**Purpose:** Build the AI provider layer (LiteLLM wrapper, prompts, rewriter, tailor)

**Skills needed:**
- LiteLLM API (completion, model routing, error handling)
- Jinja2 prompt templating
- Structured output parsing from LLMs
- Graceful degradation (AI-off fallback)

**Trigger:**
```
Use a subagent to build the AI integration:
- Read DESIGN.md section "AI provider layer"
- Create provider.py wrapping LiteLLM with config from meta.json
- Create all prompt templates in resumeforge/ai/prompts/
- Implement rewriter.py, tailor.py, style.py
- Ensure EVERY function works when ai.enabled=false (returns input unchanged)
- Write tests with mocked LiteLLM responses
- Run tests and fix until green
```

**Output contract:** provider.py, prompt templates, rewriter/tailor/style modules, passing tests with mocks

---

### Agent: analysis-suite

**Purpose:** Build all 5 analyzers + report generator

**Skills needed:**
- Text analysis (keyword extraction, counting, regex)
- NLP basics (tokenization for readability scoring)
- Markdown report generation
- Scoring/grading logic

**Trigger:**
```
Use a subagent to build the analysis engine:
- Read DESIGN.md section "Analysis engine"
- Create BaseAnalyzer ABC in resumeforge/analysis/base.py
- Implement: ats_score.py, gap_analysis.py, quantification.py, readability.py, grammar.py
- Create report.py to aggregate all results
- Write tests for each analyzer independently
- Run tests and fix until green
```

**Output contract:** base.py, 5 analyzers, report.py, passing tests

---

### Agent: cli-builder

**Purpose:** Build the Typer CLI interface

**Skills needed:**
- Typer (commands, options, arguments, callbacks)
- Rich (tables, panels, progress bars, markdown rendering)
- Click testing (CliRunner)

**Trigger:**
```
Use a subagent to build the CLI:
- Read DESIGN.md section "Interface specifications — CLI"
- Create resumeforge/cli/app.py as the main entrypoint
- Implement all commands: build, tailor, analyze, templates, data, config
- Wire commands to core engine, export engine, and analysis engine
- Write tests using Typer's CliRunner
- Run tests and fix until green
```

**Output contract:** cli app.py, command modules, passing CLI tests

---

### Agent: tui-builder

**Purpose:** Build the Textual TUI interface

**Skills needed:**
- Textual framework (screens, widgets, bindings, CSS)
- Async Python (Textual is async-first)
- Rich renderables inside Textual

**Trigger:**
```
Use a subagent to build the TUI:
- Read DESIGN.md section "Interface specifications — TUI"
- Create resumeforge/tui/app.py as the main TUI application
- Implement screens: dashboard, editor (split-pane), analysis viewer
- Wire to core engine for live preview
- Manual testing instructions (no automated TUI tests for v1)
```

**Output contract:** tui app.py, screen modules, manual test instructions

---

### Agent: web-builder

**Purpose:** Build the FastAPI + HTMX web interface

**Skills needed:**
- FastAPI (routes, templates, SSE streaming)
- HTMX (partial updates, triggers, swap strategies)
- Jinja2 HTML templates (for web UI, not resume templates)
- Basic CSS (no framework needed, keep it simple)

**Trigger:**
```
Use a subagent to build the web UI:
- Read DESIGN.md section "Interface specifications — Web UI"
- Create resumeforge/web/app.py with FastAPI
- Implement routes: builder, analysis, data viewer
- Create HTMX-powered templates for live interaction
- Wire to core engine for resume building and analysis
- Write tests using FastAPI TestClient
- Run tests and fix until green
```

**Output contract:** web app.py, routes, HTML templates, static CSS, passing tests

---

### Agent: i18n-specialist

**Purpose:** Add multi-language and RTL support

**Skills needed:**
- Babel (message extraction, .po files, locale formatting)
- RTL CSS (direction, text-align, mirrored layouts)
- Hebrew typography and date formatting

**Trigger:**
```
Use a subagent to add i18n support:
- Read DESIGN.md section "Multi-language support"
- Create resumeforge/core/i18n.py with Babel integration
- Create locale files for en and he
- Add RTL detection and CSS support to HTML/PDF templates
- Update all section headers to use translated strings
- Add --lang flag to CLI build command
- Write tests for both locales
```

**Output contract:** i18n.py, locale files, RTL-aware templates, passing tests

---

### Agent: qa-reviewer

**Purpose:** Cross-cutting quality review after each phase

**Skills needed:**
- Python testing best practices
- Security review (PII leaks, API key handling)
- Code consistency checking

**Trigger (after each phase):**
```
Use a subagent to do a quality review:
- Run full test suite: uv run pytest -x -v
- Run linter: uv run ruff check .
- Run type checker: uv run mypy resumeforge/
- Check that data/profile.json is in .gitignore
- Check that no API keys are hardcoded anywhere
- Check that all AI functions have ai.enabled=false fallbacks
- Report: passing/failing tests, lint issues, type errors, security concerns
```

**Output contract:** QA report with pass/fail per category

---

## 5. Recommended Build Order

```
Phase 1 (Foundation):
  1. data-architect     ← start here, everything depends on schemas
  2. export-engine      ← can run in parallel once schemas exist
  3. cli-builder        ← wire it together
  4. qa-reviewer        ← validate phase 1

Phase 2 (Intelligence):
  5. ai-integrator      ← adds AI capabilities
  6. analysis-suite     ← can run in parallel with AI
  7. qa-reviewer        ← validate phase 2

Phase 3 (Templates + i18n):
  8. i18n-specialist    ← adds language support
  9. qa-reviewer        ← validate phase 3

Phase 4 (Interfaces):
  10. tui-builder       ← can run in parallel
  11. web-builder       ← can run in parallel
  12. qa-reviewer       ← final validation
```

Agents 2+3 can run in parallel. Agents 5+6 can run in parallel. Agents 10+11 can run in parallel.

---

## 6. Git Workflow

```bash
main                  ← stable, always passes tests
├── phase-1/data      ← data-architect agent
├── phase-1/export    ← export-engine agent (parallel)
├── phase-1/cli       ← cli-builder (after data + export merge)
├── phase-2/ai        ← ai-integrator
├── phase-2/analysis  ← analysis-suite (parallel)
├── phase-3/i18n      ← i18n-specialist
├── phase-4/tui       ← tui-builder (parallel)
└── phase-4/web       ← web-builder (parallel)
```

Each agent works on its own branch. Merge to main after qa-reviewer passes.
