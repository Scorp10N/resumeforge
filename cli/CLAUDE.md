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
