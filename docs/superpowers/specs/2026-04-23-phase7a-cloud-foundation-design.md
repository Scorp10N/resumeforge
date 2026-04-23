# Phase 7a — Cloud Edition Foundation + GitHub Integration

**Date:** 2026-04-23
**Status:** Approved

## Context

ResumeForge has completed Phases 1–6 (engine, CLI/TUI, web frontend, AI, 4 templates, i18n). Phase 7 is the Cloud Edition, decomposed into sub-phases. Phase 7a is the foundation layer everything else depends on: JWT auth, PostgreSQL backend, multi-user isolation, and built-in GitHub integration (data import + Pages publishing). The broader GitHub automation (webhook auto-build) is a Phase 7b plugin.

**Overarching constraint:** Community Edition must remain completely unchanged — local engine, JSON files, no auth, zero new dependencies for OSS users.

---

## Scope

1. **JWT auth layer** — register/login/refresh, HS256 tokens, FastAPI Depends injection
2. **Storage abstraction** — `BaseStore` ABC, `JsonStore` (existing logic), `PostgresStore` (SQLAlchemy async)
3. **Multi-user isolation** — `user_id` on all PostgreSQL ORM models and store method signatures
4. **GitHub integration (built-in)** — import (pinned repos, README, stats, all public repos) + Pages deploy
5. **New CLI command group** — `resumeforge github import` / `resumeforge github deploy --pages`

Out of scope for 7a: plugin system, DB Connector, RAG Connector, webhook auto-build (all Phase 7b).

---

## Module Structure

### New engine modules

```
engine/resumeforge/
├── auth/
│   ├── __init__.py
│   ├── jwt.py              — issue/verify tokens (python-jose HS256)
│   ├── models.py           — User, UserCreate, UserLogin, Token Pydantic models
│   └── dependencies.py     — get_current_user FastAPI Depends
│
├── data/
│   ├── base_store.py       — BaseStore ABC (all store method signatures + user_id)
│   ├── json_store.py       — existing store.py logic moved here; user_id ignored
│   ├── postgres_store.py   — SQLAlchemy async implementation; filters by user_id
│   ├── orm_models.py       — SQLAlchemy ORM models (user_id UUID on all tables)
│   ├── factory.py          — get_store() returns JsonStore or PostgresStore from config
│   ├── store.py            — MODIFIED: thin re-export of factory.get_store() for compat
│   └── schema.py           — MODIFIED: add User + IntegrationsConfig models
│
└── integrations/
    ├── __init__.py
    └── github.py           — GitHub API client (httpx), import logic, Pages deploy

engine/resumeforge/api/routes/
├── auth.py                 — POST /api/auth/register, /login, /refresh
└── github.py               — POST /api/integrations/github/import, /pages/deploy

engine/
├── alembic.ini
└── alembic/versions/       — DB migration scripts
```

### New CLI files

```
cli/
├── cmd/github.go           — Cobra command group: github import, github deploy
└── client/github.go        — typed HTTP client methods for github endpoints
```

### Modified files

| File | Change |
|------|--------|
| `engine/resumeforge/api/app.py` | Register auth + github routers; add auth middleware (cloud mode only) |
| `engine/resumeforge/api/routes/*.py` | Accept `store: BaseStore = Depends(get_store)` + `user: User = Depends(get_current_user)` on protected routes |
| `engine/resumeforge/data/schema.py` | Add `User` model; add `IntegrationsConfig` (github_token field); add `integrations: IntegrationsConfig` to `Meta` |
| `engine/pyproject.toml` | Add: python-jose[cryptography], passlib[bcrypt], sqlalchemy[asyncio]>=2.0, asyncpg, alembic, httpx |
| `cli/cmd/root.go` | Register github command group |

---

## Auth Layer

**User storage:** PostgreSQL `users` table — managed separately from resume data, not in the JSON store.

```
users:          id UUID PK, email str UNIQUE, hashed_password str, created_at datetime, is_active bool
refresh_tokens: id UUID PK, user_id FK, token_hash str, expires_at datetime, revoked bool
```

**Endpoints (no auth required):**
```
POST /api/auth/register   {email, password}    → Token
POST /api/auth/login      {email, password}    → Token
POST /api/auth/refresh    {refresh_token}      → Token
```

**Token response:**
```json
{"access_token": "...", "refresh_token": "...", "token_type": "bearer", "expires_in": 900}
```

