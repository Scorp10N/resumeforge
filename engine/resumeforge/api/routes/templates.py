"""Templates routes — GET /api/templates and GET /api/templates/{name}/preview."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, Response

from resumeforge.api.errors import not_found
from resumeforge.api.models import TemplateInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["Templates"])


def _templates_root() -> Path:
    return Path(__file__).parent.parent.parent / "templates"


def _read_template_toml(toml_path: Path) -> dict[str, object]:
    """Read a template.toml and return its data dict."""
    if not toml_path.exists():
        return {}
    try:
        import tomllib  # Python 3.11+
        data: dict[str, object] = tomllib.loads(toml_path.read_text(encoding="utf-8"))
        return data
    except Exception:
        return {}


@router.get("", response_model=list[TemplateInfo])
async def list_templates() -> list[TemplateInfo]:
    """List all available resume templates."""
    templates_root = _templates_root()
    result: list[TemplateInfo] = []
    if templates_root.exists():
        for d in sorted(templates_root.iterdir()):
            if not d.is_dir():
                continue
            data = _read_template_toml(d / "template.toml")
            tmpl_section = data.get("template", {})
            if isinstance(tmpl_section, dict):
                description = str(tmpl_section.get("description", ""))
                supported_formats = tmpl_section.get("supported_formats", [])
                ats_friendly = bool(tmpl_section.get("ats_friendly", False))
                if not isinstance(supported_formats, list):
                    supported_formats = []
            else:
                description = ""
                supported_formats = []
                ats_friendly = False
            result.append(
                TemplateInfo(
                    name=d.name,
                    description=description,
                    supported_formats=supported_formats,
                    ats_friendly=ats_friendly,
                )
            )
    return result


@router.get("/{name}/preview")
async def preview_template(name: str) -> Response:
    """Return a sample preview of the named template.

    Returns a PDF if available, otherwise falls back to the Markdown sample.
    Returns 404 if the template does not exist.
    """
    templates_root = _templates_root().resolve()
    template_dir = (templates_root / name).resolve()
    if not str(template_dir).startswith(str(templates_root) + "/"):
        raise not_found("Template", name)
    if not template_dir.exists():
        raise not_found("Template", name)

    # Look for a pre-rendered preview asset
    for candidate in ["preview.pdf", "preview.png", "preview.md"]:
        preview_path = template_dir / candidate
        if preview_path.exists():
            media_types = {
                ".pdf": "application/pdf",
                ".png": "image/png",
                ".md": "text/markdown; charset=utf-8",
            }
            media_type = media_types.get(preview_path.suffix, "application/octet-stream")
            return FileResponse(path=str(preview_path), media_type=media_type, filename=candidate)

    # No preview asset — return template metadata as JSON placeholder
    data = _read_template_toml(template_dir / "template.toml")
    import json
    return Response(
        content=json.dumps({"template": name, "preview": "unavailable", "meta": data}),
        media_type="application/json",
    )
