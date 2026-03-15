# ResumeForge — Design Document v2.0

## Project Overview

**ResumeForge** is an open-source resume automation platform that separates resume content from presentation, enabling rapid building, tailoring, and exporting of resumes for specific roles. It features pluggable AI editing, multi-format export, multi-language support, and automated quality analysis.

The platform is built as a **polyglot system** with clearly separated standalone clients and a central engine, forming the foundation for both a free community edition and a commercial cloud edition.

---

## Business Model — Two Editions

| | **Community (OSS)** | **Cloud (Commercial)** |
|---|---|---|
| **License** | MIT / Apache 2.0 | Proprietary SaaS |
| **Core Engine** | Runs locally, self-hosted | Hosted and managed |
| **Features** | Build · Edit · Export · Basic Analysis · Templates | Everything in OSS + Plugin Store |
| **AI** | BYO API key (LiteLLM, any provider) | Managed AI with multi-provider support |
| **Storage** | Local JSON files | Cloud DB (PostgreSQL) |
| **Plugins** | Not supported | Plugin Store (see below) |
| **Multi-user** | No — single user | Yes — auth, teams, data isolation |
| **Clients** | CLI/TUI + Web Frontend (OSS) | Same OSS clients + cloud engine |

### Cloud Plugin Store

| Plugin | Description |
|--------|-------------|
| **DB Connector** | Connect to PostgreSQL, MongoDB, or custom stores |
| **RAG Connector** | Retrieval-Augmented Generation — search past resumes/docs to improve AI output |
| **ATS Repo** | Centralized ATS keyword database built from real job postings |
| **AI Tailoring Plus** | Advanced multi-provider AI tailoring with A/B testing |
| **LinkedIn Profile Enhancer** | Import/sync LinkedIn profile, AI-powered suggestions |
| **Cover Letter Generator** | AI cover letters from the same content pipeline |
| **Analytics Dashboard** | Track applications, response rates, tailoring history |

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        STANDALONE CLIENTS                           │
│                                                                     │
│  ┌──────────────────────────┐   ┌──────────────────────────────┐   │
│  │      CLI / TUI           │   │       Web Frontend           │   │
│  │      Go                  │   │       SvelteKit              │   │
│  │  Cobra + Bubble Tea      │   │  TypeScript + Svelte 5       │   │
│  │  Lip Gloss + Bubbles     │   │  TailwindCSS                 │   │
│  │  Single binary dist.     │   │  Vercel / Node deployment    │   │
│  └────────────┬─────────────┘   └──────────────┬───────────────┘   │
│               │                                │                    │
│               └───────────────┬────────────────┘                    │
│                               ▼                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Engine API  (OpenAPI / REST + SSE)               │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
       ┌────────────┐  ┌────────────┐  ┌────────────────┐
       │   LOCAL    │  │   CLOUD    │  │    HYBRID      │
       │   ENGINE   │  │   ENGINE   │  │ Local engine + │
       │  (Python)  │  │  (Python)  │  │ Cloud plugins  │
       │  FastAPI   │  │  FastAPI   │  │                │
       │  SQLite /  │  │ PostgreSQL │  │                │
       │  JSON      │  │ + Plugins  │  │                │
       └────────────┘  └────────────┘  └────────────────┘
