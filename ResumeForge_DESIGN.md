# ResumeForge — Design Document v1.0

## Project overview

**ResumeForge** is a personal, open-source CV automation platform that separates resume content from presentation, enabling rapid rebuilding and tailoring of resumes for specific roles. It features pluggable AI editing, multi-format export, multi-language support, and automated quality analysis.

**Scope:** Single-user, private repo, designed to be self-hosted and run locally.

---

## Tech stack decision

**Python** is the best fit for this project for several reasons:

- **CLI/TUI/Web all native:** Typer (CLI), Textual (TUI), and FastAPI (Web) share the same Python core — no cross-language bridges needed.
- **AI ecosystem:** LiteLLM is Python-native. LangChain, LangGraph, and all major LLM SDKs are Python-first.
- **Document generation:** python-docx, WeasyPrint (PDF), and Jinja2 templates are mature and battle-tested.
- **Your skills:** Python is already on your CV as a primary language.
- **Single dependency tree:** One `pyproject.toml`, one virtual environment, one test suite.

| Component | Library | Why |
|-----------|---------|-----|
| CLI | Typer + Rich | Type-safe CLI with beautiful output |
| TUI | Textual | Terminal UI with mouse support, built on Rich |
| Web UI | FastAPI + HTMX + Jinja2 | Lightweight, no JS framework needed |
| AI Provider | LiteLLM | Unified API for OpenAI, Anthropic, Ollama, Azure, 100+ providers |
| DOCX Export | python-docx | Full control over Word document generation |
| PDF Export | WeasyPrint | CSS-based PDF from HTML templates |
| Markdown | Jinja2 + markdown-it-py | Template-driven markdown rendering |
| Data Store | JSON files | Git-friendly, human-readable, portable |
| i18n | babel + custom | Locale-aware formatting + RTL support |
| Testing | pytest + pytest-snapshot | Snapshot testing for generated documents |
| Packaging | uv / pip | Modern Python package management |

---

## Architecture

### Layer overview

```
┌─────────────────────────────────────────────────┐
│  Interfaces: CLI (Typer) · TUI (Textual) · Web  │
├─────────────────────────────────────────────────┤
│  Core Engine: Builder · Templates · Sections     │
├────────────┬────────────────┬───────────────────┤
│ Data Store │  AI Provider   │  Export Engine     │
│ (JSON)     │  (LiteLLM)     │  (MD/PDF/DOCX)    │
├────────────┴────────────────┴───────────────────┤
│  Analysis Engine: ATS · Gaps · Quality · Grammar │
├─────────────────────────────────────────────────┤
│  Output: Tailored Resume + Report + Diff         │
└─────────────────────────────────────────────────┘
```

### Directory structure

