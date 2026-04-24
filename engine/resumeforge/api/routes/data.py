"""Data routes — GET/PUT /api/data/{section}, POST /api/data/import, GET /api/data/export."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from resumeforge.api.errors import bad_request, not_found
from resumeforge.api.models import ImportResponse
from resumeforge.data import store
from resumeforge.data.schema import (
    Certifications,
    Education,
    Experience,
    Profile,
    Projects,
    Skills,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["Data"])

# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------


@router.get("/profile", response_model=Profile)
async def get_profile() -> Profile:
    """Get profile section."""
    return store.get_profile()


@router.put("/profile", response_model=Profile)
async def update_profile(profile: Profile) -> Profile:
    """Update profile section."""
    store.save_profile(profile)
    return profile


# ---------------------------------------------------------------------------
# Experience
# ---------------------------------------------------------------------------


@router.get("/experience", response_model=Experience)
async def get_experience() -> Experience:
    """Get experience section."""
    return store.get_experience()


@router.put("/experience", response_model=Experience)
async def update_experience(experience: Experience) -> Experience:
    """Update experience section."""
    store.save_experience(experience)
    return experience


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


@router.get("/skills", response_model=Skills)
async def get_skills() -> Skills:
    """Get skills section."""
    return store.get_skills()


@router.put("/skills", response_model=Skills)
async def update_skills(skills: Skills) -> Skills:
    """Update skills section."""
    store.save_skills(skills)
    return skills


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------


@router.get("/education", response_model=Education)
async def get_education() -> Education:
    """Get education section."""
    return store.get_education()


@router.put("/education", response_model=Education)
async def update_education(education: Education) -> Education:
    """Update education section."""
    store.save_education(education)
    return education


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@router.get("/projects", response_model=Projects)
async def get_projects() -> Projects:
    """Get projects section."""
    return store.get_projects()


@router.put("/projects", response_model=Projects)
async def update_projects(projects: Projects) -> Projects:
    """Update projects section."""
    store.save_projects(projects)
    return projects


# ---------------------------------------------------------------------------
# Certifications
# ---------------------------------------------------------------------------


@router.get("/certifications", response_model=Certifications)
async def get_certifications() -> Certifications:
    """Get certifications section."""
    return store.get_certifications()


@router.put("/certifications", response_model=Certifications)
async def update_certifications(certifications: Certifications) -> Certifications:
    """Update certifications section."""
    store.save_certifications(certifications)
    return certifications


# ---------------------------------------------------------------------------
# Export / Import
# ---------------------------------------------------------------------------


@router.get("/export")
async def export_backup() -> FileResponse:
    """Export a backup zip of all resume data (excludes PII profile.json)."""
    tmp = store.OUTPUT_DIR / "backup.zip"
    store.export_backup(tmp)
    return FileResponse(path=str(tmp), filename="resumeforge_backup.zip", media_type="application/zip")


@router.post("/import", response_model=ImportResponse)
async def import_backup(archive_path: str = Query(..., description="Absolute path to backup archive")) -> ImportResponse:
    """Restore data from a backup archive."""
    path = Path(archive_path).resolve()
    allowed_root = store.OUTPUT_DIR.resolve()
    if not str(path).startswith(str(allowed_root) + "/"):
        raise bad_request(f"archive_path must be inside {allowed_root}", code="PATH_NOT_ALLOWED")
    if not path.exists():
        raise not_found("Archive", archive_path)
    restored = store.import_backup(path)
    return ImportResponse(restored=restored, count=len(restored))
