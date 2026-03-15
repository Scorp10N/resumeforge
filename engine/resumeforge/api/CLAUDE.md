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
