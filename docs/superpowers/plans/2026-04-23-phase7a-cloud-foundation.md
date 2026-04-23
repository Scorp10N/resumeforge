# Phase 7a — Cloud Edition Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add JWT auth, PostgreSQL backend (via BaseStore ABC), multi-user isolation, and GitHub import + Pages deploy to the ResumeForge engine, while keeping the Community Edition (JSON, no auth) completely unchanged.

**Architecture:** `BaseStore` ABC with `JsonStore` (existing logic, community) and `PostgresStore` (SQLAlchemy async, cloud) swapped via `factory.get_store()` injected into every route via FastAPI `Depends`. Auth activates only when `RF_ENGINE_MODE=cloud`. GitHub integration lives in `engine/resumeforge/integrations/github.py` with routes exposed via `/api/integrations/github/*`.

**Tech Stack:** python-jose (JWT), passlib[bcrypt] (passwords), SQLAlchemy 2 async + asyncpg (PostgreSQL), Alembic (migrations), httpx (GitHub API), pydantic-settings (already present), respx (test mocks for httpx).

---

## File Map

### Created
| File | Responsibility |
|------|---------------|
| `engine/resumeforge/settings.py` | Pydantic-settings: engine mode, DB URL, secret key |
| `engine/resumeforge/data/base_store.py` | `BaseStore` ABC — all 20 async method signatures |
| `engine/resumeforge/data/json_store.py` | `JsonStore(BaseStore)` — existing store.py logic, user_id ignored |
| `engine/resumeforge/data/postgres_store.py` | `PostgresStore(BaseStore)` — SQLAlchemy async, user_id on every query |
| `engine/resumeforge/data/orm_models.py` | SQLAlchemy ORM models (`users`, `refresh_tokens`, one table per data section) |
| `engine/resumeforge/data/factory.py` | `get_store() -> BaseStore` FastAPI dependency |
| `engine/resumeforge/auth/__init__.py` | Empty |
| `engine/resumeforge/auth/models.py` | `User`, `UserCreate`, `UserLogin`, `UserInDB`, `Token` Pydantic models |
| `engine/resumeforge/auth/jwt.py` | `create_access_token`, `create_refresh_token`, `verify_token` |
| `engine/resumeforge/auth/dependencies.py` | `get_current_user` FastAPI Depends; returns `LOCAL_USER` in community mode |
| `engine/resumeforge/api/routes/auth.py` | `POST /api/auth/register`, `/login`, `/refresh` |
| `engine/resumeforge/integrations/__init__.py` | Empty |
| `engine/resumeforge/integrations/github.py` | GitHub API client, import functions, Pages deploy |
| `engine/resumeforge/api/routes/github.py` | `POST /api/integrations/github/import`, `/pages/deploy` |
| `engine/alembic.ini` | Alembic config pointing at `engine/alembic/` |
| `engine/alembic/env.py` | Alembic env wired to `orm_models` metadata |
| `engine/tests/test_auth.py` | Auth model, JWT, register/login/refresh endpoint tests |
| `engine/tests/test_json_store.py` | JsonStore tests (adapted from test_data.py store section) |
| `engine/tests/test_github_integration.py` | GitHub import + deploy tests (httpx mocked with respx) |
| `cli/client/github.go` | Typed HTTP client methods for github endpoints |
| `cli/cmd/github.go` | Cobra command group: `github import`, `github deploy` |

### Modified
| File | Change |
|------|--------|
| `engine/pyproject.toml` | Add 6 new dependencies + respx to dev |
| `engine/resumeforge/data/schema.py` | Add `IntegrationsConfig`; add `integrations` field to `Meta` |
| `engine/resumeforge/data/store.py` | Replace body with thin re-export from `json_store` + `factory` |
| `engine/resumeforge/api/app.py` | Register auth + github routers; wire `get_store` startup; add Auth + Integrations OpenAPI tags |
| `engine/resumeforge/api/routes/data.py` | Add `store: BaseStore = Depends(get_store)`, `user: User = Depends(get_current_user)`; await all store calls |
| `engine/resumeforge/api/routes/jobs.py` | Same as data.py |
| `engine/resumeforge/api/routes/config.py` | Same as data.py |
| `cli/cmd/root.go` | Register `githubCmd` |

> **Note:** `routes/build.py`, `routes/tailor.py`, `routes/analyze.py` also call `store.*` — update them identically to data.py (add Depends, await calls). Not shown in detail below since the pattern is identical.

---

## Group A — Dependencies & Schema

### Task 1: Add dependencies

**Files:**
- Modify: `engine/pyproject.toml`

- [ ] **Step 1: Add new runtime and dev dependencies**

Replace the `[project]` dependencies list in `engine/pyproject.toml`:

```toml
dependencies = [
    # API
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "python-multipart>=0.0.9",
    # Data
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",
    # Auth
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    # Database
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    # HTTP client (GitHub API)
    "httpx>=0.27.0",
    # AI
    "litellm>=1.40.0",
    "jinja2>=3.1.4",
    # Export
    "python-docx>=1.1.2",
    "weasyprint>=62.3",
    "markdown-it-py>=3.0.0",
    # i18n
    "babel>=2.14.0",
    # Utils
    "rich>=13.7.0",
    "python-dotenv>=1.0.0",
    "typer>=0.12.0",
]
```

Add `"respx>=0.21.0"` to the `[project.optional-dependencies] dev` list.

- [ ] **Step 2: Install**

```bash
cd engine && uv sync --extra dev
```

Expected: no errors, lock file updated.

- [ ] **Step 3: Commit**

```bash
git add engine/pyproject.toml engine/uv.lock
git commit -m "chore(engine): add phase 7a dependencies (jose, passlib, sqlalchemy, asyncpg, alembic, httpx)"
```

---

### Task 2: Settings module

**Files:**
- Create: `engine/resumeforge/settings.py`

- [ ] **Step 1: Create settings module**

```python
"""Centralised settings — read from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RF_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    engine_mode: str = "local"   # "local" | "cloud"
    database_url: str = ""       # RF_DATABASE_URL=postgresql+asyncpg://...
    secret_key: str = ""         # RF_SECRET_KEY=...

    @property
    def is_cloud(self) -> bool:
        return self.engine_mode == "cloud"


settings = Settings()
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
cd engine && uv run python -c "from resumeforge.settings import settings; print(settings.engine_mode)"
```

Expected: `local`

- [ ] **Step 3: Commit**

```bash
git add engine/resumeforge/settings.py
git commit -m "feat(engine): add pydantic-settings Settings module"
```

---

### Task 3: Update schema.py — IntegrationsConfig + Meta.integrations

**Files:**
- Modify: `engine/resumeforge/data/schema.py`

- [ ] **Step 1: Write a failing test**

Add to `engine/tests/test_data.py`:

```python
class TestIntegrationsConfig:
    def test_defaults(self) -> None:
        from resumeforge.data.schema import IntegrationsConfig
        cfg = IntegrationsConfig()
        assert cfg.github_token is None

    def test_meta_has_integrations(self) -> None:
        m = Meta()
        assert hasattr(m, "integrations")
        assert m.integrations.github_token is None
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd engine && uv run pytest tests/test_data.py::TestIntegrationsConfig -x
```

Expected: `ImportError` — `IntegrationsConfig` not defined yet.

- [ ] **Step 3: Add IntegrationsConfig to schema.py**

After the `StyleConfig` class and before `class Meta`, insert:

```python
class IntegrationsConfig(BaseModel):
    github_token: str | None = None
```

Then update `Meta`:

```python
class Meta(VersionedModel):
    default_locale: str = "en"
    default_template: str = "classic"
    default_format: str = "pdf"
    engine: EngineConfig = Field(default_factory=EngineConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    style: StyleConfig = Field(default_factory=StyleConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd engine && uv run pytest tests/test_data.py::TestIntegrationsConfig -x
```

Expected: PASS

- [ ] **Step 5: Run full existing test suite to confirm no regressions**

```bash
cd engine && uv run pytest tests/test_data.py -x
```

Expected: all existing tests still pass.

- [ ] **Step 6: Commit**

```bash
git add engine/resumeforge/data/schema.py engine/tests/test_data.py
git commit -m "feat(schema): add IntegrationsConfig + Meta.integrations for GitHub token"
```

---

## Group B — Storage Abstraction

### Task 4: BaseStore ABC

**Files:**
- Create: `engine/resumeforge/data/base_store.py`

- [ ] **Step 1: Create the ABC**