```

### Technology Stack

| Component | Language | Key Libraries | Distribution |
|-----------|----------|--------------|-------------|
| **CLI / TUI** | Go | Cobra, Bubble Tea, Bubbles, Lip Gloss, Huh | Single binary (GoReleaser) |
| **Web Frontend** | TypeScript | SvelteKit, Svelte 5, TailwindCSS | npm / Docker / Vercel |
| **Core Engine** | Python | FastAPI, Pydantic v2, LiteLLM, Jinja2 | pip / uv / Docker |
| **Export Engine** | Python | python-docx, WeasyPrint, markdown-it-py | Part of engine |
| **Analysis Engine** | Python | Part of engine | Part of engine |

#### Why Go for CLI/TUI?
- **Single binary** — users run `resumeforge` with zero dependencies
- **~5ms startup** vs ~300ms for Python — critical for CLI UX
- **Cobra** is the standard for professional CLIs (Docker, kubectl, GitHub CLI, Hugo)
- **Bubble Tea** (Elm architecture) + **Lip Gloss** = the most cohesive TUI toolkit available
- **GoReleaser** trivialises cross-platform releases (Linux / macOS / Windows)

#### Why SvelteKit for Web?
- A resume builder requires **rich interactivity**: drag-and-drop, live preview, split-pane editor — HTMX cannot do this well
- Svelte 5 compiles to **vanilla JS** — smallest bundles and fastest DOM updates of any major framework
- **Scoped CSS** + TailwindCSS makes the premium commercial UI achievable
- **Typescript-first** with Svelte 5 Runes provides strong type safety end-to-end
- Cleanest separation from the Python engine — calls it via fetch/SSE

#### Why Python for the Engine?
- **AI ecosystem** — LiteLLM, LangChain, all major LLM SDKs are Python-first
- **Document generation** — python-docx and WeasyPrint are mature and battle-tested
- **Single dependency tree** — all engine logic in one package with one test suite
- **FastAPI** auto-generates OpenAPI docs consumed by both Go and SvelteKit clients

---

## Repository Structure

```
resumeforge/            ← Root (monorepo or separate repos per component)
│
├── engine/             ← Python: FastAPI core engine
│   ├── pyproject.toml
│   ├── resumeforge/
│   │   ├── api/                ← REST API routes (OpenAPI)
│   │   │   ├── routes/
│   │   │   │   ├── build.py
│   │   │   │   ├── tailor.py
│   │   │   │   ├── analyze.py
│   │   │   │   ├── data.py
│   │   │   │   └── templates.py
│   │   │   └── app.py          ← FastAPI application
│   │   ├── core/               ← Resume builder engine
│   │   │   ├── builder.py
│   │   │   ├── section.py
│   │   │   ├── template_engine.py
│   │   │   └── i18n.py
│   │   ├── data/               ← Data store layer
│   │   │   ├── schema.py       ← Pydantic models
│   │   │   ├── store.py
│   │   │   └── migrations.py
│   │   ├── ai/                 ← AI provider layer
│   │   │   ├── provider.py     ← LiteLLM wrapper
│   │   │   ├── rewriter.py
│   │   │   ├── tailor.py
│   │   │   ├── style.py
│   │   │   └── prompts/        ← Jinja2 prompt templates
│   │   │       ├── rewrite_section.j2
│   │   │       ├── tailor_to_job.j2
│   │   │       ├── translate.j2
│   │   │       └── analyze.j2
│   │   ├── export/             ← Export engine
│   │   │   ├── base.py
│   │   │   ├── markdown.py
│   │   │   ├── pdf.py
│   │   │   └── docx_export.py
│   │   ├── analysis/           ← Analysis engine
│   │   │   ├── base.py
│   │   │   ├── ats_score.py
│   │   │   ├── gap_analysis.py
│   │   │   ├── quantification.py
│   │   │   ├── readability.py
│   │   │   ├── grammar.py
│   │   │   └── report.py
│   │   └── templates/          ← Resume output templates
│   │       ├── classic/
│   │       │   ├── template.toml
│   │       │   ├── resume.md.j2
│   │       │   ├── resume.html.j2
│   │       │   └── resume.docx.py
│   │       ├── modern/
│   │       ├── minimal/
│   │       └── executive/
│   ├── data/                   ← User data (gitignored PII)
│   │   ├── profile.json
│   │   ├── experience.json
│   │   ├── skills.json
│   │   ├── education.json
│   │   ├── projects.json
│   │   ├── meta.json
│   │   └── jobs/
│   ├── output/                 ← Generated resumes
│   └── tests/
│
├── cli/                ← Go: CLI + TUI standalone client
│   ├── go.mod
│   ├── go.sum
│   ├── main.go
│   ├── cmd/                    ← Cobra commands
│   │   ├── root.go
│   │   ├── build.go
│   │   ├── tailor.go
│   │   ├── analyze.go
│   │   ├── data.go
│   │   ├── templates.go
│   │   └── config.go
│   ├── tui/                    ← Bubble Tea TUI application
│   │   ├── app.go
│   │   └── screens/
│   │       ├── dashboard.go
│   │       ├── editor.go
│   │       ├── jobmatcher.go
│   │       └── analysis.go
│   ├── client/                 ← HTTP client for engine API
│   │   ├── client.go
│   │   └── models.go           ← Go structs mirroring engine API
│   └── .goreleaser.yml
│
├── web/                ← SvelteKit: Web frontend standalone client
│   ├── package.json
│   ├── svelte.config.js
│   ├── vite.config.ts
│   ├── src/
│   │   ├── app.html
│   │   ├── routes/             ← SvelteKit file-based routing
│   │   │   ├── +layout.svelte
│   │   │   ├── +page.svelte    ← Dashboard
│   │   │   ├── builder/
│   │   │   ├── analyze/
│   │   │   ├── data/
│   │   │   └── templates/
│   │   ├── lib/
│   │   │   ├── components/     ← Reusable Svelte components
│   │   │   │   ├── ResumePreview.svelte
│   │   │   │   ├── SectionEditor.svelte
│   │   │   │   ├── ATSScore.svelte
│   │   │   │   └── TemplatePicker.svelte
│   │   │   └── api/            ← Engine API client (typed fetch)
│   │   │       ├── engine.ts
│   │   │       └── types.ts    ← TypeScript types from OpenAPI
│   │   └── app.css
│   └── static/
│
└── docs/               ← Shared documentation
    ├── api/            ← Engine API spec (OpenAPI JSON)
    └── architecture/
