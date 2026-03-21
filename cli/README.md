# ResumeForge CLI / TUI

Go standalone client for ResumeForge. Single binary — no Python runtime required at runtime. Communicates with the engine over HTTP (auto-spawns local engine if not running).

**Stack:** Go · Cobra (CLI) · Bubble Tea + Lip Gloss (TUI)

---

## Prerequisites

- Go 1.21+ — [go.dev/dl](https://go.dev/dl/)
- ResumeForge engine running at `localhost:8080` (or configured via `--engine`)

---

## Build

```bash
cd cli
go build -o resumeforge .
```

Cross-platform release builds:
```bash
goreleaser build --snapshot --clean
```

---

## Non-Interactive Testing

```bash
cd cli
go test ./...     # all unit tests
go vet ./...      # static analysis
go build ./...    # compilation check
```

---

## Interactive Testing

### CLI Commands

```bash
# Help
./resumeforge --help
./resumeforge build --help

# Build resume
./resumeforge build --template classic --format md
./resumeforge build --template classic --format docx --job <slug>

# Analyze
./resumeforge analyze
./resumeforge analyze --job <slug> --format json

# Templates
./resumeforge templates list
./resumeforge templates preview classic

# Data
./resumeforge data show experience
./resumeforge data show skills
./resumeforge data export --output backup.zip
./resumeforge data import --input backup.zip

# Config
./resumeforge config set ai.enabled false
./resumeforge config set engine.url http://localhost:8080
```

### TUI

```bash
./resumeforge tui
```

Screens:
| Screen | Description |
|--------|-------------|
| **Dashboard** | Data overview, recent builds, quick actions |
| **Editor** | Section editor with Markdown preview |
| **Job Matcher** | Paste job description, live ATS score via SSE |
| **Analysis** | Full report with expandable sections |

Navigation: arrow keys / `Tab` to move, `Enter` to select, `q` / `Ctrl+C` to quit.

---

## Remote Engine

```bash
# Connect to a remote/cloud engine
./resumeforge --engine https://cloud.resumeforge.io build --template classic --format pdf
```