```python
"""BaseStore — abstract interface for all resume data storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID

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


class BaseStore(ABC):
    """Storage backend interface. user_id is the owner of all data."""

    # --- Profile ---
    @abstractmethod
    async def get_profile(self, user_id: UUID) -> Profile: ...

    @abstractmethod
    async def save_profile(self, user_id: UUID, profile: Profile) -> None: ...

    # --- Experience ---
    @abstractmethod
    async def get_experience(self, user_id: UUID) -> Experience: ...

    @abstractmethod
    async def save_experience(self, user_id: UUID, experience: Experience) -> None: ...

    # --- Skills ---
    @abstractmethod
    async def get_skills(self, user_id: UUID) -> Skills: ...

    @abstractmethod
    async def save_skills(self, user_id: UUID, skills: Skills) -> None: ...

    # --- Education ---
    @abstractmethod
    async def get_education(self, user_id: UUID) -> Education: ...

    @abstractmethod
    async def save_education(self, user_id: UUID, education: Education) -> None: ...

    # --- Projects ---
    @abstractmethod
    async def get_projects(self, user_id: UUID) -> Projects: ...

    @abstractmethod
    async def save_projects(self, user_id: UUID, projects: Projects) -> None: ...

    # --- Certifications ---
    @abstractmethod
    async def get_certifications(self, user_id: UUID) -> Certifications: ...

    @abstractmethod
    async def save_certifications(self, user_id: UUID, certifications: Certifications) -> None: ...

    # --- Meta ---
    @abstractmethod
    async def get_meta(self, user_id: UUID) -> Meta: ...

    @abstractmethod
    async def save_meta(self, user_id: UUID, meta: Meta) -> None: ...

    # --- Jobs ---
    @abstractmethod
    async def list_jobs(self, user_id: UUID) -> list[JobDescription]: ...

    @abstractmethod
    async def get_job(self, user_id: UUID, slug: str) -> JobDescription | None: ...

    @abstractmethod
    async def save_job(self, user_id: UUID, job: JobDescription) -> None: ...

    @abstractmethod
    async def delete_job(self, user_id: UUID, slug: str) -> bool: ...

    # --- Backup ---
    @abstractmethod
    async def export_backup(self, user_id: UUID, output_path: Path) -> Path: ...

    @abstractmethod
    async def import_backup(self, user_id: UUID, archive_path: Path) -> list[str]: ...
```

- [ ] **Step 2: Verify it imports cleanly**

```bash
cd engine && uv run python -c "from resumeforge.data.base_store import BaseStore; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add engine/resumeforge/data/base_store.py
git commit -m "feat(store): add BaseStore ABC with user_id-scoped async interface"
```

---

### Task 5: JsonStore

**Files:**
- Create: `engine/resumeforge/data/json_store.py`
- Create: `engine/tests/test_json_store.py`

- [ ] **Step 1: Write failing tests for JsonStore**

Create `engine/tests/test_json_store.py`:

```python
"""Tests for JsonStore — must pass identically to existing store tests."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

import pytest

from resumeforge.data.json_store import JsonStore
from resumeforge.data.schema import Experience, Position, Profile, Skills

USER_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture()
def store(tmp_path: Path) -> JsonStore:
    return JsonStore(data_dir=tmp_path / "data")


class TestJsonStoreProfile:
    @pytest.mark.asyncio
    async def test_get_profile_returns_default(self, store: JsonStore) -> None:
        profile = await store.get_profile(USER_ID)
        assert profile.name == ""
        assert profile.email == ""

    @pytest.mark.asyncio
    async def test_save_and_get_profile(self, store: JsonStore) -> None:
        profile = Profile(name="Test User", email="test@example.com")
        await store.save_profile(USER_ID, profile)
        retrieved = await store.get_profile(USER_ID)
        assert retrieved.name == "Test User"
        assert retrieved.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_user_id_ignored(self, store: JsonStore) -> None:
        """JsonStore stores one copy regardless of user_id."""
        profile = Profile(name="Single User")
        await store.save_profile(USER_ID, profile)
        other_id = UUID("00000000-0000-0000-0000-000000000002")
        retrieved = await store.get_profile(other_id)
        assert retrieved.name == "Single User"


class TestJsonStoreJobs:
    @pytest.mark.asyncio
    async def test_list_jobs_empty(self, store: JsonStore) -> None:
        jobs = await store.list_jobs(USER_ID)
        assert jobs == []

    @pytest.mark.asyncio
    async def test_save_and_list_job(self, store: JsonStore) -> None:
        from resumeforge.data.schema import JobDescription
        job = JobDescription(slug="test-job", title="SWE", company="Acme", description="desc")
        await store.save_job(USER_ID, job)
        jobs = await store.list_jobs(USER_ID)
        assert len(jobs) == 1
        assert jobs[0].slug == "test-job"

    @pytest.mark.asyncio
    async def test_delete_job(self, store: JsonStore) -> None:
        from resumeforge.data.schema import JobDescription
        job = JobDescription(slug="del-job", title="X", company="Y", description="Z")
        await store.save_job(USER_ID, job)
        deleted = await store.delete_job(USER_ID, "del-job")
        assert deleted is True
        assert await store.get_job(USER_ID, "del-job") is None

    @pytest.mark.asyncio
    async def test_delete_missing_job(self, store: JsonStore) -> None:
        deleted = await store.delete_job(USER_ID, "no-such-job")
        assert deleted is False
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd engine && uv run pytest tests/test_json_store.py -x
```

Expected: `ImportError` — `JsonStore` not defined.

- [ ] **Step 3: Create json_store.py**

Create `engine/resumeforge/data/json_store.py`:

```python
"""JsonStore — file-based storage backend (community edition)."""

from __future__ import annotations

import contextlib
import json
import zipfile
from pathlib import Path
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel

from resumeforge.data.base_store import BaseStore
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

# Sentinel output dir (relative to data_dir parent)
_OUTPUT_SUBDIR = "output"


class JsonStore(BaseStore):
    """Reads/writes JSON files in data_dir. user_id is accepted but ignored."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._jobs_dir = data_dir / "jobs"
        self._output_dir = data_dir.parent / _OUTPUT_SUBDIR

    def _ensure_dirs(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._jobs_dir.mkdir(parents=True, exist_ok=True)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def _read(self, path: Path, model: type[T]) -> T:
        if not path.exists():
            return model()
        raw = json.loads(path.read_text(encoding="utf-8"))
        return model.model_validate(raw)

    def _write(self, path: Path, model: BaseModel) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(model.model_dump_json(indent=2, exclude_none=False), encoding="utf-8")

    # --- Profile ---

    async def get_profile(self, user_id: UUID) -> Profile:
        self._ensure_dirs()
        return self._read(self._data_dir / "profile.json", Profile)

    async def save_profile(self, user_id: UUID, profile: Profile) -> None:
        self._ensure_dirs()
        self._write(self._data_dir / "profile.json", profile)

    # --- Experience ---

    async def get_experience(self, user_id: UUID) -> Experience:
        self._ensure_dirs()
        return self._read(self._data_dir / "experience.json", Experience)

    async def save_experience(self, user_id: UUID, experience: Experience) -> None:
        self._ensure_dirs()
        self._write(self._data_dir / "experience.json", experience)

    # --- Skills ---

    async def get_skills(self, user_id: UUID) -> Skills:
        self._ensure_dirs()
        return self._read(self._data_dir / "skills.json", Skills)

    async def save_skills(self, user_id: UUID, skills: Skills) -> None:
        self._ensure_dirs()
        self._write(self._data_dir / "skills.json", skills)

    # --- Education ---

    async def get_education(self, user_id: UUID) -> Education:
        self._ensure_dirs()
        return self._read(self._data_dir / "education.json", Education)

    async def save_education(self, user_id: UUID, education: Education) -> None:
        self._ensure_dirs()
        self._write(self._data_dir / "education.json", education)

    # --- Projects ---

    async def get_projects(self, user_id: UUID) -> Projects:
        self._ensure_dirs()
        return self._read(self._data_dir / "projects.json", Projects)

    async def save_projects(self, user_id: UUID, projects: Projects) -> None:
        self._ensure_dirs()
        self._write(self._data_dir / "projects.json", projects)

    # --- Certifications ---

    async def get_certifications(self, user_id: UUID) -> Certifications:
        self._ensure_dirs()
        return self._read(self._data_dir / "certifications.json", Certifications)

    async def save_certifications(self, user_id: UUID, certifications: Certifications) -> None:
        self._ensure_dirs()
        self._write(self._data_dir / "certifications.json", certifications)

    # --- Meta ---

    async def get_meta(self, user_id: UUID) -> Meta:
        self._ensure_dirs()
        return self._read(self._data_dir / "meta.json", Meta)

    async def save_meta(self, user_id: UUID, meta: Meta) -> None:
        self._ensure_dirs()
        self._write(self._data_dir / "meta.json", meta)

    # --- Jobs ---

    async def list_jobs(self, user_id: UUID) -> list[JobDescription]:
        self._ensure_dirs()
        jobs: list[JobDescription] = []
        for f in sorted(self._jobs_dir.glob("*.json")):
            with contextlib.suppress(json.JSONDecodeError, ValueError):
                jobs.append(JobDescription.model_validate(json.loads(f.read_text(encoding="utf-8"))))
        return jobs

    async def get_job(self, user_id: UUID, slug: str) -> JobDescription | None:
        self._ensure_dirs()
        path = self._jobs_dir / f"{slug}.json"
        if not path.exists():
            return None
        return JobDescription.model_validate(json.loads(path.read_text(encoding="utf-8")))

    async def save_job(self, user_id: UUID, job: JobDescription) -> None:
        self._ensure_dirs()
        self._write(self._jobs_dir / f"{job.slug}.json", job)

    async def delete_job(self, user_id: UUID, slug: str) -> bool:
        path = self._jobs_dir / f"{slug}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    # --- Backup ---

    async def export_backup(self, user_id: UUID, output_path: Path) -> Path:
        self._ensure_dirs()
        output_path = output_path.with_suffix(".zip")
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for f in self._data_dir.glob("*.json"):
                if f.name == "profile.json":
                    continue
                zf.write(f, f"data/{f.name}")
            for f in self._jobs_dir.glob("*.json"):
                zf.write(f, f"data/jobs/{f.name}")
        return output_path

    async def import_backup(self, user_id: UUID, archive_path: Path) -> list[str]:
        self._ensure_dirs()
        restored: list[str] = []
        with zipfile.ZipFile(archive_path, "r") as zf:
            for name in zf.namelist():
                if name.startswith("data/") and name.endswith(".json"):
                    dest = self._data_dir.parent / Path(name)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(zf.read(name))
                    restored.append(name)
        return restored

    def init_data_dir(self) -> None:
        """Seed empty JSON files on first run (called by app startup)."""
        self._ensure_dirs()
        sections: list[tuple[Path, BaseModel]] = [
            (self._data_dir / "experience.json", Experience()),
            (self._data_dir / "skills.json", Skills()),
            (self._data_dir / "education.json", Education()),
            (self._data_dir / "projects.json", Projects()),
            (self._data_dir / "certifications.json", Certifications()),
            (self._data_dir / "meta.json", Meta()),
        ]
        for path, model in sections:
            if not path.exists():
                self._write(path, model)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd engine && uv run pytest tests/test_json_store.py -x
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add engine/resumeforge/data/json_store.py engine/tests/test_json_store.py
git commit -m "feat(store): add JsonStore — async BaseStore implementation wrapping JSON files"
```

