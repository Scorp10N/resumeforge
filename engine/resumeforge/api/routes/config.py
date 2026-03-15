"""Config routes — GET /api/config and PATCH /api/config."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from resumeforge.data import store
from resumeforge.data.schema import Meta

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["Config"])


class MetaPatch(BaseModel):
    """Partial update model for Meta — all fields optional."""

    default_locale: str | None = None
    default_template: str | None = None
    default_format: str | None = None
    engine: dict[str, Any] | None = None
    ai: dict[str, Any] | None = None
    style: dict[str, Any] | None = None


@router.get("", response_model=Meta)
async def get_config() -> Meta:
    """Get the current engine configuration."""
    return store.get_meta()


@router.patch("", response_model=Meta)
async def patch_config(patch: MetaPatch) -> Meta:
    """Partially update the engine configuration."""
    meta = store.get_meta()
    current = meta.model_dump()

    # Apply scalar overrides
    if patch.default_locale is not None:
        current["default_locale"] = patch.default_locale
    if patch.default_template is not None:
        current["default_template"] = patch.default_template
    if patch.default_format is not None:
        current["default_format"] = patch.default_format

    # Apply nested dict merges
    for key, value in [("engine", patch.engine), ("ai", patch.ai), ("style", patch.style)]:
        if value is not None:
            current[key] = {**current.get(key, {}), **value}

    updated = Meta.model_validate(current)
    store.save_meta(updated)
    return updated


@router.put("", response_model=Meta)
async def update_config(meta: Meta) -> Meta:
    """Replace the full engine configuration."""
    store.save_meta(meta)
    return meta
