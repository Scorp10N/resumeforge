"""Cross-component integration tests.

These tests run against a live engine instance (started by conftest.py).
They exercise the full HTTP → engine → response path without mocking.
"""
from __future__ import annotations

import httpx
import pytest

BASE = "http://127.0.0.1:8089"


class TestTemplates:
    def test_list_returns_array(self, engine_server: str) -> None:
        r = httpx.get(f"{BASE}/api/templates")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_classic_template_present(self, engine_server: str) -> None:
        r = httpx.get(f"{BASE}/api/templates")
        names = [t["name"] for t in r.json()]
        assert "classic" in names


class TestBuild:
    def test_build_markdown_succeeds(self, engine_server: str) -> None:
        r = httpx.post(
            f"{BASE}/api/build",
            params={"template": "classic", "format": "md", "analyze": "false"},
            timeout=30.0,
        )
        assert r.status_code == 200
        body = r.json()
        # Response must have an output_path field
        assert "output_path" in body

    def test_build_unsupported_format_returns_error(self, engine_server: str) -> None:
        r = httpx.post(
            f"{BASE}/api/build",
            params={"template": "classic", "format": "xlsx"},
            timeout=10.0,
        )
        assert r.status_code in (400, 422)


class TestAnalysis:
    def test_analyze_returns_report(self, engine_server: str) -> None:
        r = httpx.post(f"{BASE}/api/analyze", json={}, timeout=30.0)
        assert r.status_code == 200
        body = r.json()
        assert "overall_score" in body
        assert "results" in body
        assert isinstance(body["results"], list)

    def test_analyze_score_in_range(self, engine_server: str) -> None:
        r = httpx.post(f"{BASE}/api/analyze", json={}, timeout=30.0)
        body = r.json()
        score = body["overall_score"]
        assert 0.0 <= score <= 1.0


class TestData:
    def test_get_experience_section(self, engine_server: str) -> None:
        r = httpx.get(f"{BASE}/api/data/experience")
        assert r.status_code == 200
        body = r.json()
        assert "positions" in body

    def test_get_skills_section(self, engine_server: str) -> None:
        r = httpx.get(f"{BASE}/api/data/skills")
        assert r.status_code == 200
        body = r.json()
        assert "categories" in body
