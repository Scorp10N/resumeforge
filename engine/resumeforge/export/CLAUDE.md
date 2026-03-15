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
