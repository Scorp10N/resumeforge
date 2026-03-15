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
