"""Analyze routes — POST /api/analyze and GET /api/analyze/{job_slug}."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Query

from resumeforge.analysis.report import AnalysisReport, run_analysis
from resumeforge.api.errors import not_found
from resumeforge.api.models import AnalyzeRequest
from resumeforge.core.builder import ResumeBuilder
from resumeforge.data import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analyze", tags=["Analyze"])

# Simple in-process cache: job_slug (or "") → AnalysisReport
_cache: dict[str, AnalysisReport] = {}


def _cache_path(job_slug: str | None) -> Path:
    """Return a path for persisting cached analysis reports."""
    key = job_slug or "__base__"
    return store.OUTPUT_DIR / "analysis_cache" / f"{key}.json"


def _save_cache(job_slug: str | None, report: AnalysisReport) -> None:
    path = _cache_path(job_slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    _cache[job_slug or ""] = report


def _load_cache(job_slug: str | None) -> AnalysisReport | None:
    key = job_slug or ""
    if key in _cache:
        return _cache[key]
    path = _cache_path(job_slug)
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            report = AnalysisReport.model_validate(raw)
            _cache[key] = report
            return report
        except Exception:
            pass
    return None


@router.post("", response_model=AnalysisReport)
async def analyze_resume(
    body: AnalyzeRequest | None = None,
    job_slug: str | None = Query(default=None),
) -> AnalysisReport:
    """Run the full analysis suite on the current resume data."""
    resolved_slug = (body.job_slug if body else None) or job_slug
    builder = ResumeBuilder()
    context = builder.build(job_slug=resolved_slug)
    report = run_analysis(context)
    _save_cache(resolved_slug, report)
    return report


@router.get("/{job_slug}", response_model=AnalysisReport)
async def get_cached_analysis(job_slug: str) -> AnalysisReport:
    """Return cached analysis for a job slug, or 404 if not yet run."""
    report = _load_cache(job_slug)
    if report is None:
        raise not_found("Analysis", job_slug)
    return report
