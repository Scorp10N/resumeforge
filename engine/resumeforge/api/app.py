"""FastAPI application — main entry point for the ResumeForge engine."""

from __future__ import annotations

import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from resumeforge.api.errors import APIError
from resumeforge.api.models import StatusResponse
from resumeforge.api.routes import analyze, build, config, data, jobs, tailor, templates
from resumeforge.data import store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ResumeForge Engine",
    description="Core engine API for the ResumeForge platform.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Health", "description": "Service health and status."},
        {"name": "Build", "description": "Resume building and export."},
        {"name": "Tailor", "description": "AI-powered resume tailoring."},
        {"name": "Analyze", "description": "Resume analysis and scoring."},
        {"name": "Data", "description": "Resume data CRUD operations."},
        {"name": "Templates", "description": "Template management and preview."},
        {"name": "Jobs", "description": "Job description management."},
        {"name": "Config", "description": "Engine configuration."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # SvelteKit prod local / generic
        "http://localhost:4173",   # SvelteKit preview
        "http://localhost:5173",   # SvelteKit dev
        "http://localhost:8080",   # CLI / generic local
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(build.router)
app.include_router(tailor.router)
app.include_router(analyze.router)
app.include_router(data.router)
app.include_router(templates.router)
app.include_router(jobs.router)
app.include_router(config.router)

# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Return structured error responses for all APIError exceptions."""
    detail: object = exc.detail
    if isinstance(detail, dict):
        return JSONResponse(status_code=exc.status_code, content=detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(detail), "code": "ERROR"},
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/", tags=["Health"], response_model=StatusResponse)
async def root() -> StatusResponse:
    """Service root — confirms the engine is running."""
    return StatusResponse(status="ok", version="0.1.0")


@app.get("/health", tags=["Health"], response_model=StatusResponse)
async def health() -> StatusResponse:
    """Health check endpoint."""
    return StatusResponse(status="ok", version="0.1.0")


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@app.on_event("startup")
async def startup() -> None:
    store.init_data_dir()
    logger.info("ResumeForge engine started.")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    meta = store.get_meta()
    uvicorn.run("resumeforge.api.app:app", host="127.0.0.1", port=meta.engine.port, reload=False)


if __name__ == "__main__":
    main()
