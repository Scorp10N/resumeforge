"""Build routes — POST /api/build and GET /api/build/stream (SSE)."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse, StreamingResponse

from resumeforge.analysis.report import run_analysis
from resumeforge.api.errors import bad_request, internal_error, not_found
from resumeforge.api.models import BuildRequest, BuildResponse
from resumeforge.core.builder import ResumeBuilder
from resumeforge.data import store
from resumeforge.export.docx_export import DocxExporter
from resumeforge.export.markdown import MarkdownExporter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/build", tags=["Build"])

_EXPORTERS = {
    "md": MarkdownExporter,
    "docx": DocxExporter,
}


def _templates_root() -> Path:
    return Path(__file__).parent.parent.parent / "templates"


def _do_build(
    template: str,
    format: str,
    job_slug: str | None,
    locale: str,
    analyze: bool,
) -> BuildResponse:
    """Core build logic shared by sync and streaming endpoints."""
    builder = ResumeBuilder()
    context = builder.build(
        template_name=template,
        output_format=format,
        job_slug=job_slug,
        locale=locale,
    )

    template_dir = _templates_root() / template
    if not template_dir.exists():
        raise not_found("Template", template)

    exporter_cls = _EXPORTERS.get(format)
    if exporter_cls is None:
        raise bad_request(f"Format '{format}' not supported.", code="UNSUPPORTED_FORMAT")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug_part = f"_{job_slug}" if job_slug else ""
    output_dir = store.OUTPUT_DIR / f"{timestamp}{slug_part}"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"resume_{template}"

    try:
        final_path = exporter_cls().export(context, template_dir, output_path)
    except Exception as exc:
        raise internal_error(str(exc)) from exc

    report = run_analysis(context) if analyze else None

    return BuildResponse(
        output_path=str(final_path),
        format=format,
        template=template,
        generated_at=datetime.now().isoformat(timespec="seconds"),
        analysis=report,
    )


@router.post("", response_model=BuildResponse)
async def build_resume(
    template: str = Query(default="classic", description="Template name"),
    format: str = Query(default="md", description="Output format: md | docx"),
    job_slug: str | None = Query(default=None, description="Job slug for tailoring"),
    locale: str = Query(default="en", description="Output locale"),
    analyze: bool = Query(default=True, description="Run analysis after build"),
) -> BuildResponse:
    """Build a resume from stored data."""
    return _do_build(template, format, job_slug, locale, analyze)


@router.get("/stream")
async def build_stream(
    template: str = Query(default="classic"),
    format: str = Query(default="md"),
    job_slug: str | None = Query(default=None),
    locale: str = Query(default="en"),
    analyze: bool = Query(default=True),
) -> StreamingResponse:
    """SSE stream of build progress, ending with the full BuildResponse."""

    async def _generate() -> AsyncGenerator[str, None]:
        def _sse(event: str, data: object) -> str:
            payload = json.dumps(data) if not isinstance(data, str) else data
            return f"event: {event}\ndata: {payload}\n\n"

        yield _sse("status", {"message": "Starting build...", "step": 1, "total": 4})

        try:
            yield _sse("status", {"message": "Loading resume data...", "step": 2, "total": 4})
            builder = ResumeBuilder()
            context = builder.build(
                template_name=template,
                output_format=format,
                job_slug=job_slug,
                locale=locale,
            )

            template_dir = _templates_root() / template
            if not template_dir.exists():
                yield _sse("error", {"detail": f"Template '{template}' not found.", "code": "NOT_FOUND"})
                return

            exporter_cls = _EXPORTERS.get(format)
            if exporter_cls is None:
                yield _sse("error", {"detail": f"Format '{format}' not supported.", "code": "UNSUPPORTED_FORMAT"})
                return

            yield _sse("status", {"message": "Rendering resume...", "step": 3, "total": 4})
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug_part = f"_{job_slug}" if job_slug else ""
            output_dir = store.OUTPUT_DIR / f"{timestamp}{slug_part}"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"resume_{template}"

            try:
                final_path = exporter_cls().export(context, template_dir, output_path)
            except Exception as exc:
                yield _sse("error", {"detail": str(exc), "code": "EXPORT_ERROR"})
                return

            yield _sse("status", {"message": "Running analysis...", "step": 4, "total": 4})
            report = run_analysis(context) if analyze else None

            result = BuildResponse(
                output_path=str(final_path),
                format=format,
                template=template,
                generated_at=datetime.now().isoformat(timespec="seconds"),
                analysis=report,
            )
            yield _sse("complete", result.model_dump())

        except Exception as exc:
            logger.exception("Build stream error")
            yield _sse("error", {"detail": str(exc), "code": "INTERNAL_ERROR"})

    return StreamingResponse(_generate(), media_type="text/event-stream")


@router.get("/download")
async def download_output(
    path: str = Query(..., description="Absolute path from build response"),
) -> FileResponse:
    """Download a previously built file."""
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise not_found("File", path)
    return FileResponse(path=str(file_path), filename=file_path.name)