---

### Task 6: factory.py + update store.py

**Files:**
- Create: `engine/resumeforge/data/factory.py`
- Modify: `engine/resumeforge/data/store.py`

- [ ] **Step 1: Create factory.py**

```python
"""Store factory — returns the correct BaseStore for the current engine mode."""

from __future__ import annotations

from pathlib import Path

from resumeforge.data.base_store import BaseStore
from resumeforge.data.json_store import JsonStore
from resumeforge.settings import settings

# Paths used by JsonStore (community edition)
_ENGINE_ROOT = Path(__file__).parent.parent.parent  # engine/
_DATA_DIR = _ENGINE_ROOT / "data"

# Singleton store instance — created once at app startup
_store: BaseStore | None = None


def init_store() -> BaseStore:
    """Create and cache the store instance. Called once at app startup."""
    global _store
    if _store is not None:
        return _store
    if settings.is_cloud:
        from resumeforge.data.postgres_store import PostgresStore
        _store = PostgresStore(settings.database_url)
    else:
        _store = JsonStore(_DATA_DIR)
    return _store


def get_store() -> BaseStore:
    """FastAPI Depends target — returns the cached store instance."""
    if _store is None:
        return init_store()
    return _store
```

- [ ] **Step 2: Update store.py to thin re-export**

Replace the full body of `engine/resumeforge/data/store.py` with:

```python
"""store.py — compatibility re-export. Use json_store.py or factory.py directly."""

from __future__ import annotations

# Legacy path constants (used by existing tests + data.py route for OUTPUT_DIR)
from resumeforge.data.json_store import JsonStore as _JsonStore
from resumeforge.data.factory import _DATA_DIR, get_store as _get_store
from pathlib import Path

DATA_DIR = _DATA_DIR
JOBS_DIR = _DATA_DIR / "jobs"
OUTPUT_DIR = _DATA_DIR.parent / "output"

# Legacy sync shim used by app.py startup — wraps JsonStore.init_data_dir()
def init_data_dir() -> None:
    _js = _JsonStore(_DATA_DIR)
    _js.init_data_dir()

# Legacy sync accessors used by app.py main()
def get_meta() -> object:  # type: ignore[return]
    import asyncio
    js = _JsonStore(_DATA_DIR)
    from uuid import UUID
    return asyncio.run(js.get_meta(UUID("00000000-0000-0000-0000-000000000001")))
```

- [ ] **Step 3: Verify existing tests still pass**

```bash
cd engine && uv run pytest tests/test_data.py -x
```

Expected: all PASS (existing tests monkeypatch `store.DATA_DIR` etc., which still exist).

- [ ] **Step 4: Commit**

```bash
git add engine/resumeforge/data/factory.py engine/resumeforge/data/store.py
git commit -m "feat(store): add factory.py + make store.py a thin compat re-export"
```

---

## Group C — Auth Layer

### Task 7: Auth models

**Files:**
- Create: `engine/resumeforge/auth/__init__.py`
- Create: `engine/resumeforge/auth/models.py`

- [ ] **Step 1: Write failing tests**

Create `engine/tests/test_auth.py` (models section only for now):

```python
"""Tests for auth models, JWT, and register/login endpoints."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest


class TestAuthModels:
    def test_user_create_requires_email_and_password(self) -> None:
        from resumeforge.auth.models import UserCreate
        u = UserCreate(email="test@example.com", password="secret123")
        assert u.email == "test@example.com"

    def test_token_defaults(self) -> None:
        from resumeforge.auth.models import Token
        t = Token(access_token="abc", refresh_token="xyz")
        assert t.token_type == "bearer"
        assert t.expires_in == 900

    def test_user_has_id(self) -> None:
        from resumeforge.auth.models import User
        u = User(id=uuid4(), email="a@b.com", is_active=True)
        assert isinstance(u.id, UUID)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd engine && uv run pytest tests/test_auth.py::TestAuthModels -x
```

Expected: `ImportError`

- [ ] **Step 3: Create auth package**

```bash
touch engine/resumeforge/auth/__init__.py
```

Create `engine/resumeforge/auth/models.py`:

```python
"""Auth Pydantic models."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserInDB(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    email: str
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


class User(BaseModel):
    id: UUID
    email: str
    is_active: bool


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900  # seconds — matches access token TTL
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd engine && uv run pytest tests/test_auth.py::TestAuthModels -x
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/resumeforge/auth/__init__.py engine/resumeforge/auth/models.py engine/tests/test_auth.py
git commit -m "feat(auth): add auth package with User, Token Pydantic models"
```

---

### Task 8: JWT utilities

**Files:**
- Create: `engine/resumeforge/auth/jwt.py`

- [ ] **Step 1: Add JWT tests to test_auth.py**

Append to `engine/tests/test_auth.py`:

```python
class TestJWT:
    def test_create_and_verify_access_token(self) -> None:
        from resumeforge.auth.jwt import create_access_token, verify_token
        user_id = uuid4()
        token = create_access_token(user_id)
        assert isinstance(token, str)
        extracted = verify_token(token)
        assert extracted == user_id

    def test_create_and_verify_refresh_token(self) -> None:
        from resumeforge.auth.jwt import create_refresh_token, verify_token
        user_id = uuid4()
        token = create_refresh_token(user_id)
        extracted = verify_token(token)
        assert extracted == user_id

    def test_invalid_token_raises(self) -> None:
        from jose import JWTError
        from resumeforge.auth.jwt import verify_token
        with pytest.raises(JWTError):
            verify_token("not.a.valid.token")
```

- [ ] **Step 2: Run to verify failure**

```bash
cd engine && uv run pytest tests/test_auth.py::TestJWT -x
```

Expected: `ImportError`

- [ ] **Step 3: Create jwt.py**

```python
"""JWT token utilities."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt  # noqa: F401 — re-exported for callers

_ALGORITHM = "HS256"
_ACCESS_EXPIRE_MINUTES = 15
_REFRESH_EXPIRE_DAYS = 7


def _secret() -> str:
    secret = os.environ.get("RF_SECRET_KEY", "dev-secret-do-not-use-in-production")
    return secret


def create_access_token(user_id: UUID) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": exp, "type": "access"}, _secret(), algorithm=_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=_REFRESH_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": exp, "type": "refresh"}, _secret(), algorithm=_ALGORITHM)


def verify_token(token: str) -> UUID:
    """Decode and validate a JWT. Raises JWTError on failure."""
    payload = jwt.decode(token, _secret(), algorithms=[_ALGORITHM])
    sub: str | None = payload.get("sub")
    if sub is None:
        raise JWTError("Token missing 'sub' claim")
    return UUID(sub)
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd engine && uv run pytest tests/test_auth.py::TestJWT -x
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/resumeforge/auth/jwt.py engine/tests/test_auth.py
git commit -m "feat(auth): add JWT create_access_token / create_refresh_token / verify_token"
```

---

### Task 9: Auth dependencies

**Files:**
- Create: `engine/resumeforge/auth/dependencies.py`

- [ ] **Step 1: Create dependencies.py**

