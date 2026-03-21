"""Shared pytest fixtures for integration tests.

The engine_server fixture starts a real uvicorn instance on port 8089
for the duration of the test session. Tests that need it can either
use it via autouse or request it explicitly.
"""
from __future__ import annotations

import threading
import time

import httpx
import pytest
import uvicorn


ENGINE_URL = "http://127.0.0.1:8089"
_STARTUP_TIMEOUT_S = 10.0


@pytest.fixture(scope="session", autouse=True)
def engine_server() -> str:
    """Start the ResumeForge engine on port 8089 for the test session.

    Yields the base URL. Shuts down cleanly when the session ends.
    Using port 8089 avoids conflicts with a running dev server on 8080.
    """
    config = uvicorn.Config(
        "resumeforge.api.app:app",
        host="127.0.0.1",
        port=8089,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait for the server to accept connections
    deadline = time.time() + _STARTUP_TIMEOUT_S
    while time.time() < deadline:
        try:
            httpx.get(f"{ENGINE_URL}/api/templates", timeout=1.0)
            break
        except Exception:
            time.sleep(0.2)
    else:
        raise RuntimeError(f"Engine did not start within {_STARTUP_TIMEOUT_S}s")

    yield ENGINE_URL

    server.should_exit = True
    thread.join(timeout=5)