- Access token: 15-min TTL, HS256, payload `{sub: user_id, exp}`
- Refresh token: 7-day TTL, hash stored in DB to enable revocation
- `SECRET_KEY` env var required in cloud mode
- `get_current_user` dependency: decodes token → queries users table → returns User
- **Activation gate:** auth middleware only active when `engine.mode == "cloud"`. Local engine stays unauthenticated.
- **Passwords:** `passlib[bcrypt]` — never store plaintext.

---

## Storage Abstraction

**`BaseStore` ABC** (`engine/resumeforge/data/base_store.py`):

All existing store functions become abstract async methods, each gaining a `user_id: UUID` parameter:

```python
class BaseStore(ABC):
    async def get_profile(self, user_id: UUID) -> Profile: ...
    async def save_profile(self, user_id: UUID, profile: Profile) -> None: ...
    async def get_experience(self, user_id: UUID) -> Experience: ...
    async def save_experience(self, user_id: UUID, experience: Experience) -> None: ...
    async def get_skills(self, user_id: UUID) -> Skills: ...
    async def save_skills(self, user_id: UUID, skills: Skills) -> None: ...
    async def get_education(self, user_id: UUID) -> Education: ...
    async def save_education(self, user_id: UUID, education: Education) -> None: ...
    async def get_projects(self, user_id: UUID) -> Projects: ...
    async def save_projects(self, user_id: UUID, projects: Projects) -> None: ...
    async def get_certifications(self, user_id: UUID) -> Certifications: ...
    async def save_certifications(self, user_id: UUID, certifications: Certifications) -> None: ...
    async def get_meta(self, user_id: UUID) -> Meta: ...
    async def save_meta(self, user_id: UUID, meta: Meta) -> None: ...
    async def list_jobs(self, user_id: UUID) -> list[JobDescription]: ...
    async def get_job(self, user_id: UUID, slug: str) -> JobDescription | None: ...
    async def save_job(self, user_id: UUID, job: JobDescription) -> None: ...
    async def delete_job(self, user_id: UUID, slug: str) -> bool: ...
    async def export_backup(self, user_id: UUID, output_path: Path) -> Path: ...
    async def import_backup(self, user_id: UUID, archive_path: Path) -> list[str]: ...
```

**`JsonStore`:** existing `store.py` logic moved verbatim, made async with `asyncio.to_thread`. `user_id` accepted but ignored — single-user, always reads the same `DATA_DIR`.

**`PostgresStore`:** SQLAlchemy async session. All queries include `WHERE user_id = :user_id`. ORM models in `orm_models.py` — one table per data section plus `users` + `refresh_tokens`.

**`factory.py`:**
```python
def get_store() -> BaseStore:
    if settings.engine_mode == EngineMode.cloud:
        return PostgresStore(settings.database_url)
    return JsonStore(settings.data_dir)
```

Instantiated once at app startup, injected into routes via `Depends(get_store)`. Route logic unchanged — only signatures gain a `store` parameter.

**Alembic** manages PostgreSQL schema migrations. Existing `migrations.py` JSON versioning stays untouched.

---

## Multi-User Isolation

Isolation enforced at the **store layer**, not the route layer:

- `PostgresStore` always includes `WHERE user_id = current_user.id` — impossible to leak another user's data
- `JsonStore` ignores user_id — single-user community edition, behavior unchanged
- `POST /api/auth/register` creates a `users` row and seeds empty data sections for that user_id
- No cross-user operations in Phase 7a (team features deferred)

---

## GitHub Integration

**Token storage:** `Meta.integrations.github_token` — set via `resumeforge config set integrations.github_token $GITHUB_TOKEN`. Stored in `meta.json` / PostgreSQL meta row. Never committed (gitignored, same rule as profile.json and AI keys).

### Import endpoint

```
POST /api/integrations/github/import
Body: {
  username: str,
  sections: list["pinned" | "readme" | "stats" | "repos"],
  selected_repo_names: list[str]   // for "repos" section only
}
```

| Section | GitHub API | Mapped to | Behavior |
|---------|-----------|-----------|----------|
| `pinned` | GraphQL (pinned items require GraphQL) | `Projects` | Upsert by URL — update if exists, insert if new |
| `readme` | REST `/{username}/{username}` repo | `Profile.summary` draft | Returned for review; engine never overwrites existing summary |
| `stats` | REST `/users/{username}` + `/repos` aggregation | `Skills.exploring[]` suggestion | Additive only |
| `repos` | REST `/users/{username}/repos?type=public` | `Projects` (filtered by `selected_repo_names`) | Upsert by URL |

All import operations are **non-destructive**: merge/add only, never delete existing data.