```

---

## Engine API Contract

The engine exposes a REST API consumed by both the Go CLI and the SvelteKit web frontend. FastAPI auto-generates the OpenAPI spec, from which Go structs and TypeScript types are generated.

### Core Endpoints

```
# Resume building
POST   /api/build                 → Build resume from data + template
GET    /api/build/stream          → SSE stream of build progress

# AI tailoring
POST   /api/tailor                → Tailor resume to job description
GET    /api/tailor/stream         → SSE stream of tailoring progress

# Analysis
POST   /api/analyze               → Run analysis suite
GET    /api/analyze/{job_slug}    → Get cached analysis

# Data management
GET    /api/data/{section}        → Get section data
PUT    /api/data/{section}        → Update section data
POST   /api/data/import           → Import backup
GET    /api/data/export           → Export backup as zip

# Templates
GET    /api/templates             → List available templates
GET    /api/templates/{name}/preview → Preview template (PDF bytes)

# Jobs
GET    /api/jobs                  → List saved job descriptions
POST   /api/jobs                  → Save new job description
GET    /api/jobs/{slug}           → Get job description
DELETE /api/jobs/{slug}           → Delete job description

# Config
GET    /api/config                → Get current config
PATCH  /api/config                → Update config fields
```

### Engine Startup Modes

```
# Run engine as a server (web frontend or remote CLI use)
resumeforge-engine --port 8080

# CLI launches engine as a local subprocess (transparent to user)
resumeforge build --template classic --format pdf
# ↑ Go CLI starts engine if not running, calls API, shuts down on exit