```
resumeforge/
├── pyproject.toml
├── README.md
├── resumeforge/
│   ├── __init__.py
│   ├── cli/                    # CLI interface (Typer)
│   │   ├── __init__.py
│   │   ├── app.py              # Main CLI entrypoint
│   │   └── commands/
│   │       ├── build.py        # Build resume from data + template
│   │       ├── tailor.py       # Tailor resume to job description
│   │       ├── analyze.py      # Run analysis suite
│   │       ├── template.py     # List/preview templates
│   │       └── data.py         # Edit/view stored data
│   ├── tui/                    # TUI interface (Textual)
│   │   ├── __init__.py
│   │   ├── app.py              # Main TUI application
│   │   └── screens/
│   │       ├── dashboard.py    # Overview + quick actions
│   │       ├── editor.py       # Section editor with preview
│   │       └── analysis.py     # Analysis results viewer
│   ├── web/                    # Web UI interface (FastAPI)
│   │   ├── __init__.py
│   │   ├── app.py              # FastAPI application
│   │   ├── routes/
│   │   │   ├── builder.py      # Resume builder routes
│   │   │   ├── analysis.py     # Analysis routes
│   │   │   └── api.py          # JSON API for HTMX
│   │   ├── templates/          # Jinja2 HTML templates (web UI)
│   │   │   ├── base.html
│   │   │   ├── builder.html
│   │   │   └── analysis.html
│   │   └── static/
│   │       └── styles.css
│   ├── core/                   # Core engine (shared by all interfaces)
│   │   ├── __init__.py
│   │   ├── builder.py          # Resume assembly orchestrator
│   │   ├── section.py          # Section model and management
│   │   ├── template_engine.py  # Template loading and rendering
│   │   └── i18n.py             # Internationalization engine
│   ├── data/                   # Data store layer
│   │   ├── __init__.py
│   │   ├── store.py            # JSON read/write operations
│   │   ├── schema.py           # Pydantic models for all data
│   │   └── migrations.py       # Schema version upgrades
│   ├── ai/                     # AI provider layer
│   │   ├── __init__.py
│   │   ├── provider.py         # LiteLLM wrapper + config
│   │   ├── prompts/            # Prompt templates (Jinja2)
│   │   │   ├── rewrite_section.j2
│   │   │   ├── tailor_to_job.j2
│   │   │   ├── translate.j2
│   │   │   └── analyze.j2
│   │   ├── rewriter.py         # Section rewriting logic
│   │   ├── tailor.py           # Job description matching
│   │   └── style.py            # Tone/style controller
│   ├── export/                 # Export engine
│   │   ├── __init__.py
│   │   ├── markdown.py         # Markdown export
│   │   ├── pdf.py              # PDF via WeasyPrint
│   │   ├── docx_export.py      # DOCX via python-docx
│   │   └── base.py             # Abstract exporter interface
│   ├── analysis/               # Analysis engine
│   │   ├── __init__.py
│   │   ├── ats_score.py        # ATS keyword matching
│   │   ├── gap_analysis.py     # Missing skills detector
│   │   ├── quantification.py   # Metrics/numbers in bullets
│   │   ├── readability.py      # Length, formatting, structure
│   │   ├── grammar.py          # Language quality (AI-assisted)
│   │   └── report.py           # Report generator
│   └── templates/              # Resume templates (output)
│       ├── classic/
│       │   ├── template.toml   # Template metadata
│       │   ├── resume.md.j2    # Markdown template
│       │   ├── resume.html.j2  # HTML template (for PDF)
│       │   └── resume.docx.py  # python-docx builder
│       ├── modern/
│       ├── minimal/
│       └── executive/
├── data/                       # User data (gitignored PII)
│   ├── profile.json            # Name, contact, links (PII)
│   ├── experience.json         # Work history
│   ├── skills.json             # Skills and competencies
│   ├── education.json          # Education and certifications
│   ├── projects.json           # Side projects, open source
│   ├── meta.json               # Preferences, default locale, template
│   └── jobs/                   # Saved job descriptions
│       ├── bank-appsec.json
│       └── startup-devsecops.json
├── output/                     # Generated resumes
│   └── 2026-03-15_bank-appsec/
│       ├── resume.md
│       ├── resume.pdf
│       ├── resume.docx
│       └── analysis_report.md
└── tests/
    ├── test_builder.py
    ├── test_analysis.py
    ├── test_export.py
    └── snapshots/
```

---

## Data model

All data is stored as JSON files in the `data/` directory. Each file maps to a Pydantic model for validation.

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

### education.json

```json
{
  "schema_version": "1.0",
  "entries": [
    {
      "institution": "Ben-Zvi High School, Kiryat-Ono",
      "degree": "Computer Science & Chemistry",
      "start_date": null,
      "end_date": null
    }
  ],
  "certifications": []
}
```

### meta.json