```python
"""FastAPI dependencies for auth — get_current_user."""

from __future__ import annotations

from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from resumeforge.api.errors import APIError
from resumeforge.auth.models import User
from resumeforge.auth.jwt import verify_token
from resumeforge.settings import settings

_security = HTTPBearer(auto_error=False)

# Community-edition sentinel — JsonStore ignores user_id
LOCAL_USER_ID = UUID("00000000-0000-0000-0000-000000000001")
LOCAL_USER = User(id=LOCAL_USER_ID, email="local@localhost", is_active=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> User:
    """Return the authenticated user, or LOCAL_USER in community (local) mode."""
    if not settings.is_cloud:
        return LOCAL_USER
    if credentials is None:
        raise APIError(401, "Authentication required.", "UNAUTHORIZED")
    try:
        user_id = verify_token(credentials.credentials)
    except JWTError:
        raise APIError(401, "Invalid or expired token.", "UNAUTHORIZED")
    # In cloud mode, verify user exists (PostgresStore handles this in auth routes).
    # For now, trust the token — user existence is validated at login/register.
    return User(id=user_id, email="", is_active=True)
```

- [ ] **Step 2: Verify import**

```bash
cd engine && uv run python -c "from resumeforge.auth.dependencies import get_current_user, LOCAL_USER; print(LOCAL_USER)"
```

Expected: `id=UUID('00000000-...') email='local@localhost' is_active=True`

- [ ] **Step 3: Commit**

```bash
git add engine/resumeforge/auth/dependencies.py
git commit -m "feat(auth): add get_current_user FastAPI dependency (returns LOCAL_USER in community mode)"
```

---

### Task 10: Auth routes (register / login / refresh)

**Files:**
- Create: `engine/resumeforge/api/routes/auth.py`

- [ ] **Step 1: Add auth route tests to test_auth.py**

Append to `engine/tests/test_auth.py`:

```python
class TestAuthRoutes:
    @pytest.fixture()
    def client(self) -> object:
        from fastapi.testclient import TestClient
        from resumeforge.api.app import app
        return TestClient(app)

    def test_register_returns_tokens(self, client: object) -> None:
        resp = client.post("/api/auth/register", json={"email": "new@test.com", "password": "pass123"})
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    def test_register_duplicate_email_returns_409(self, client: object) -> None:
        client.post("/api/auth/register", json={"email": "dup@test.com", "password": "pass123"})
        resp = client.post("/api/auth/register", json={"email": "dup@test.com", "password": "pass123"})
        assert resp.status_code == 409
        assert resp.json()["code"] == "EMAIL_TAKEN"

    def test_login_success(self, client: object) -> None:
        client.post("/api/auth/register", json={"email": "login@test.com", "password": "pass123"})
        resp = client.post("/api/auth/login", json={"email": "login@test.com", "password": "pass123"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password_returns_401(self, client: object) -> None:
        client.post("/api/auth/register", json={"email": "wp@test.com", "password": "correct"})
        resp = client.post("/api/auth/login", json={"email": "wp@test.com", "password": "wrong"})
        assert resp.status_code == 401
        assert resp.json()["code"] == "INVALID_CREDENTIALS"

    def test_refresh_returns_new_access_token(self, client: object) -> None:
        reg = client.post("/api/auth/register", json={"email": "ref@test.com", "password": "pass123"})
        refresh_token = reg.json()["refresh_token"]
        resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()
```

- [ ] **Step 2: Run to verify failure**

```bash
cd engine && uv run pytest tests/test_auth.py::TestAuthRoutes -x
```

Expected: 404 (routes not registered yet).

- [ ] **Step 3: Create auth routes**

Create `engine/resumeforge/api/routes/auth.py`:

```python
"""Auth routes — register, login, refresh."""

from __future__ import annotations

import hashlib
from uuid import uuid4

from fastapi import APIRouter
from passlib.context import CryptContext

from resumeforge.api.errors import APIError
from resumeforge.auth.jwt import create_access_token, create_refresh_token, verify_token
from resumeforge.auth.models import Token, UserCreate, UserInDB, UserLogin
from jose import JWTError

router = APIRouter(prefix="/api/auth", tags=["Auth"])

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory user store for community mode (cloud mode will use PostgresStore)
# Keyed by email → UserInDB
_users: dict[str, UserInDB] = {}
# Refresh token → user_id mapping (hash stored for security)
_refresh_tokens: dict[str, str] = {}  # token_hash → str(user_id)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/register", response_model=Token, status_code=201)
async def register(body: UserCreate) -> Token:
    """Register a new user and return tokens."""
    if body.email in _users:
        raise APIError(409, f"Email '{body.email}' is already registered.", "EMAIL_TAKEN")
    user = UserInDB(
        id=uuid4(),
        email=body.email,
        hashed_password=_pwd_context.hash(body.password),
    )
    _users[body.email] = user
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    _refresh_tokens[_hash_token(refresh)] = str(user.id)
    return Token(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=Token)
async def login(body: UserLogin) -> Token:
    """Authenticate with email + password and return tokens."""
    user = _users.get(body.email)
    if user is None or not _pwd_context.verify(body.password, user.hashed_password):
        raise APIError(401, "Invalid email or password.", "INVALID_CREDENTIALS")
    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    _refresh_tokens[_hash_token(refresh)] = str(user.id)
    return Token(access_token=access, refresh_token=refresh)


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=Token)
async def refresh(body: RefreshRequest) -> Token:
    """Exchange a valid refresh token for a new access token."""
    try:
        user_id = verify_token(body.refresh_token)
    except JWTError:
        raise APIError(401, "Invalid or expired refresh token.", "UNAUTHORIZED")
    token_hash = _hash_token(body.refresh_token)
    if token_hash not in _refresh_tokens:
        raise APIError(401, "Refresh token revoked.", "UNAUTHORIZED")
    access = create_access_token(user_id)
    new_refresh = create_refresh_token(user_id)
    # Rotate refresh token
    del _refresh_tokens[token_hash]
    _refresh_tokens[_hash_token(new_refresh)] = str(user_id)
    return Token(access_token=access, refresh_token=new_refresh)
```

> **Note:** `_users` and `_refresh_tokens` are in-memory dicts — fine for community mode and tests. PostgresStore replaces them in cloud mode (Task 14).

- [ ] **Step 4: Register router in app.py**

In `engine/resumeforge/api/app.py`, add to imports:
```python
from resumeforge.api.routes import analyze, auth, build, config, data, jobs, tailor, templates
```

And add after the existing `app.include_router(config.router)` line:
```python
app.include_router(auth.router)
```

Also add to the `openapi_tags` list:
```python
{"name": "Auth", "description": "User registration and authentication."},
```

- [ ] **Step 5: Run auth tests**

```bash
cd engine && uv run pytest tests/test_auth.py -x
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add engine/resumeforge/api/routes/auth.py engine/resumeforge/api/app.py engine/tests/test_auth.py
git commit -m "feat(auth): add register/login/refresh routes with bcrypt + JWT"
```

---

## Group D — Route Injection

### Task 11: Update data + jobs + config routes to use BaseStore

**Files:**
- Modify: `engine/resumeforge/api/routes/data.py`
- Modify: `engine/resumeforge/api/routes/jobs.py`
- Modify: `engine/resumeforge/api/routes/config.py`

- [ ] **Step 1: Verify existing API tests pass before touching routes**

```bash
cd engine && uv run pytest tests/test_api.py -x
```

Expected: all PASS (baseline).

- [ ] **Step 2: Update data.py**

Replace `engine/resumeforge/api/routes/data.py` with:

```python
"""Data routes — GET/PUT /api/data/{section}, POST /api/data/import, GET /api/data/export."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse

from resumeforge.api.errors import not_found
from resumeforge.api.models import ImportResponse
from resumeforge.auth.dependencies import get_current_user, User
from resumeforge.data.base_store import BaseStore
from resumeforge.data.factory import get_store
from resumeforge.data.schema import (
    Certifications,
    Education,
    Experience,
    Profile,
    Projects,
    Skills,
)
from resumeforge.data import store as _legacy_store  # for OUTPUT_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["Data"])


@router.get("/profile", response_model=Profile)
async def get_profile(
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Profile:
    return await db.get_profile(user.id)


@router.put("/profile", response_model=Profile)
async def update_profile(
    profile: Profile,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Profile:
    await db.save_profile(user.id, profile)
    return profile


@router.get("/experience", response_model=Experience)
async def get_experience(
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Experience:
    return await db.get_experience(user.id)


@router.put("/experience", response_model=Experience)
async def update_experience(
    experience: Experience,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Experience:
    await db.save_experience(user.id, experience)
    return experience


@router.get("/skills", response_model=Skills)
async def get_skills(
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Skills:
    return await db.get_skills(user.id)


@router.put("/skills", response_model=Skills)
async def update_skills(
    skills: Skills,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Skills:
    await db.save_skills(user.id, skills)
    return skills


@router.get("/education", response_model=Education)
async def get_education(
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Education:
    return await db.get_education(user.id)


@router.put("/education", response_model=Education)
async def update_education(
    education: Education,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Education:
    await db.save_education(user.id, education)
    return education


@router.get("/projects", response_model=Projects)
async def get_projects(
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Projects:
    return await db.get_projects(user.id)


@router.put("/projects", response_model=Projects)
async def update_projects(
    projects: Projects,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Projects:
    await db.save_projects(user.id, projects)
    return projects


@router.get("/certifications", response_model=Certifications)
async def get_certifications(
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Certifications:
    return await db.get_certifications(user.id)


@router.put("/certifications", response_model=Certifications)
async def update_certifications(
    certifications: Certifications,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Certifications:
    await db.save_certifications(user.id, certifications)
    return certifications


@router.get("/export")
async def export_backup(
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> FileResponse:
    tmp = _legacy_store.OUTPUT_DIR / "backup.zip"
    await db.export_backup(user.id, tmp)
    return FileResponse(path=str(tmp), filename="resumeforge_backup.zip", media_type="application/zip")


@router.post("/import", response_model=ImportResponse)
async def import_backup(
    archive_path: str = Query(..., description="Absolute path to backup archive"),
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> ImportResponse:
    path = Path(archive_path)
    if not path.exists():
        raise not_found("Archive", archive_path)
    restored = await db.import_backup(user.id, path)
    return ImportResponse(restored=restored, count=len(restored))
```