# Cloud mode: CLI connects to hosted engine
resumeforge --engine https://cloud.resumeforge.io build ...
```

---

## Data Model

All data is stored as JSON files in `engine/data/`. Each file maps to a Pydantic model.

### profile.json (PII — gitignored)

```json
{
  "schema_version": "1.0",
  "name": "Yarin Mor",
  "title": "Information Security Engineer | Security Architect",
  "email": "scorpyarin@gmail.com",
  "phone": "054-6390066",
  "linkedin": "linkedin.com/in/cyberquantumcat",
  "github": "",
  "website": "",
  "location": "Israel",
  "languages": ["en", "he"]
}
```

### experience.json

```json
{
  "schema_version": "1.0",
  "positions": [
    {
      "id": "scorp-2025",
      "company": "Scorp Solutions",
      "title": "Security Consultant (Freelance)",
      "start_date": "2025-03",
      "end_date": null,
      "is_current": true,
      "location": "Israel",
      "bullets": [
        {
          "id": "scorp-2025-1",
          "text": "Provide cloud security consulting, security architecture reviews, and penetration testing for diverse clients.",
          "tags": ["cloud-security", "pentest", "architecture"],
          "metrics": false
        }
      ],
      "tags": ["freelance", "consulting", "cloud", "appsec"],
      "priority": 1
    }
  ]
}
```

### skills.json

```json
{
  "schema_version": "1.0",
  "categories": [
    {
      "id": "cloud-security",
      "label": "Cloud Security",
      "items": ["AWS", "Azure", "GCP", "Office 365", "Prisma Cloud", "Aqua Security", "Snyk"],
      "priority": 1
    }
  ],
  "exploring": [
    {
      "label": "AI Security",
      "items": ["LangChain", "LangGraph", "Langfuse", "LiteLLM", "OpenTelemetry for AI"]
    }
  ]
}
```

### meta.json

```json
{
  "schema_version": "1.0",
  "default_locale": "en",
  "default_template": "classic",
  "default_format": "pdf",
  "engine": {
    "mode": "local",
    "url": null,
    "port": 8080
  },
  "ai": {
    "provider": "openai",
    "model": "gpt-4o",
    "base_url": null,
    "temperature": 0.3,
    "enabled": false
  },
  "style": {
    "tone": "professional",
    "max_pages": 1,
    "bullet_style": "action-verb-first",
    "avoid_tool_names_in_bullets": true
  }
}
```

### jobs/{job-slug}.json

```json
{
  "slug": "bank-appsec",
  "title": "Senior Application Security Guide",
  "company": "Major Israeli Bank",
  "description": "Full job description text...",
  "requirements": ["Application Security", "SAST/DAST", "Kubernetes", "Azure/GCP"],
  "nice_to_have": ["Penetration Testing", "CS Degree"],
  "language": "he",
  "saved_date": "2026-03-15",
  "notes": "Digital space project, banking sector"
}
```

---

## Template System

Each template is a self-contained directory in `engine/resumeforge/templates/`. Templates are engine-side only — both clients receive rendered output.

### template.toml

```toml
[template]
name = "Classic"
description = "Clean single-column layout, ATS-optimized"
author = "ResumeForge"
version = "1.0"
supported_formats = ["md", "pdf", "docx"]
max_pages = 2
ats_friendly = true

[style]
font_family = "Calibri"
font_size_body = 10
font_size_heading = 12
margin_top = 0.5
margin_sides = 0.75
color_primary = "#1F4E79"
color_accent = "#2E75B6"
color_text = "#333333"

