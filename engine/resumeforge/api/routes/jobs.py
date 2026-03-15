"""Jobs routes — CRUD for /api/jobs."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from resumeforge.api.errors import not_found
from resumeforge.api.models import DeleteResponse
from resumeforge.data import store
from resumeforge.data.schema import JobDescription

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("", response_model=list[JobDescription])
async def list_jobs() -> list[JobDescription]:
    """List all saved job descriptions."""
    return store.list_jobs()


@router.post("", response_model=JobDescription)
async def create_job(job: JobDescription) -> JobDescription:
    """Save a new job description."""
    store.save_job(job)
    return job


@router.get("/{slug}", response_model=JobDescription)
async def get_job(slug: str) -> JobDescription:
    """Get a job description by slug."""
    job = store.get_job(slug)
    if job is None:
        raise not_found("Job", slug)
    return job


@router.put("/{slug}", response_model=JobDescription)
async def update_job(slug: str, job: JobDescription) -> JobDescription:
    """Update an existing job description."""
    existing = store.get_job(slug)
    if existing is None:
        raise not_found("Job", slug)
    # Use the slug from the URL path (canonical)
    updated = job.model_copy(update={"slug": slug})
    store.save_job(updated)
    return updated


@router.delete("/{slug}", response_model=DeleteResponse)
async def delete_job(slug: str) -> DeleteResponse:
    """Delete a job description by slug."""
    if not store.delete_job(slug):
        raise not_found("Job", slug)
    return DeleteResponse(status="deleted", slug=slug)
