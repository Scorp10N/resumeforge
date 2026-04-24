"""Security regression tests — T007 zip-slip, T008 path traversal, T009 allowlist, T010 SSRF."""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from resumeforge.api.app import app


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