[sections]
order = ["header", "summary", "competencies", "exploring", "experience", "education"]
```

### Template Rendering Flow

```
data/*.json ──→ Pydantic Models ──→ ResumeContext ──→ Jinja2 ──→ Format renderer
                                         ↑                          │
                                    i18n strings               ┌────┴────┐
                                                              MD   PDF  DOCX
```

---

## AI Provider Layer (Engine)

```
User Request ──→ AI Router (LiteLLM) ──→ Any OpenAI-compatible API
                      │
                 ┌────┴────────────────────┐
                 │  Prompt Templates (j2)   │
                 │  rewrite_section.j2      │
                 │  tailor_to_job.j2        │
                 │  translate.j2            │
                 │  analyze.j2              │
                 └─────────────────────────┘
```

### AI Capabilities

| Capability | Prompt | Description |
|-----------|--------|-------------|
| Rewrite section | `rewrite_section.j2` | Rewrite with tone/style control |
| Tailor to job | `tailor_to_job.j2` | Adapt resume to job description |
| Translate | `translate.j2` | Translate content to target locale |
| Analyze | `analyze.j2` | AI-assisted grammar and quality check |
| Suggest bullets | `suggest_bullets.j2` | Generate bullets from raw experience |
| Gap fill | `gap_fill.j2` | Suggest how to address skill gaps |

AI is **always optional** — every function must work with `ai.enabled: false`.

Supported providers via LiteLLM:

```python
# OpenAI
litellm.completion(model="gpt-4o", messages=[...])

# Anthropic
litellm.completion(model="claude-opus-4-20250514", messages=[...])

# Local Ollama
litellm.completion(model="ollama/llama3", messages=[...], api_base="http://localhost:11434")

# Azure OpenAI
litellm.completion(model="azure/gpt-4o", messages=[...], api_base="https://my-endpoint.openai.azure.com")
```

---

## Export Engine (Engine)

```python
from abc import ABC, abstractmethod

class BaseExporter(ABC):
    @abstractmethod
    def export(self, context: ResumeContext, template: Template, output_path: Path) -> Path:
        ...

class MarkdownExporter(BaseExporter): ...
class PdfExporter(BaseExporter): ...      # WeasyPrint: HTML → PDF
class DocxExporter(BaseExporter): ...     # python-docx programmatic builder
```

### Export Flow

```
POST /api/build

1. Load data/*.json → Pydantic models
2. Load job description (if job_slug provided)
3. [Optional] AI tailor sections to job
4. Build ResumeContext (merged, prioritized sections)
5. Apply i18n (locale-specific labels, date formatting, RTL)
6. Render through template + exporter
7. Save to output/{date}_{job-slug}/
8. Run analysis suite → save report
9. Return output file paths + analysis summary
```

---

## Analysis Engine (Engine)

| Analyzer | What it measures | Scoring |
|---------|-----------------|---------|
| **ATS keyword match** | Keywords from JD found in resume | % match, missing keywords |
| **Gap analysis** | Required skills in JD not in resume | Critical / nice-to-have gaps |
| **Quantification** | % of bullets containing metrics | Score + flagged weak bullets |
| **Readability** | Page count, bullet length, section balance | Pass / warn / fail per metric |
| **Grammar & quality** | Spelling, grammar, consistency (AI-assisted) | Issues list with severity |

---

## Client Specifications

### CLI (Go — Cobra)

```bash
# Build
resumeforge build --template classic --format pdf
resumeforge build --template modern --format docx --job bank-appsec --lang he

# Tailor
resumeforge tailor --job bank-appsec --ai
resumeforge tailor --job-file ./description.txt --ai --model claude-opus-4-20250514

# Analyze
resumeforge analyze --job bank-appsec
resumeforge analyze --format json

# Templates
resumeforge templates list
resumeforge templates preview classic --format pdf

# Data
resumeforge data show experience
resumeforge data edit experience --section scorp-2025
resumeforge data export --output backup.zip
resumeforge data import --input backup.zip

# Config
resumeforge config set ai.model gpt-4o
resumeforge config set ai.enabled true
resumeforge config set engine.url https://cloud.resumeforge.io

# Launch TUI
resumeforge tui
```

#### CLI → Engine Communication

```
resumeforge build ...
  ├── Check if local engine is running on meta.engine.port
  ├── If not → spawn engine process (python -m resumeforge.api.app)
  ├── Call POST /api/build
  ├── Stream SSE progress to terminal (Rich progress bar)
  └── Print output path on completion
```

### TUI (Go — Bubble Tea)

```bash
resumeforge tui
```

Screens (Bubble Tea):

- **Dashboard** — data overview, recent builds, quick actions
- **Editor** — split-pane section editor with live Markdown preview (rendered via Glow)
- **Job Matcher** — paste JD, watch ATS score update live via SSE
- **Analysis** — full report with expandable sections
- **Templates** — visual template browser with sample renders

### Web Frontend (SvelteKit)

Defaults to running at `http://localhost:5173` (dev) / port 3000 (prod).

Routes:

```
/                    ← Dashboard: recent builds, quick actions
/builder             ← Resume builder: template picker, format, job selector
/builder/preview     ← Live preview pane (PDF iframe / Markdown render)
/analyze             ← Analysis view with charts and recommendations
/data/[section]      ← View and edit section data (form-based)
/templates           ← Template gallery with preview
/jobs                ← Saved job descriptions
/settings            ← Config: AI, engine URL, style preferences
```

The SvelteKit frontend communicates with the engine API via typed fetch functions in `src/lib/api/engine.ts`.

---

## Multi-Language Support

- **Content translation:** AI-powered via `translate.j2` prompt template
- **UI labels:** Babel message catalogs (`.po` files) — section headers, report labels
- **Date formatting:** Locale-aware via Babel (`March 2025` vs `מרץ 2025`)
- **RTL support:** HTML/PDF templates detect RTL locales and apply `dir="rtl"` + CSS
- **Per-section language:** Each section can override the global locale

```
engine/resumeforge/locales/
  en/LC_MESSAGES/messages.po   ← "Professional Summary", "Core Competencies"
  he/LC_MESSAGES/messages.po   ← "תקציר מקצועי", "יכולות ליבה"
```

---

## Build Phases

### Phase 1 — Engine Foundation (MVP)
- Data store (JSON + Pydantic models)
- Core builder engine
- 1 template ("classic")
- Markdown + DOCX export
- Engine REST API (FastAPI, core endpoints)
- Basic ATS keyword analysis

### Phase 2 — Go CLI Client
- Cobra CLI with all commands
- Engine auto-spawn on first command
- Goreleaser multi-platform release
- Basic Rich progress output

### Phase 3 — AI + Full Analysis
- LiteLLM integration
- AI rewriting and tailoring
- Full analysis suite (5 analyzers)
- Report generator
- PDF export (WeasyPrint)

### Phase 4 — Go TUI
- Bubble Tea TUI screens (Dashboard, Editor, Job Matcher, Analysis)
- Live preview via Glow
- SSE streaming from engine

### Phase 5 — SvelteKit Web Frontend
- SvelteKit project setup
- All pages and components
- Resume preview component
- Typed API client from OpenAPI spec
- Live ATS scoring via SSE

### Phase 6 — Templates + i18n
- 3 additional templates (modern, minimal, executive)
- Multi-language support (en, he)
- RTL support

### Phase 7 — Cloud Edition Foundation
- Auth (JWT)
- PostgreSQL backend
- Plugin system interface
- First plugins: DB Connector, RAG Connector

---

## Security Considerations

- **PII isolation:** `engine/data/profile.json` is in `.gitignore`. Generated on `resumeforge init`.
- **AI data:** Resume content is sent to the configured AI provider when enabled. Local providers (Ollama) keep data on-machine. Warning shown on first cloud provider use.
- **No telemetry:** Zero analytics, tracking, or phone-home in the OSS edition.
- **API keys:** Stored in environment variables or `.env` (gitignored), never in JSON data files.
- **Engine API auth:** Local engine is localhost-only (no auth needed). Cloud engine uses JWT + API keys.
- **Language boundary:** Go CLI → Python engine is always over HTTP. No direct memory access between components.

---

## Future Considerations (Post-v1 / Cloud Edition)

- **Plugin marketplace:** Community-contributed plugins with review process
- **GitHub integration:** Auto-build on push, resume versioning via git tags
- **LinkedIn import:** Parse LinkedIn profile export to seed data
- **Portfolio mode:** Generate personal website from the same data pipeline
- **Team features:** Shared templates, reviewer workflows
- **Analytics:** Application tracking, response rate monitoring
