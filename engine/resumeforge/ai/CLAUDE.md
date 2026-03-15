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