- [ ] **Step 3: Update jobs.py**

Replace `engine/resumeforge/api/routes/jobs.py` with:

```python
"""Jobs routes — CRUD for /api/jobs."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends

from resumeforge.api.errors import not_found
from resumeforge.api.models import DeleteResponse
from resumeforge.auth.dependencies import User, get_current_user
from resumeforge.data.base_store import BaseStore
from resumeforge.data.factory import get_store
from resumeforge.data.schema import JobDescription

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("", response_model=list[JobDescription])
async def list_jobs(
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> list[JobDescription]:
    return await db.list_jobs(user.id)


@router.post("", response_model=JobDescription)
async def create_job(
    job: JobDescription,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> JobDescription:
    await db.save_job(user.id, job)
    return job


@router.get("/{slug}", response_model=JobDescription)
async def get_job(
    slug: str,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> JobDescription:
    job = await db.get_job(user.id, slug)
    if job is None:
        raise not_found("Job", slug)
    return job


@router.put("/{slug}", response_model=JobDescription)
async def update_job(
    slug: str,
    job: JobDescription,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> JobDescription:
    existing = await db.get_job(user.id, slug)
    if existing is None:
        raise not_found("Job", slug)
    updated = job.model_copy(update={"slug": slug})
    await db.save_job(user.id, updated)
    return updated


@router.delete("/{slug}", response_model=DeleteResponse)
async def delete_job(
    slug: str,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> DeleteResponse:
    if not await db.delete_job(user.id, slug):
        raise not_found("Job", slug)
    return DeleteResponse(status="deleted", slug=slug)
```

- [ ] **Step 4: Update config.py**

Replace `engine/resumeforge/api/routes/config.py` with:

```python
"""Config routes — GET /api/config and PATCH /api/config."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from resumeforge.auth.dependencies import User, get_current_user
from resumeforge.data.base_store import BaseStore
from resumeforge.data.factory import get_store
from resumeforge.data.schema import Meta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["Config"])


class MetaPatch(BaseModel):
    default_locale: str | None = None
    default_template: str | None = None
    default_format: str | None = None
    engine: dict[str, Any] | None = None
    ai: dict[str, Any] | None = None
    style: dict[str, Any] | None = None


@router.get("", response_model=Meta)
async def get_config(
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Meta:
    return await db.get_meta(user.id)


@router.patch("", response_model=Meta)
async def patch_config(
    patch: MetaPatch,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Meta:
    meta = await db.get_meta(user.id)
    current = meta.model_dump()
    if patch.default_locale is not None:
        current["default_locale"] = patch.default_locale
    if patch.default_template is not None:
        current["default_template"] = patch.default_template
    if patch.default_format is not None:
        current["default_format"] = patch.default_format
    for key, value in [("engine", patch.engine), ("ai", patch.ai), ("style", patch.style)]:
        if value is not None:
            current[key] = {**current.get(key, {}), **value}
    updated = Meta.model_validate(current)
    await db.save_meta(user.id, updated)
    return updated


@router.put("", response_model=Meta)
async def update_config(
    meta: Meta,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> Meta:
    await db.save_meta(user.id, meta)
    return meta
```

- [ ] **Step 5: Run full API tests**

```bash
cd engine && uv run pytest tests/test_api.py -x
```

Expected: all PASS (community mode — `get_current_user` returns `LOCAL_USER`, `get_store` returns `JsonStore`).

- [ ] **Step 6: Run mypy**

```bash
cd engine && uv run mypy resumeforge/api/routes/data.py resumeforge/api/routes/jobs.py resumeforge/api/routes/config.py
```

Expected: no errors.

- [ ] **Step 7: Commit**

```bash
git add engine/resumeforge/api/routes/data.py engine/resumeforge/api/routes/jobs.py engine/resumeforge/api/routes/config.py
git commit -m "refactor(routes): inject BaseStore + User via FastAPI Depends on data/jobs/config routes"
```

> **Also update** `routes/build.py`, `routes/tailor.py`, `routes/analyze.py` following the identical pattern: replace `store.get_X()` with `await db.get_X(user.id)`, add `user: User = Depends(get_current_user)` and `db: BaseStore = Depends(get_store)` parameters. Commit separately per file.

---

## Group E — PostgreSQL Backend

### Task 12: ORM models + Alembic

**Files:**
- Create: `engine/resumeforge/data/orm_models.py`
- Create: `engine/alembic.ini`
- Create: `engine/alembic/env.py` (via `alembic init`)

- [ ] **Step 1: Create ORM models**

Create `engine/resumeforge/data/orm_models.py`:

```python
"""SQLAlchemy ORM models for the cloud (PostgreSQL) backend."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class RefreshTokenORM(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)


class ResumeDataORM(Base):
    """Generic JSONB store — one row per user per section."""
    __tablename__ = "resume_data"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    section: Mapped[str] = mapped_column(String(50), primary_key=True)  # "profile", "experience", etc.
    data_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class JobORM(Base):
    __tablename__ = "jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), primary_key=True)
    data_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
```

- [ ] **Step 2: Init Alembic**

```bash
cd engine && uv run alembic init alembic
```

- [ ] **Step 3: Update alembic/env.py to use ORM models**

In `engine/alembic/env.py`, replace the target metadata line:

```python
from resumeforge.data.orm_models import Base
target_metadata = Base.metadata
```

Also update `sqlalchemy.url` in `alembic.ini` to read from env:

In `engine/alembic/env.py` `run_migrations_online()` function, set the URL from the environment:
```python
import os
connectable = create_engine(os.environ["RF_DATABASE_URL"].replace("+asyncpg", ""))
```

- [ ] **Step 4: Verify Alembic can generate a migration (requires DB)**

```bash
cd engine && RF_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/rftest \
  uv run alembic revision --autogenerate -m "initial_schema"
```

Expected: new file in `engine/alembic/versions/`.

- [ ] **Step 5: Commit**

```bash
git add engine/resumeforge/data/orm_models.py engine/alembic.ini engine/alembic/
git commit -m "feat(db): add SQLAlchemy ORM models + Alembic init for PostgreSQL backend"
```

---

### Task 13: PostgresStore

**Files:**
- Create: `engine/resumeforge/data/postgres_store.py`
- Modify: `engine/resumeforge/data/factory.py`

- [ ] **Step 1: Create PostgresStore**

Create `engine/resumeforge/data/postgres_store.py`:

```python
"""PostgresStore — SQLAlchemy async backend (cloud edition)."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from resumeforge.data.base_store import BaseStore
from resumeforge.data.orm_models import JobORM, ResumeDataORM
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

_SECTION_MODELS = {
    "profile": Profile,
    "experience": Experience,
    "skills": Skills,
    "education": Education,
    "projects": Projects,
    "certifications": Certifications,
    "meta": Meta,
}


class PostgresStore(BaseStore):
    """Stores all resume data as JSON in PostgreSQL resume_data table."""

    def __init__(self, database_url: str) -> None:
        self._engine = create_async_engine(database_url, echo=False)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    def _session(self) -> AsyncSession:
        return self._session_factory()

    async def _get_section(self, user_id: UUID, section: str, model: type) -> object:
        async with self._session() as s:
            row = await s.get(ResumeDataORM, (user_id, section))
            if row is None:
                return model()
            return model.model_validate_json(row.data_json)

    async def _save_section(self, user_id: UUID, section: str, data: object) -> None:
        async with self._session() as s:
            row = await s.get(ResumeDataORM, (user_id, section))
            data_json = data.model_dump_json(indent=2, exclude_none=False)  # type: ignore[attr-defined]
            if row is None:
                s.add(ResumeDataORM(user_id=user_id, section=section, data_json=data_json))
            else:
                row.data_json = data_json
            await s.commit()

    async def get_profile(self, user_id: UUID) -> Profile:
        return await self._get_section(user_id, "profile", Profile)  # type: ignore[return-value]

    async def save_profile(self, user_id: UUID, profile: Profile) -> None:
        await self._save_section(user_id, "profile", profile)

    async def get_experience(self, user_id: UUID) -> Experience:
        return await self._get_section(user_id, "experience", Experience)  # type: ignore[return-value]

    async def save_experience(self, user_id: UUID, experience: Experience) -> None:
        await self._save_section(user_id, "experience", experience)

    async def get_skills(self, user_id: UUID) -> Skills:
        return await self._get_section(user_id, "skills", Skills)  # type: ignore[return-value]

    async def save_skills(self, user_id: UUID, skills: Skills) -> None:
        await self._save_section(user_id, "skills", skills)

    async def get_education(self, user_id: UUID) -> Education:
        return await self._get_section(user_id, "education", Education)  # type: ignore[return-value]

    async def save_education(self, user_id: UUID, education: Education) -> None:
        await self._save_section(user_id, "education", education)

    async def get_projects(self, user_id: UUID) -> Projects:
        return await self._get_section(user_id, "projects", Projects)  # type: ignore[return-value]

    async def save_projects(self, user_id: UUID, projects: Projects) -> None:
        await self._save_section(user_id, "projects", projects)

    async def get_certifications(self, user_id: UUID) -> Certifications:
        return await self._get_section(user_id, "certifications", Certifications)  # type: ignore[return-value]

    async def save_certifications(self, user_id: UUID, certifications: Certifications) -> None:
        await self._save_section(user_id, "certifications", certifications)

    async def get_meta(self, user_id: UUID) -> Meta:
        return await self._get_section(user_id, "meta", Meta)  # type: ignore[return-value]

    async def save_meta(self, user_id: UUID, meta: Meta) -> None:
        await self._save_section(user_id, "meta", meta)

    async def list_jobs(self, user_id: UUID) -> list[JobDescription]:
        async with self._session() as s:
            result = await s.execute(select(JobORM).where(JobORM.user_id == user_id))
            rows = result.scalars().all()
            return [JobDescription.model_validate_json(r.data_json) for r in rows]

    async def get_job(self, user_id: UUID, slug: str) -> JobDescription | None:
        async with self._session() as s:
            row = await s.get(JobORM, (user_id, slug))
            if row is None:
                return None
            return JobDescription.model_validate_json(row.data_json)

    async def save_job(self, user_id: UUID, job: JobDescription) -> None:
        async with self._session() as s:
            row = await s.get(JobORM, (user_id, job.slug))
            data_json = job.model_dump_json(indent=2, exclude_none=False)
            if row is None:
                s.add(JobORM(user_id=user_id, slug=job.slug, data_json=data_json))
            else:
                row.data_json = data_json
            await s.commit()

    async def delete_job(self, user_id: UUID, slug: str) -> bool:
        async with self._session() as s:
            row = await s.get(JobORM, (user_id, slug))
            if row is None:
                return False
            await s.delete(row)
            await s.commit()
            return True

    async def export_backup(self, user_id: UUID, output_path: Path) -> Path:
        output_path = output_path.with_suffix(".zip")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for section, model in _SECTION_MODELS.items():
                if section == "profile":
                    continue  # PII — never export
                data = await self._get_section(user_id, section, model)
                zf.writestr(f"data/{section}.json", data.model_dump_json(indent=2))  # type: ignore[attr-defined]
            for job in await self.list_jobs(user_id):
                zf.writestr(f"data/jobs/{job.slug}.json", job.model_dump_json(indent=2))
        return output_path

    async def import_backup(self, user_id: UUID, archive_path: Path) -> list[str]:
        restored: list[str] = []
        with zipfile.ZipFile(archive_path, "r") as zf:
            for name in zf.namelist():
                raw = json.loads(zf.read(name))
                if name == "data/profile.json":
                    continue
                elif name.startswith("data/jobs/") and name.endswith(".json"):
                    job = JobDescription.model_validate(raw)
                    await self.save_job(user_id, job)
                    restored.append(name)
                elif name.startswith("data/") and name.endswith(".json"):
                    section = name.removeprefix("data/").removesuffix(".json")
                    model_cls = _SECTION_MODELS.get(section)
                    if model_cls:
                        await self._save_section(user_id, section, model_cls.model_validate(raw))
                        restored.append(name)
        return restored
```

- [ ] **Step 2: Update factory.py to wire PostgresStore**

The `init_store()` in `factory.py` already imports `PostgresStore` conditionally. No changes needed.

- [ ] **Step 3: Verify imports clean in both modes**

```bash
cd engine && uv run python -c "from resumeforge.data.factory import get_store; s = get_store(); print(type(s).__name__)"
```

Expected: `JsonStore`

- [ ] **Step 4: Commit**

```bash
git add engine/resumeforge/data/postgres_store.py
git commit -m "feat(store): add PostgresStore — SQLAlchemy async implementation for cloud backend"
```

---

## Group F — GitHub Integration

### Task 14: GitHub client — import functions

**Files:**
- Create: `engine/resumeforge/integrations/__init__.py`
- Create: `engine/resumeforge/integrations/github.py`
- Create: `engine/tests/test_github_integration.py`

- [ ] **Step 1: Write failing tests**

Create `engine/tests/test_github_integration.py`:

```python
"""Tests for GitHub integration — httpx calls mocked with respx."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
import respx
from httpx import Response

from resumeforge.integrations.github import GitHubClient


class TestGitHubImport:
    @pytest.fixture()
    def client(self) -> GitHubClient:
        return GitHubClient(token="test-token")

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_pinned_repos(self, client: GitHubClient) -> None:
        respx.post("https://api.github.com/graphql").mock(
            return_value=Response(
                200,
                json={
                    "data": {
                        "user": {
                            "pinnedItems": {
                                "nodes": [
                                    {
                                        "name": "resumeforge",
                                        "description": "Resume tool",
                                        "url": "https://github.com/Scorp10N/resumeforge",
                                        "pushedAt": "2026-04-01T00:00:00Z",
                                        "primaryLanguage": {"name": "Python"},
                                        "languages": {"nodes": [{"name": "Python"}, {"name": "Go"}]},
                                    }
                                ]
                            }
                        }
                    }
                },
            )
        )
        projects = await client.fetch_pinned_repos("Scorp10N")
        assert len(projects) == 1
        assert projects[0].name == "resumeforge"
        assert "Python" in projects[0].technologies
        assert projects[0].url == "https://github.com/Scorp10N/resumeforge"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_readme_summary(self, client: GitHubClient) -> None:
        respx.get("https://api.github.com/repos/Scorp10N/Scorp10N/readme").mock(
            return_value=Response(200, json={"content": "SGVsbG8gV29ybGQ=", "encoding": "base64"})
        )
        readme = await client.fetch_readme_summary("Scorp10N")
        assert readme == "Hello World"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_readme_missing(self, client: GitHubClient) -> None:
        respx.get("https://api.github.com/repos/Scorp10N/Scorp10N/readme").mock(
            return_value=Response(404)
        )
        readme = await client.fetch_readme_summary("Scorp10N")
        assert readme is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_fetch_all_public_repos(self, client: GitHubClient) -> None:
        respx.get("https://api.github.com/users/Scorp10N/repos").mock(
            return_value=Response(
                200,
                json=[
                    {
                        "name": "myrepo",
                        "description": "A repo",
                        "html_url": "https://github.com/Scorp10N/myrepo",
                        "pushed_at": "2026-03-01T00:00:00Z",
                        "language": "TypeScript",
                        "stargazers_count": 5,
                    }
                ],
            )
        )
        repos = await client.fetch_all_public_repos("Scorp10N")
        assert len(repos) == 1
        assert repos[0].name == "myrepo"
```

- [ ] **Step 2: Run to verify failure**

```bash
cd engine && uv run pytest tests/test_github_integration.py -x
```

Expected: `ImportError`

- [ ] **Step 3: Create integrations package + github.py**

```bash
touch engine/resumeforge/integrations/__init__.py
```

Create `engine/resumeforge/integrations/github.py`:

```python
"""GitHub API client — import and Pages deploy functions."""

from __future__ import annotations

import base64
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import httpx

from resumeforge.data.schema import Project


_GH_API = "https://api.github.com"
_GH_GRAPHQL = "https://api.github.com/graphql"

_PINNED_QUERY = """
query($login: String!) {
  user(login: $login) {
    pinnedItems(first: 6, types: [REPOSITORY]) {
      nodes {
        ... on Repository {
          name
          description
          url
          pushedAt
          primaryLanguage { name }
          languages(first: 5) { nodes { name } }
        }
      }
    }
  }
}
"""


class GitHubClient:
    def __init__(self, token: str) -> None:
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def fetch_pinned_repos(self, username: str) -> list[Project]:
        """Fetch pinned repositories and map to Project objects."""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _GH_GRAPHQL,
                headers=self._headers,
                json={"query": _PINNED_QUERY, "variables": {"login": username}},
                timeout=15,
            )
            resp.raise_for_status()
        nodes: list[dict[str, Any]] = (
            resp.json().get("data", {}).get("user", {}).get("pinnedItems", {}).get("nodes", [])
        )
        projects = []
        for node in nodes:
            techs = [lang["name"] for lang in node.get("languages", {}).get("nodes", [])]
            pushed = (node.get("pushedAt") or "")[:7]  # YYYY-MM
            projects.append(
                Project(
                    name=node.get("name", ""),
                    description=node.get("description") or "",
                    url=node.get("url", ""),
                    technologies=techs,
                    date=pushed,
                    tags=["github", "pinned"],
                )
            )
        return projects

    async def fetch_readme_summary(self, username: str) -> str | None:
        """Fetch the profile README (username/username repo). Returns decoded text or None."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_GH_API}/repos/{username}/{username}/readme",
                headers=self._headers,
                timeout=10,
            )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return data.get("content")

    async def fetch_contribution_stats(self, username: str) -> dict[str, Any]:
        """Return top languages and star count for a user's public repos."""
        repos = await self.fetch_all_public_repos(username)
        lang_counts: dict[str, int] = {}
        total_stars = 0
        for repo in repos:
            if repo.technologies:
                lang = repo.technologies[0]
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_GH_API}/users/{username}",
                headers=self._headers,
                timeout=10,
            )
            resp.raise_for_status()
        return {
            "top_languages": sorted(lang_counts, key=lambda k: lang_counts[k], reverse=True)[:5],
            "public_repos": resp.json().get("public_repos", 0),
        }

    async def fetch_all_public_repos(self, username: str, selected_names: list[str] | None = None) -> list[Project]:
        """Fetch all public repos. If selected_names given, filter to those."""
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{_GH_API}/users/{username}/repos",
                headers=self._headers,
                params={"type": "public", "per_page": "100", "sort": "pushed"},
                timeout=15,
            )
            resp.raise_for_status()
        repos = resp.json()
        if selected_names:
            repos = [r for r in repos if r["name"] in selected_names]
        projects = []
        for r in repos:
            pushed = (r.get("pushed_at") or "")[:7]
            lang = r.get("language")
            techs = [lang] if lang else []
            projects.append(
                Project(
                    name=r["name"],
                    description=r.get("description") or "",
                    url=r.get("html_url", ""),
                    technologies=techs,
                    date=pushed,
                    tags=["github"],
                )
            )
        return projects

    def deploy_pages(
        self,
        html_content: str,
        repo: str,
        branch: str = "gh-pages",
    ) -> str:
        """Push html_content as index.html to gh-pages branch. Returns Pages URL."""
        owner = repo.split("/")[0]
        remote_url = f"https://x-access-token:{self._token}@github.com/{repo}.git"

        with tempfile.TemporaryDirectory() as tmpdir:
            work = Path(tmpdir)
            # Clone or init gh-pages branch
            result = subprocess.run(
                ["git", "clone", "--branch", branch, "--single-branch", "--depth", "1", remote_url, str(work)],
                capture_output=True,
                timeout=60,
            )
            if result.returncode != 0:
                # Branch doesn't exist — init empty
                subprocess.run(["git", "init", str(work)], check=True)
                subprocess.run(["git", "-C", str(work), "remote", "add", "origin", remote_url], check=True)
                subprocess.run(["git", "-C", str(work), "checkout", "--orphan", branch], check=True)

            index = work / "index.html"
            index.write_text(html_content, encoding="utf-8")

            subprocess.run(["git", "-C", str(work), "add", "index.html"], check=True)
            subprocess.run(
                ["git", "-C", str(work), "commit", "--allow-empty", "-m", "chore: deploy resume via ResumeForge"],
                check=True,
            )
            push = subprocess.run(
                ["git", "-C", str(work), "push", "origin", branch],
                capture_output=True,
                timeout=60,
            )
            if push.returncode != 0:
                raise RuntimeError(f"git push failed: {push.stderr.decode()}")

        return f"https://{owner}.github.io/{repo.split('/')[-1]}"

    @property
    def _token(self) -> str:
        return self._headers["Authorization"].removeprefix("Bearer ")
```

- [ ] **Step 4: Run tests**

```bash
cd engine && uv run pytest tests/test_github_integration.py -x
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add engine/resumeforge/integrations/__init__.py engine/resumeforge/integrations/github.py engine/tests/test_github_integration.py
git commit -m "feat(integrations): add GitHub API client — pinned repos, README, stats, all repos, Pages deploy"
```

---

### Task 15: GitHub API routes

**Files:**
- Create: `engine/resumeforge/api/routes/github.py`
- Modify: `engine/resumeforge/api/app.py`

- [ ] **Step 1: Create GitHub routes**

Create `engine/resumeforge/api/routes/github.py`:

```python
"""GitHub integration routes."""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from resumeforge.api.errors import APIError, internal_error
from resumeforge.auth.dependencies import User, get_current_user
from resumeforge.data.base_store import BaseStore
from resumeforge.data.factory import get_store
from resumeforge.data.schema import Project

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/integrations/github", tags=["Integrations"])


class GitHubImportRequest(BaseModel):
    username: str
    sections: list[Literal["pinned", "readme", "stats", "repos"]] = ["pinned"]
    selected_repo_names: list[str] = []


class GitHubImportResult(BaseModel):
    imported_projects: list[Project] = []
    readme_draft: str | None = None
    suggested_languages: list[str] = []
    public_repos_count: int = 0


class GitHubDeployRequest(BaseModel):
    repo: str  # "owner/repo"
    branch: str = "gh-pages"
    template: str = "classic"
    locale: str = "en"


class GitHubDeployResult(BaseModel):
    pages_url: str
    message: str = "Deployed successfully"


def _get_gh_client(meta: object) -> object:
    from resumeforge.integrations.github import GitHubClient
    token = getattr(getattr(meta, "integrations", None), "github_token", None)
    if not token:
        raise APIError(422, "GitHub token not configured. Run: resumeforge config set integrations.github_token $GITHUB_TOKEN", "GITHUB_AUTH_ERROR")
    return GitHubClient(token=token)


@router.post("/import", response_model=GitHubImportResult)
async def github_import(
    body: GitHubImportRequest,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> GitHubImportResult:
    """Import GitHub profile data into resume sections."""
    meta = await db.get_meta(user.id)
    gh = _get_gh_client(meta)

    result = GitHubImportResult()

    if "pinned" in body.sections:
        pinned = await gh.fetch_pinned_repos(body.username)
        result.imported_projects.extend(pinned)

    if "repos" in body.sections:
        repos = await gh.fetch_all_public_repos(body.username, body.selected_repo_names or None)
        result.imported_projects.extend(repos)

    if result.imported_projects:
        projects = await db.get_projects(user.id)
        existing_urls = {p.url for p in projects.projects}
        for proj in result.imported_projects:
            # Upsert by URL
            existing = next((p for p in projects.projects if p.url == proj.url), None)
            if existing:
                idx = projects.projects.index(existing)
                projects.projects[idx] = proj
            elif proj.url not in existing_urls:
                projects.projects.append(proj)
                existing_urls.add(proj.url)
        await db.save_projects(user.id, projects)

    if "readme" in body.sections:
        result.readme_draft = await gh.fetch_readme_summary(body.username)

    if "stats" in body.sections:
        stats = await gh.fetch_contribution_stats(body.username)
        result.suggested_languages = stats.get("top_languages", [])
        result.public_repos_count = stats.get("public_repos", 0)

    return result


@router.post("/pages/deploy", response_model=GitHubDeployResult)
async def github_pages_deploy(
    body: GitHubDeployRequest,
    user: User = Depends(get_current_user),
    db: BaseStore = Depends(get_store),
) -> GitHubDeployResult:
    """Build resume as HTML and push to GitHub Pages."""
    from jinja2 import Environment, FileSystemLoader
    from pathlib import Path as P

    from resumeforge.data.schema import ResumeContext

    meta = await db.get_meta(user.id)
    gh = _get_gh_client(meta)

    # Assemble ResumeContext directly (no sync builder dependency)
    context = ResumeContext(
        profile=await db.get_profile(user.id),
        experience=await db.get_experience(user.id),
        skills=await db.get_skills(user.id),
        education=await db.get_education(user.id),
        projects=await db.get_projects(user.id),
        certifications=await db.get_certifications(user.id),
        meta=meta,
        locale=body.locale,
        template_name=body.template,
        output_format="html",
    )

    # Render HTML via the template's Jinja2 html template
    templates_dir = P(__file__).parent.parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
    tmpl = env.get_template(f"{body.template}/resume.html.j2")
    html_content = tmpl.render(ctx=context)

    try:
        pages_url = gh.deploy_pages(html_content, repo=body.repo, branch=body.branch)
    except RuntimeError as exc:
        raise internal_error(str(exc), "PAGES_DEPLOY_FAILED")

    return GitHubDeployResult(pages_url=pages_url)
```

- [ ] **Step 2: Register github router in app.py**

In `engine/resumeforge/api/app.py`, update the routes import:
```python
from resumeforge.api.routes import analyze, auth, build, config, data, github, jobs, tailor, templates
```

