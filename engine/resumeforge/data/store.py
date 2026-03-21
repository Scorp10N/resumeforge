"""Data store — read/write JSON files for all resume sections."""

from __future__ import annotations

import contextlib
import json
import zipfile
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from resumeforge.data.schema import (
    Certifications,
    Education,
    Experience,
    JobDescription,
    Meta,
    Profile,
    Projects,
    Skills,
)

T = TypeVar("T", bound=BaseModel)


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# The data directory lives alongside the engine package, at engine/data/
_ENGINE_ROOT = Path(__file__).parent.parent.parent  # engine/
DATA_DIR = _ENGINE_ROOT / "data"
JOBS_DIR = DATA_DIR / "jobs"
OUTPUT_DIR = _ENGINE_ROOT / "output"


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Generic read / write
# ---------------------------------------------------------------------------


def _read[T: BaseModel](path: Path, model: type[T]) -> T:
    """Read a JSON file into a Pydantic model. Returns default instance if file missing."""
    if not path.exists():
        return model()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return model.model_validate(raw)


def _write(path: Path, model: BaseModel) -> None:
    """Write a Pydantic model to a JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        model.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Section accessors
# ---------------------------------------------------------------------------


def get_profile() -> Profile:
    _ensure_dirs()
    return _read(DATA_DIR / "profile.json", Profile)


def save_profile(profile: Profile) -> None:
    _ensure_dirs()
    _write(DATA_DIR / "profile.json", profile)


def get_experience() -> Experience:
    _ensure_dirs()
    return _read(DATA_DIR / "experience.json", Experience)


def save_experience(experience: Experience) -> None:
    _ensure_dirs()
    _write(DATA_DIR / "experience.json", experience)


def get_skills() -> Skills:
    _ensure_dirs()
    return _read(DATA_DIR / "skills.json", Skills)


def save_skills(skills: Skills) -> None:
    _ensure_dirs()
    _write(DATA_DIR / "skills.json", skills)


def get_education() -> Education:
    _ensure_dirs()
    return _read(DATA_DIR / "education.json", Education)


def save_education(education: Education) -> None:
    _ensure_dirs()
    _write(DATA_DIR / "education.json", education)


def get_projects() -> Projects:
    _ensure_dirs()
    return _read(DATA_DIR / "projects.json", Projects)


def save_projects(projects: Projects) -> None:
    _ensure_dirs()
    _write(DATA_DIR / "projects.json", projects)


def get_certifications() -> Certifications:
    _ensure_dirs()
    return _read(DATA_DIR / "certifications.json", Certifications)


def save_certifications(certifications: Certifications) -> None:
    _ensure_dirs()
    _write(DATA_DIR / "certifications.json", certifications)


def get_meta() -> Meta:
    _ensure_dirs()
    return _read(DATA_DIR / "meta.json", Meta)


def save_meta(meta: Meta) -> None:
    _ensure_dirs()
    _write(DATA_DIR / "meta.json", meta)


# ---------------------------------------------------------------------------
# Job descriptions
# ---------------------------------------------------------------------------


def list_jobs() -> list[JobDescription]:
    _ensure_dirs()
    jobs: list[JobDescription] = []
    for f in sorted(JOBS_DIR.glob("*.json")):
        with contextlib.suppress(json.JSONDecodeError, ValueError):
            jobs.append(JobDescription.model_validate(json.loads(f.read_text(encoding="utf-8"))))
    return jobs


def get_job(slug: str) -> JobDescription | None:
    _ensure_dirs()
    path = JOBS_DIR / f"{slug}.json"
    if not path.exists():
        return None
    return JobDescription.model_validate(json.loads(path.read_text(encoding="utf-8")))


def save_job(job: JobDescription) -> None:
    _ensure_dirs()
    _write(JOBS_DIR / f"{job.slug}.json", job)


def delete_job(slug: str) -> bool:
    path = JOBS_DIR / f"{slug}.json"
    if path.exists():
        path.unlink()
        return True
    return False


# ---------------------------------------------------------------------------
# Export / import (backup)
# ---------------------------------------------------------------------------


def export_backup(output_path: Path) -> Path:
    """Zip all data files (excluding PII profile.json) into a backup archive."""
    _ensure_dirs()
    output_path = output_path.with_suffix(".zip")
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in DATA_DIR.glob("*.json"):
            if f.name == "profile.json":
                continue  # PII — never export
            zf.write(f, f"data/{f.name}")
        for f in JOBS_DIR.glob("*.json"):
            zf.write(f, f"data/jobs/{f.name}")
    return output_path


def import_backup(archive_path: Path) -> list[str]:
    """Restore data from a backup zip. Returns list of restored files."""
    _ensure_dirs()
    restored: list[str] = []
    with zipfile.ZipFile(archive_path, "r") as zf:
        for name in zf.namelist():
            if name.startswith("data/") and name.endswith(".json"):
                relative = Path(name)
                dest = DATA_DIR.parent / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(name))
                restored.append(name)
    return restored


def init_data_dir() -> None:
    """Seed data directory with empty JSON files on first run."""
    _ensure_dirs()
    sections: list[tuple[Path, BaseModel]] = [
        (DATA_DIR / "experience.json", Experience()),
        (DATA_DIR / "skills.json", Skills()),
        (DATA_DIR / "education.json", Education()),
        (DATA_DIR / "projects.json", Projects()),
        (DATA_DIR / "certifications.json", Certifications()),
        (DATA_DIR / "meta.json", Meta()),
    ]
    for path, model in sections:
        if not path.exists():
            _write(path, model)