```json
{
  "schema_version": "1.0",
  "default_locale": "en",
  "default_template": "classic",
  "default_format": "pdf",
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

## Template system

Each template is a self-contained directory with metadata and format-specific renderers.

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

### Template rendering flow

```
data/*.json ──→ Pydantic Models ──→ Template Context ──→ Jinja2 ──→ Format-specific renderer
                                         ↑                              │
                                    i18n strings                   ┌────┴────┐
                                                                   MD  PDF  DOCX
```

Templates use Jinja2 for markdown and HTML (PDF). DOCX templates use a Python builder class inheriting from `BaseDocxTemplate` that receives the same context dict.

---

## AI provider layer

### Architecture

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

### LiteLLM configuration

LiteLLM supports 100+ providers through a single `completion()` call. Configuration in `meta.json`:

```python
import litellm

# OpenAI
litellm.completion(model="gpt-4o", messages=[...])

# Anthropic
litellm.completion(model="claude-sonnet-4-20250514", messages=[...])

# Local Ollama
litellm.completion(model="ollama/llama3", messages=[...], api_base="http://localhost:11434")

# Azure OpenAI
litellm.completion(model="azure/gpt-4o", messages=[...], api_base="https://my-endpoint.openai.azure.com")
```

### AI capabilities

| Capability | Prompt template | Description |
|-----------|----------------|-------------|
| Rewrite section | `rewrite_section.j2` | Rewrite a section with style/tone control |
| Tailor to job | `tailor_to_job.j2` | Adapt entire resume to match job description |
| Translate | `translate.j2` | Translate resume content to target locale |
| Analyze | `analyze.j2` | AI-assisted grammar and quality check |
| Suggest bullets | `suggest_bullets.j2` | Generate bullet points from raw experience |
| Gap fill | `gap_fill.j2` | Suggest how to address skill gaps for a role |

### Style controller

The AI style controller governs tone and formatting rules passed to every prompt:

```python
class StyleController:
    tone: str           # "professional", "technical", "executive", "casual"
    max_bullet_words: int
    action_verb_first: bool
    avoid_tool_names: bool
    quantify_preference: str  # "aggressive", "moderate", "minimal"
    language: str       # Target language code
```

---

## Export engine

### Exporter interface

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

### Export flow

```
resumeforge build --template classic --format pdf --job bank-appsec

1. Load data/*.json → Pydantic models
2. Load job description (if --job provided)
3. [Optional] AI tailor sections to job
4. Build ResumeContext (merged, prioritized sections)
5. Apply i18n (locale-specific labels, date formatting, RTL)
6. Render through template + exporter
7. Save to output/{date}_{job-slug}/
8. Run analysis suite → save report
```

---

## Analysis engine

The analysis engine runs multiple analyzers and produces a unified report.

### Analyzers

| Analyzer | What it measures | Scoring |
|---------|-----------------|---------|
| **ATS keyword match** | Keywords from job description found in resume | % match, missing keywords list |
| **Gap analysis** | Required skills in JD not present in resume | Critical/nice-to-have gaps |
| **Quantification** | % of bullets containing metrics/numbers | Score + flagged weak bullets |
| **Readability** | Page count, bullet length, section balance | Pass/warn/fail per metric |
| **Grammar & quality** | Spelling, grammar, consistency (AI-assisted) | Issues list with severity |

### Report output

```markdown
# Resume Analysis Report
## Generated: 2026-03-15 | Target: Senior AppSec Guide — Major Bank

### ATS Keyword Match: 78/100
**Matched:** Application Security, SAST/DAST, Kubernetes, Azure, GCP, CI/CD...
**Missing:** Checkmarx (add to competencies), OWASP Top 10 (add to summary)

### Skill Gap Analysis
**Critical gaps:** None
**Nice-to-have gaps:** CS Degree (cannot address), Penetration Testing cert

### Quantification Score: 65/100
**Strong:** "40% reduction in incidents", "100+ reviews", "200% productivity"
**Weak (no metrics):** 3 bullets in current role — consider adding client count or project scope

### Readability: Pass
- Pages: 1 (target: 1) ✓
- Avg bullet length: 18 words ✓
- Longest bullet: 24 words ✓
- Section balance: Good ✓

### Grammar & Quality: 2 issues
- "Provide cloud security consulting" → Consider past tense for non-current roles
- Inconsistent date format: "2018 – 2022" vs "Nov 2022 – Feb 2025"
```

---

## Multi-language support

### Approach

- **Content translation:** AI-powered via `translate.j2` prompt template
- **UI labels:** Babel message catalogs (`.po` files) for section headers, report labels
- **Date formatting:** Locale-aware via Babel (`March 2025` vs `מרץ 2025`)
- **RTL support:** HTML/PDF templates detect RTL locales and apply `dir="rtl"` + appropriate CSS
- **Per-section language:** Each section can specify its own language override

### Locale structure

```
resumeforge/
  locales/
    en/
      LC_MESSAGES/
        messages.po    # "Professional Summary", "Core Competencies", ...
    he/
      LC_MESSAGES/
        messages.po    # "תקציר מקצועי", "יכולות ליבה", ...
```

---

## Interface specifications

### CLI (Typer)

```bash
# Build resume
resumeforge build --template classic --format pdf
resumeforge build --template modern --format docx --job bank-appsec --lang he

# Tailor to job
resumeforge tailor --job bank-appsec --ai
resumeforge tailor --job-file ./description.txt --ai --model claude-sonnet-4-20250514

# Analyze
resumeforge analyze --job bank-appsec
resumeforge analyze --format json  # Machine-readable report

# Templates
resumeforge templates list
resumeforge templates preview classic --format pdf

# Data management
resumeforge data show experience
resumeforge data edit experience --section scorp-2025
resumeforge data export --output backup.zip
resumeforge data import --input backup.zip

# Configuration
resumeforge config set ai.model gpt-4o
resumeforge config set ai.enabled true
resumeforge config set style.tone executive
```

### TUI (Textual)

```bash
resumeforge tui
```

Screens:
- **Dashboard:** Overview of stored data, recent builds, quick actions
- **Editor:** Split-pane section editor with live preview (markdown rendered in right pane)
- **Job matcher:** Paste job description, see ATS score update live
- **Analysis:** Full analysis report with expandable sections
- **Templates:** Visual template browser with sample renders

### Web UI (FastAPI + HTMX)

```bash
resumeforge web --port 8080
```

Routes:
- `GET /` — Dashboard
- `GET /build` — Resume builder (template picker, format selector, job selector)
- `POST /build` — Generate resume, stream progress via SSE
- `GET /analyze` — Analysis view
- `POST /analyze` — Run analysis, return HTMX partial
- `GET /data/{section}` — View/edit section data
- `GET /api/templates` — List templates (JSON)
- `GET /api/preview/{template}` — Preview template (returns PDF bytes)

---

## Build phases

### Phase 1 — Foundation (MVP)
- Data store (JSON + Pydantic models)
- Core builder engine
- 1 template ("classic")
- Markdown + DOCX export
- CLI interface (build + data commands)
- Basic ATS keyword analysis

### Phase 2 — AI + Analysis
- LiteLLM integration
- AI rewriting and tailoring
- Full analysis suite (all 5 analyzers)
- Report generator
- PDF export (WeasyPrint)

### Phase 3 — Templates + i18n
- 3 additional templates (modern, minimal, executive)
- Multi-language support (en, he)
- RTL support for Hebrew
- Template preview system

### Phase 4 — TUI + Web
- TUI interface (Textual)
- Web UI (FastAPI + HTMX)
- Live preview
- Job description manager

### Phase 5 — Polish
- Diff view (before/after AI edits)
- Snapshot testing
- CI pipeline
- Documentation + README
- Plugin system for custom analyzers

---

## Security considerations

- **PII isolation:** `profile.json` is in `.gitignore` by default. A `.gitignore` template is generated on `resumeforge init`.
- **AI data:** When AI is enabled, resume content is sent to the configured provider. Local providers (Ollama) keep data on-machine. A warning is displayed on first use of cloud providers.
- **No telemetry:** Zero analytics, tracking, or phone-home behavior.
- **API keys:** Stored in environment variables or a local `.env` file (also gitignored), never in JSON data files.

---

## Future considerations (post-v1)

- **Multi-user mode:** SQLite/PostgreSQL backend, auth, per-user data isolation
- **SaaS deployment:** Docker compose, hosted web UI, Stripe billing
- **GitHub integration:** Auto-build on push, resume versioning via git tags
- **LinkedIn import:** Parse LinkedIn profile export to seed data files
- **Cover letter generator:** Same AI pipeline, different templates
- **Portfolio mode:** Generate a personal website from the same data
