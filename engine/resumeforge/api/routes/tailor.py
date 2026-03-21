"""Tailor routes — POST /api/tailor and GET /api/tailor/stream (SSE)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from resumeforge.ai.provider import AIProvider
from resumeforge.ai.tailor import ResumeTailor
from resumeforge.api.errors import not_found
from resumeforge.api.models import TailorRequest, TailorResponse
from resumeforge.core.builder import ResumeBuilder
from resumeforge.data import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tailor", tags=["Tailor"])


def _do_tailor(job_slug: str, ai: bool) -> TailorResponse:
    """Core tailoring logic."""
    job = store.get_job(job_slug)
    if job is None:
        raise not_found("Job", job_slug)

    builder = ResumeBuilder()
    context = builder.build(job_slug=job_slug)

    meta = store.get_meta()
    ai_config = meta.ai
    if ai and not ai_config.enabled:
        # Allow request-level override if config has enabled=False but caller says ai=True
        # We honour the caller intent; AIProvider.enabled checks config.enabled
        pass

    provider = AIProvider(ai_config)
    tailor = ResumeTailor(provider)

    tailored_summary = tailor.generate_summary(context, job)
    missing_keywords = tailor.suggest_keywords(context, job)

    suggestions: list[str] = []
    if missing_keywords:
        suggestions.append(
            f"Consider incorporating the following keywords: {', '.join(missing_keywords[:5])}"
        )
    if not context.profile.summary:
        suggestions.append("Add a professional summary to improve ATS matching.")

    return TailorResponse(
        job_slug=job_slug,
        tailored_summary=tailored_summary,
        missing_keywords=missing_keywords,
        suggestions=suggestions,
    )


@router.post("", response_model=TailorResponse)
async def tailor_resume(body: TailorRequest) -> TailorResponse:
    """Tailor the resume to a specific job description."""
    return _do_tailor(body.job_slug, body.ai)


@router.get("/stream")
async def tailor_stream(
    job_slug: str = "",
    ai: bool = False,
) -> StreamingResponse:
    """SSE stream of tailoring progress, ending with the full TailorResponse."""

    async def _generate() -> AsyncGenerator[str, None]:
        def _sse(event: str, data: object) -> str:
            payload = json.dumps(data) if not isinstance(data, str) else data
            return f"event: {event}\ndata: {payload}\n\n"

        if not job_slug:
            yield _sse("error", {"detail": "job_slug query parameter is required.", "code": "BAD_REQUEST"})
            return

        yield _sse("status", {"message": "Starting tailoring...", "step": 1, "total": 3})

        try:
            job = store.get_job(job_slug)
            if job is None:
                yield _sse("error", {"detail": f"Job '{job_slug}' not found.", "code": "NOT_FOUND"})
                return

            yield _sse("status", {"message": "Analysing job requirements...", "step": 2, "total": 3})

            builder = ResumeBuilder()
            context = builder.build(job_slug=job_slug)

            meta = store.get_meta()
            provider = AIProvider(meta.ai)
            tailor = ResumeTailor(provider)

            yield _sse("status", {"message": "Generating tailored content...", "step": 3, "total": 3})

            tailored_summary = tailor.generate_summary(context, job)
            missing_keywords = tailor.suggest_keywords(context, job)

            suggestions: list[str] = []
            if missing_keywords:
                suggestions.append(
                    f"Consider incorporating: {', '.join(missing_keywords[:5])}"
                )

            result = TailorResponse(
                job_slug=job_slug,
                tailored_summary=tailored_summary,
                missing_keywords=missing_keywords,
                suggestions=suggestions,
            )
            yield _sse("complete", result.model_dump())

        except Exception as exc:
            logger.exception("Tailor stream error")
            yield _sse("error", {"detail": str(exc), "code": "INTERNAL_ERROR"})

    return StreamingResponse(_generate(), media_type="text/event-stream")
