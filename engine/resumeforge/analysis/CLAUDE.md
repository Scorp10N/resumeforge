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
