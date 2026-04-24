"""Security regression tests — T007 zip-slip, T008 path traversal, T009 allowlist, T010 SSRF."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from resumeforge.api.app import _parse_cors_origins, app
from resumeforge.data import store


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# T007-A — import endpoint must reject paths outside OUTPUT_DIR
# ---------------------------------------------------------------------------

def test_import_rejects_path_outside_output_dir(client: TestClient) -> None:
    r = client.post("/api/data/import?archive_path=/etc/passwd")
    assert r.status_code in (400, 422), (
        f"Expected 400/422 for path outside OUTPUT_DIR, got {r.status_code}: {r.text}"
    )


# ---------------------------------------------------------------------------
# T007-B — zip-slip: entries with ../ must be skipped, not written
# ---------------------------------------------------------------------------

def test_import_skips_zip_slip_entry(tmp_path: Path) -> None:
    """A zip entry with path traversal must be silently skipped."""
    from resumeforge.data.store import import_backup  # noqa: PLC0415

    evil_zip = tmp_path / "evil.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("data/../../../tmp/pwned_resumeforge.json", '{"pwned": true}')
    evil_zip.write_bytes(buf.getvalue())

    restored = import_backup(evil_zip)

    assert restored == [], f"Zip-slip entry must be skipped, got: {restored}"
    assert not Path("/tmp/pwned_resumeforge.json").exists(), "Zip-slip must not write outside DATA_DIR"


# ---------------------------------------------------------------------------
# T008 — template preview must reject path traversal in name
# ---------------------------------------------------------------------------

def test_template_preview_rejects_encoded_traversal(client: TestClient) -> None:
    r = client.get("/api/templates/..%2F..%2Fetc%2Fpasswd/preview")
    assert r.status_code in (400, 404), (
        f"Expected 400/404 for URL-encoded traversal, got {r.status_code}: {r.text}"
    )


def test_template_preview_rejects_dotdot_name(client: TestClient) -> None:
    r = client.get("/api/templates/../../../etc/passwd/preview")
    assert r.status_code in (400, 404), (
        f"Expected 400/404 for ../ template name, got {r.status_code}: {r.text}"
    )


# ---------------------------------------------------------------------------
# T010 — AIConfig.base_url must reject SSRF vectors
# ---------------------------------------------------------------------------

def test_aiconfig_rejects_private_ip() -> None:
    from pydantic import ValidationError  # noqa: PLC0415

    from resumeforge.data.schema import AIConfig  # noqa: PLC0415

    with pytest.raises(ValidationError, match="private IP"):
        AIConfig(base_url="http://192.168.1.1/v1")


def test_aiconfig_rejects_file_scheme() -> None:
    from pydantic import ValidationError  # noqa: PLC0415

    from resumeforge.data.schema import AIConfig  # noqa: PLC0415

    with pytest.raises(ValidationError, match="http or https"):
        AIConfig(base_url="file:///etc/passwd")


def test_aiconfig_allows_localhost() -> None:
    from resumeforge.data.schema import AIConfig  # noqa: PLC0415

    cfg = AIConfig(base_url="http://localhost:11434")  # Ollama / LM Studio
    assert cfg.base_url == "http://localhost:11434"


# ---------------------------------------------------------------------------
# T011 — CORS_ORIGINS env var parsing
# ---------------------------------------------------------------------------
class TestCORSOriginsConfig:
    """T011: _parse_cors_origins correctly handles whitespace and wildcard."""

    def test_normal_origin_is_added(self) -> None:
        origins = _parse_cors_origins("http://api.example.com:3000")
        assert "http://api.example.com:3000" in origins

    def test_multiple_origins(self) -> None:
        origins = _parse_cors_origins("http://a.com,http://b.com")
        assert origins == ["http://a.com", "http://b.com"]

    def test_whitespace_is_stripped(self) -> None:
        origins = _parse_cors_origins(" http://example.com:3000 , http://app.local ")
        assert "http://example.com:3000" in origins
        assert "http://app.local" in origins
        assert not any(o != o.strip() for o in origins)

    def test_empty_string_produces_no_extras(self) -> None:
        origins = _parse_cors_origins("")
        assert origins == []

    def test_wildcard_raises(self) -> None:
        with pytest.raises(RuntimeError, match=r"\*"):
            _parse_cors_origins("*")

    def test_wildcard_mixed_raises(self) -> None:
        with pytest.raises(RuntimeError, match=r"\*"):
            _parse_cors_origins("http://ok.com,*")


# ---------------------------------------------------------------------------
# T012 — lifespan initialises data directory
# ---------------------------------------------------------------------------
def test_lifespan_calls_init_data_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """T012: Startup lifespan must create data and output directories."""
    monkeypatch.setattr(store, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(store, "JOBS_DIR", tmp_path / "data" / "jobs")
    monkeypatch.setattr(store, "OUTPUT_DIR", tmp_path / "output")

    with TestClient(app):
        assert (tmp_path / "data").is_dir(), "DATA_DIR not created by lifespan"
        assert (tmp_path / "output").is_dir(), "OUTPUT_DIR not created by lifespan"
