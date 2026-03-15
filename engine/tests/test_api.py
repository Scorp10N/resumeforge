"""Tests for the FastAPI engine API."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from resumeforge.api.app import app
from resumeforge.data import store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """Test client with isolated data directory."""
    monkeypatch.setattr(store, "DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(store, "JOBS_DIR", tmp_path / "data" / "jobs")
    monkeypatch.setattr(store, "OUTPUT_DIR", tmp_path / "output")
    store.init_data_dir()
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_root(self, client) -> None:
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health(self, client) -> None:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Data — all sections
# ---------------------------------------------------------------------------


class TestDataEndpoints:
    def test_get_profile_empty(self, client) -> None:
        r = client.get("/api/data/profile")
        assert r.status_code == 200
        data = r.json()
        assert "name" in data

    def test_update_profile(self, client) -> None:
        payload = {
            "name": "Test User",
            "email": "y@test.com",
            "title": "Engineer",
            "schema_version": "1.0",
            "languages": ["en"],
        }
        r = client.put("/api/data/profile", json=payload)
        assert r.status_code == 200
        assert r.json()["name"] == "Test User"

    def test_get_experience_empty(self, client) -> None:
        r = client.get("/api/data/experience")
        assert r.status_code == 200
        assert "positions" in r.json()

    def test_update_experience(self, client) -> None:
        payload = {
            "schema_version": "1.0",
            "positions": [
                {
                    "company": "ACME",
                    "title": "Engineer",
                    "start_date": "2022-01",
                    "bullets": [],
                    "tags": [],
                }
            ],
        }
        r = client.put("/api/data/experience", json=payload)
        assert r.status_code == 200
        assert r.json()["positions"][0]["company"] == "ACME"

    def test_get_skills_empty(self, client) -> None:
        r = client.get("/api/data/skills")
        assert r.status_code == 200
        assert "categories" in r.json()

    def test_update_skills(self, client) -> None:
        payload = {
            "schema_version": "1.0",
            "categories": [{"label": "Cloud", "items": ["AWS", "Azure"], "priority": 1}],
            "exploring": [],
        }
        r = client.put("/api/data/skills", json=payload)
        assert r.status_code == 200
        assert r.json()["categories"][0]["label"] == "Cloud"

    def test_get_education_empty(self, client) -> None:
        r = client.get("/api/data/education")
        assert r.status_code == 200
        assert "entries" in r.json()

    def test_update_education(self, client) -> None:
        payload = {
            "schema_version": "1.0",
            "entries": [
                {
                    "institution": "MIT",
                    "degree": "BSc",
                    "field": "CS",
                    "start_date": "2018-09",
                    "end_date": "2022-06",
                }
            ],
        }
        r = client.put("/api/data/education", json=payload)
        assert r.status_code == 200
        assert r.json()["entries"][0]["institution"] == "MIT"

    def test_get_projects_empty(self, client) -> None:
        r = client.get("/api/data/projects")
        assert r.status_code == 200
        assert "projects" in r.json()

    def test_update_projects(self, client) -> None:
        payload = {
            "schema_version": "1.0",
            "projects": [
                {
                    "name": "ResumeForge",
                    "description": "A resume tool",
                    "technologies": ["Python", "FastAPI"],
                }
            ],
        }
        r = client.put("/api/data/projects", json=payload)
        assert r.status_code == 200
        assert r.json()["projects"][0]["name"] == "ResumeForge"

    def test_get_certifications_empty(self, client) -> None:
        r = client.get("/api/data/certifications")
        assert r.status_code == 200
        assert "certifications" in r.json()

    def test_update_certifications(self, client) -> None:
        payload = {
            "schema_version": "1.0",
            "certifications": [
                {
                    "name": "AWS SAA",
                    "issuer": "Amazon",
                    "date": "2023-06",
                }
            ],
        }
        r = client.put("/api/data/certifications", json=payload)
        assert r.status_code == 200
        assert r.json()["certifications"][0]["name"] == "AWS SAA"

    def test_profile_roundtrip(self, client) -> None:
        """PUT then GET should return the same data."""
        payload = {
            "name": "Test User",
            "email": "test@example.com",
            "title": "Dev",
            "schema_version": "1.0",
            "languages": ["en", "he"],
        }
        client.put("/api/data/profile", json=payload)
        r = client.get("/api/data/profile")
        assert r.status_code == 200
        assert r.json()["name"] == "Test User"
        assert r.json()["languages"] == ["en", "he"]


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------

_SAMPLE_JOB = {
    "slug": "test-job",
    "title": "Security Engineer",
    "company": "Bank",
    "description": "Looking for security expert",
    "requirements": ["Python", "AWS"],
    "nice_to_have": [],
    "language": "en",
    "notes": "",
}


class TestJobEndpoints:
    def test_create_and_get_job(self, client) -> None:
        r = client.post("/api/jobs", json=_SAMPLE_JOB)
        assert r.status_code == 200

        r = client.get("/api/jobs/test-job")
        assert r.status_code == 200
        assert r.json()["title"] == "Security Engineer"

    def test_list_jobs_empty(self, client) -> None:
        r = client.get("/api/jobs")
        assert r.status_code == 200
        assert r.json() == []

    def test_list_jobs(self, client) -> None:
        client.post("/api/jobs", json=_SAMPLE_JOB)
        r = client.get("/api/jobs")
        assert r.status_code == 200
        jobs = r.json()
        assert isinstance(jobs, list)
        assert len(jobs) == 1
        assert jobs[0]["slug"] == "test-job"

    def test_delete_job(self, client) -> None:
        job = {
            "slug": "del-job",
            "title": "Dev",
            "company": "Corp",
            "description": "...",
            "requirements": [],
            "nice_to_have": [],
            "language": "en",
            "notes": "",
        }
        client.post("/api/jobs", json=job)
        r = client.delete("/api/jobs/del-job")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "deleted"
        assert body["slug"] == "del-job"

    def test_get_nonexistent_job(self, client) -> None:
        r = client.get("/api/jobs/does-not-exist")
        assert r.status_code == 404
        body = r.json()
        assert "detail" in body
        assert "code" in body

    def test_delete_nonexistent_job(self, client) -> None:
        r = client.delete("/api/jobs/ghost")
        assert r.status_code == 404

    def test_update_job(self, client) -> None:
        client.post("/api/jobs", json=_SAMPLE_JOB)
        updated = {**_SAMPLE_JOB, "title": "Senior Security Engineer"}
        r = client.put("/api/jobs/test-job", json=updated)
        assert r.status_code == 200
        assert r.json()["title"] == "Senior Security Engineer"

    def test_update_nonexistent_job(self, client) -> None:
        r = client.put("/api/jobs/no-such-job", json=_SAMPLE_JOB)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


class TestConfigEndpoint:
    def test_get_config(self, client) -> None:
        r = client.get("/api/config")
        assert r.status_code == 200
        data = r.json()
        assert data["default_template"] == "classic"
        assert data["ai"]["enabled"] is False

    def test_update_config_put(self, client) -> None:
        r = client.get("/api/config")
        config = r.json()
        config["default_template"] = "modern"
        r2 = client.put("/api/config", json=config)
        assert r2.status_code == 200
        assert r2.json()["default_template"] == "modern"

    def test_patch_config(self, client) -> None:
        r = client.patch("/api/config", json={"default_template": "minimal"})
        assert r.status_code == 200
        assert r.json()["default_template"] == "minimal"

    def test_patch_config_nested(self, client) -> None:
        r = client.patch("/api/config", json={"ai": {"enabled": True}})
        assert r.status_code == 200
        # enabled flag updated; other ai fields preserved
        assert r.json()["ai"]["enabled"] is True
        assert "model" in r.json()["ai"]

    def test_patch_config_preserves_other_fields(self, client) -> None:
        r = client.patch("/api/config", json={"default_locale": "he"})
        assert r.status_code == 200
        data = r.json()
        assert data["default_locale"] == "he"
        assert data["default_template"] == "classic"  # unchanged


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


class TestTemplatesEndpoint:
    def test_list_templates(self, client) -> None:
        r = client.get("/api/templates")
        assert r.status_code == 200
        templates = r.json()
        assert isinstance(templates, list)
        names = [t["name"] for t in templates]
        assert "classic" in names

    def test_list_templates_schema(self, client) -> None:
        r = client.get("/api/templates")
        assert r.status_code == 200
        for tmpl in r.json():
            assert "name" in tmpl
            assert "description" in tmpl

    def test_preview_classic(self, client) -> None:
        r = client.get("/api/templates/classic/preview")
        # Should return 200 (either a file or JSON metadata placeholder)
        assert r.status_code == 200

    def test_preview_nonexistent(self, client) -> None:
        r = client.get("/api/templates/does-not-exist/preview")
        assert r.status_code == 404
        body = r.json()
        assert "detail" in body
        assert "code" in body


# ---------------------------------------------------------------------------
# Analyze
# ---------------------------------------------------------------------------


class TestAnalyzeEndpoints:
    def test_analyze_post(self, client) -> None:
        r = client.post("/api/analyze")
        assert r.status_code == 200
        data = r.json()
        assert "overall_score" in data
        assert "overall_label" in data
        assert "results" in data
        assert "generated_at" in data

    def test_analyze_with_job(self, client) -> None:
        """Analyze with a job slug that exists."""
        client.post("/api/jobs", json=_SAMPLE_JOB)
        r = client.post("/api/analyze", json={"job_slug": "test-job"})
        assert r.status_code == 200
        data = r.json()
        assert "overall_score" in data

    def test_analyze_cache_miss(self, client) -> None:
        """GET /api/analyze/{job_slug} returns 404 when not yet run."""
        r = client.get("/api/analyze/not-yet-analyzed")
        assert r.status_code == 404

    def test_analyze_cache_hit(self, client) -> None:
        """POST /api/analyze then GET /api/analyze/{job_slug} should return cached result."""
        client.post("/api/jobs", json=_SAMPLE_JOB)
        client.post("/api/analyze", json={"job_slug": "test-job"})
        r = client.get("/api/analyze/test-job")
        assert r.status_code == 200
        assert "overall_score" in r.json()


# ---------------------------------------------------------------------------
# Tailor
# ---------------------------------------------------------------------------


class TestTailorEndpoints:
    def test_tailor_post(self, client) -> None:
        client.post("/api/jobs", json=_SAMPLE_JOB)
        r = client.post("/api/tailor", json={"job_slug": "test-job", "ai": False})
        assert r.status_code == 200
        data = r.json()
        assert data["job_slug"] == "test-job"
        assert "tailored_summary" in data
        assert "missing_keywords" in data
        assert isinstance(data["missing_keywords"], list)

    def test_tailor_nonexistent_job(self, client) -> None:
        r = client.post("/api/tailor", json={"job_slug": "no-such-job", "ai": False})
        assert r.status_code == 404
        body = r.json()
        assert "detail" in body
        assert "code" in body

    def test_tailor_stream(self, client) -> None:
        """SSE stream should return text/event-stream content type."""
        client.post("/api/jobs", json=_SAMPLE_JOB)
        with client.stream("GET", "/api/tailor/stream", params={"job_slug": "test-job"}) as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
            # Collect all SSE lines
            lines = []
            for line in r.iter_lines():
                lines.append(line)
                if "complete" in line or "error" in line:
                    break
        # Should have received at least one SSE event
        assert any(line.startswith("event:") or line.startswith("data:") for line in lines)

    def test_tailor_stream_missing_slug(self, client) -> None:
        """Stream with no job_slug should emit an error event."""
        with client.stream("GET", "/api/tailor/stream") as r:
            assert r.status_code == 200
            content = b"".join(r.iter_bytes()).decode()
        assert "error" in content


# ---------------------------------------------------------------------------
# Build SSE stream (basic smoke test)
# ---------------------------------------------------------------------------


class TestBuildStream:
    def test_build_stream_content_type(self, client) -> None:
        """GET /api/build/stream returns text/event-stream."""
        with client.stream("GET", "/api/build/stream", params={"format": "md", "analyze": "false"}) as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
            # Read enough to confirm SSE events arrive
            lines = []
            for line in r.iter_lines():
                lines.append(line)
                if "complete" in line or "error" in line:
                    break
        assert len(lines) > 0


# ---------------------------------------------------------------------------
# Data export/import
# ---------------------------------------------------------------------------


class TestDataBackup:
    def test_export_backup(self, client) -> None:
        r = client.get("/api/data/export")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/zip"

    def test_import_nonexistent_archive(self, client) -> None:
        r = client.post("/api/data/import", params={"archive_path": "/nonexistent/path/backup.zip"})
        assert r.status_code == 404
        body = r.json()
        assert "detail" in body
        assert "code" in body
