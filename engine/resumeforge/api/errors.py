"""Structured error helpers for the API."""

from __future__ import annotations

from fastapi import HTTPException


class APIError(HTTPException):
    """HTTPException with an explicit error code."""

    def __init__(self, status_code: int, detail: str, code: str) -> None:
        super().__init__(
            status_code=status_code,
            detail={"detail": detail, "code": code},
        )


def not_found(resource: str, identifier: str) -> APIError:
    return APIError(
        status_code=404,
        detail=f"{resource} '{identifier}' not found.",
        code="NOT_FOUND",
    )


def bad_request(detail: str, code: str = "BAD_REQUEST") -> APIError:
    return APIError(status_code=400, detail=detail, code=code)


def internal_error(detail: str, code: str = "INTERNAL_ERROR") -> APIError:
    return APIError(status_code=500, detail=detail, code=code)