Add after `app.include_router(auth.router)`:
```python
app.include_router(github.router)
```

Add to `openapi_tags`:
```python
{"name": "Integrations", "description": "GitHub import and Pages deploy."},
```

- [ ] **Step 3: Smoke test the routes are reachable**

```bash
cd engine && uv run python -c "
from fastapi.testclient import TestClient
from resumeforge.api.app import app
c = TestClient(app)
# No token needed in local mode
resp = c.post('/api/integrations/github/import', json={'username': 'test', 'sections': ['pinned']})
print(resp.status_code, resp.json().get('code', 'ok'))
"
```

Expected: `422 GITHUB_AUTH_ERROR` (no token configured — correct behaviour).

- [ ] **Step 4: Run full test suite**

```bash
cd engine && uv run pytest tests/ -x
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add engine/resumeforge/api/routes/github.py engine/resumeforge/api/app.py
git commit -m "feat(api): add /api/integrations/github/import and /pages/deploy routes"
```

---

## Group G — CLI GitHub Commands

### Task 16: CLI client + command group

**Files:**
- Create: `cli/client/github.go`
- Create: `cli/cmd/github.go`
- Modify: `cli/cmd/root.go`

- [ ] **Step 1: Create cli/client/github.go**

```go
package client

import (
	"bytes"
	"encoding/json"
	"fmt"
)

// GitHubImportRequest matches POST /api/integrations/github/import
type GitHubImportRequest struct {
	Username          string   `json:"username"`
	Sections          []string `json:"sections"`
	SelectedRepoNames []string `json:"selected_repo_names"`
}

// GitHubImportResult matches the engine response
type GitHubImportResult struct {
	ImportedProjects  []map[string]interface{} `json:"imported_projects"`
	ReadmeDraft       *string                  `json:"readme_draft"`
	SuggestedLanguages []string                `json:"suggested_languages"`
	PublicReposCount  int                      `json:"public_repos_count"`
}

// GitHubDeployRequest matches POST /api/integrations/github/pages/deploy
type GitHubDeployRequest struct {
	Repo     string `json:"repo"`
	Branch   string `json:"branch"`
	Template string `json:"template"`
	Locale   string `json:"locale"`
}

// GitHubDeployResult matches the engine response
type GitHubDeployResult struct {
	PagesURL string `json:"pages_url"`
	Message  string `json:"message"`
}

// GitHubImport calls the engine GitHub import endpoint.
func (c *Client) GitHubImport(req GitHubImportRequest) (*GitHubImportResult, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}
	resp, err := c.post("/api/integrations/github/import", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	var result GitHubImportResult
	if err := json.Unmarshal(resp, &result); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}
	return &result, nil
}

// GitHubDeployPages calls the engine GitHub Pages deploy endpoint.
func (c *Client) GitHubDeployPages(req GitHubDeployRequest) (*GitHubDeployResult, error) {
	body, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}
	resp, err := c.post("/api/integrations/github/pages/deploy", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	var result GitHubDeployResult
	if err := json.Unmarshal(resp, &result); err != nil {
		return nil, fmt.Errorf("decode response: %w", err)
	}
	return &result, nil
}
```

- [ ] **Step 2: Create cli/cmd/github.go**

```go
package cmd

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"

	"resumeforge/client"
)

var githubCmd = &cobra.Command{
	Use:   "github",
	Short: "GitHub integration — import profile data and deploy to GitHub Pages",
}

var githubImportCmd = &cobra.Command{
	Use:   "import",
	Short: "Import GitHub profile data into resume sections",
	RunE: func(cmd *cobra.Command, args []string) error {
		username, _ := cmd.Flags().GetString("username")
		if username == "" {
			return fmt.Errorf("--username is required")
		}
		sectionsStr, _ := cmd.Flags().GetString("sections")
		sections := strings.Split(sectionsStr, ",")

		c, err := client.NewClient()
		if err != nil {
			return err
		}
		if err := c.EnsureEngine(); err != nil {
			return err
		}

		req := client.GitHubImportRequest{
			Username: username,
			Sections: sections,
		}
		result, err := c.GitHubImport(req)
		if err != nil {
			return fmt.Errorf("import failed: %w", err)
		}

		fmt.Printf("Imported %d projects\n", len(result.ImportedProjects))
		if result.ReadmeDraft != nil {
			fmt.Printf("README draft available (%d chars) — review in web UI\n", len(*result.ReadmeDraft))
		}
		if len(result.SuggestedLanguages) > 0 {
			fmt.Printf("Suggested languages: %s\n", strings.Join(result.SuggestedLanguages, ", "))
		}
		return nil
	},
}

var githubDeployCmd = &cobra.Command{
	Use:   "deploy",
	Short: "Deploy resume to GitHub Pages",
	RunE: func(cmd *cobra.Command, args []string) error {
		pages, _ := cmd.Flags().GetBool("pages")
		if !pages {
			return fmt.Errorf("--pages flag is required (only GitHub Pages deploy is supported)")
		}
		repo, _ := cmd.Flags().GetString("repo")
		if repo == "" {
			return fmt.Errorf("--repo is required (format: owner/repo)")
		}
		template, _ := cmd.Flags().GetString("template")
		locale, _ := cmd.Flags().GetString("locale")

		c, err := client.NewClient()
		if err != nil {
			return err
		}
		if err := c.EnsureEngine(); err != nil {
			return err
		}

		req := client.GitHubDeployRequest{
			Repo:     repo,
			Branch:   "gh-pages",
			Template: template,
			Locale:   locale,
		}
		result, err := c.GitHubDeployPages(req)
		if err != nil {
			return fmt.Errorf("deploy failed: %w", err)
		}

		fmt.Printf("Deployed! %s\n", result.PagesURL)
		return nil
	},
}

func init() {
	githubImportCmd.Flags().String("username", "", "GitHub username to import from (required)")
	githubImportCmd.Flags().String("sections", "pinned", "Comma-separated sections: pinned,readme,stats,repos")

	githubDeployCmd.Flags().Bool("pages", false, "Deploy to GitHub Pages (required)")
	githubDeployCmd.Flags().String("repo", "", "Target repository in owner/repo format (required)")
	githubDeployCmd.Flags().String("template", "classic", "Resume template to use")
	githubDeployCmd.Flags().String("locale", "en", "Output locale")

	githubCmd.AddCommand(githubImportCmd)
	githubCmd.AddCommand(githubDeployCmd)
}
```

- [ ] **Step 3: Register in root.go**

In `cli/cmd/root.go`, find the `init()` function (or wherever other commands are registered) and add:

```go
rootCmd.AddCommand(githubCmd)
```

- [ ] **Step 4: Build and verify**

```bash
cd cli && go build ./... 2>&1
```

Expected: no errors.

```bash
cd cli && ./resumeforge github --help
```

Expected:
```
GitHub integration — import profile data and deploy to GitHub Pages

Usage:
  resumeforge github [command]

Available Commands:
  deploy      Deploy resume to GitHub Pages
  import      Import GitHub profile data into resume sections
```

- [ ] **Step 5: Run CLI tests**

```bash
cd cli && go test ./...
```

Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add cli/client/github.go cli/cmd/github.go cli/cmd/root.go
git commit -m "feat(cli): add github command group — import and deploy pages"
```

---

## Final QA

### Task 17: Full test suite + mypy + ruff

- [ ] **Step 1: Engine — full test suite**

```bash
cd engine && uv run pytest tests/ -v
```

Expected: all tests pass (243 original + new auth/json_store/github tests).

- [ ] **Step 2: mypy strict check**

```bash
cd engine && uv run mypy resumeforge/
```

Expected: no errors.

- [ ] **Step 3: ruff lint**

```bash
cd engine && uv run ruff check . && uv run ruff format --check .
```

Expected: no issues.

- [ ] **Step 4: CLI build and test**

```bash
cd cli && go build ./... && go test ./... && go vet ./...
```

Expected: all pass.

- [ ] **Step 5: Community Edition smoke test (no env vars)**

```bash
cd engine && uv run uvicorn resumeforge.api.app:app --port 8080 &
sleep 2
curl -s http://localhost:8080/health | python3 -m json.tool
curl -s http://localhost:8080/api/data/profile | python3 -m json.tool
kill %1
```

Expected: `{"status": "ok"}` and valid profile JSON with no auth errors.

- [ ] **Step 6: Update ROADMAP.md — mark Phase 7a items complete**

In `ROADMAP.md`, update Phase 7 section:
```markdown
## Phase 7 — Cloud Edition Foundation 🔄

- [x] JWT authentication layer
- [x] PostgreSQL backend (replaces JSON files)
- [ ] Plugin system interface
- [ ] DB Connector plugin
- [ ] RAG Connector plugin
- [x] Multi-user isolation
- [x] GitHub integration (built-in): import + Pages deploy
```

- [ ] **Step 7: Final commit**

```bash
git add ROADMAP.md
git commit -m "docs: update ROADMAP — Phase 7a complete (auth, PostgreSQL, multi-user, GitHub integration)"
```
