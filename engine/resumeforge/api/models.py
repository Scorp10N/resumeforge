"""Shared Pydantic request/response models for the API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from resumeforge.analysis.report import AnalysisReport

# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------


class StatusResponse(BaseModel):
    status: str
    version: str


class ErrorResponse(BaseModel):
    detail: str
    code: str


class DeleteResponse(BaseModel):
    status: str
    slug: str


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


class BuildRequest(BaseModel):
    template: str = "classic"
    format: str = "md"
    job_slug: str | None = None
    locale: str = "en"
    analyze: bool = True


class BuildResponse(BaseModel):
    output_path: str
    format: str
    template: str
    generated_at: str
    analysis: AnalysisReport | None = None


# ---------------------------------------------------------------------------
# Tailor
# ---------------------------------------------------------------------------


class TailorRequest(BaseModel):
    job_slug: str
    ai: bool = False


class TailorResponse(BaseModel):
    job_slug: str
    tailored_summary: str
    missing_keywords: list[str]
    suggestions: list[str]


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------


class AnalyzeRequest(BaseModel):
    job_slug: str | None = None


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------


class ImportResponse(BaseModel):
    restored: list[str]
    count: int


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


class TemplateInfo(BaseModel):
    name: str
    description: str
    supported_formats: list[str] = []
    ats_friendly: bool = False


# ---------------------------------------------------------------------------
# SSE
# ---------------------------------------------------------------------------


class SSEEvent(BaseModel):
    event: str
    data: Any