### Pages deploy endpoint

```
POST /api/integrations/github/pages/deploy
Body: { repo: str, branch: str = "gh-pages", template: str, locale: str }
```

**Prerequisite:** `git` must be installed in the engine environment (standard in dev; must be in Docker image for cloud).

Flow:
1. Build resume HTML — reuse WeasyPrint's intermediate HTML step from `PdfExporter`
2. Clone gh-pages branch into temp dir (creates branch if it doesn't exist yet)
3. Write `index.html` + static assets
4. `git commit` + `git push` using `GITHUB_TOKEN` in remote URL for auth
5. Return `{ pages_url: "https://{owner}.github.io/{repo}", commit_sha: "..." }`

### CLI commands

```bash
resumeforge github import --username Scorp10N
resumeforge github import --username Scorp10N --sections pinned,readme
resumeforge github import --username Scorp10N --sections repos   # interactive picker

resumeforge github deploy --pages --repo Scorp10N/resumeforge
resumeforge github deploy --pages --repo Scorp10N/resumeforge --template modern --locale en
```

CLI calls engine endpoints — no direct GitHub API calls from Go. Token flows from env/config through engine.

---

## Error Codes

Following existing `{detail, code}` pattern:

| Code | HTTP | Meaning |
|------|------|---------|
| `UNAUTHORIZED` | 401 | Missing or expired token |
| `FORBIDDEN` | 403 | Valid token, wrong user |
| `EMAIL_TAKEN` | 409 | Register with existing email |
| `INVALID_CREDENTIALS` | 401 | Wrong email/password on login |
| `GITHUB_AUTH_ERROR` | 422 | GitHub token missing or invalid |
| `GITHUB_RATE_LIMITED` | 429 | GitHub API rate limit hit |
| `REPO_NOT_FOUND` | 404 | Pages deploy target repo doesn't exist |
| `PAGES_DEPLOY_FAILED` | 500 | Git push failed |

---

## Testing Strategy

| Area | Approach |
|------|----------|
| Auth flows | pytest fixtures: valid token, expired token, missing token, wrong user |
| JsonStore | Existing `test_data.py` runs against `JsonStore` unchanged |
| PostgresStore | pytest-asyncio + real test DB (`DATABASE_URL` env in CI); no mocks |
| GitHub import | `respx` to mock GitHub API responses; each section tested independently |
| GitHub deploy | Mock `git` subprocess; HTML output tested in isolation |
| Route auth | TestClient with each token state for every protected endpoint |
| Backward compat | All 243 existing tests must pass unchanged in community (JsonStore) mode |

---

## New Dependencies

```toml
# engine/pyproject.toml additions
python-jose = {extras = ["cryptography"], version = ">=3.3.0"}
passlib = {extras = ["bcrypt"], version = ">=1.7.4"}
sqlalchemy = {extras = ["asyncio"], version = ">=2.0"}
asyncpg = ">=0.29.0"
alembic = ">=1.13.0"
httpx = ">=0.27.0"
```

---

## Build Order

```
1. engine-auth-architect      — auth/ module, JWT, User model, register/login/refresh routes
2. engine-store-abstraction   — BaseStore ABC, JsonStore refactor, PostgresStore, ORM models, Alembic
   (1 and 2 can run in parallel)
3. engine-route-update        — Depends(get_store) + Depends(get_current_user) on all routes
4. engine-github-integration  — integrations/github.py + /api/integrations/github/* routes
   (3 and 4 depend on 1+2)
5. cli-github-commands        — cmd/github.go + client/github.go (depends on 4)
6. qa-reviewer-7a             — full test suite + mypy + ruff
```

---

## Verification

```bash
# Engine full suite
cd engine
uv run pytest tests/ -x -v
uv run mypy resumeforge/
uv run ruff check .

# Specific new test modules
uv run pytest tests/test_auth.py -x
uv run pytest tests/test_data.py -x               # JsonStore backward compat
uv run pytest tests/test_postgres_store.py -x
uv run pytest tests/test_github.py -x

# CLI
cd cli && go test ./...

# End-to-end smoke (cloud mode)
DATABASE_URL=postgresql://... SECRET_KEY=... ENGINE_MODE=cloud \
  uv run uvicorn resumeforge.api.app:app --reload
resumeforge github import --username Scorp10N --sections pinned,readme
resumeforge github deploy --pages --repo Scorp10N/resumeforge

# Community Edition regression (must work unchanged with no env vars)
uv run uvicorn resumeforge.api.app:app --reload
resumeforge build --template classic --format md
```
