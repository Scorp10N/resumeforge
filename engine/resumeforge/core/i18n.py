"""Internationalization utilities for ResumeForge.

Provides translation functions and locale-aware date formatting
using Babel. Falls back gracefully when a locale is not supported.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

_LOCALES_DIR = Path(__file__).parent.parent / "locales"
_FALLBACK_LOCALE = "en"


def get_translator(locale: str) -> Callable[[str], str]:
    """Return a gettext translation function for the given locale.

    Returns an identity function (passthrough) if the locale is not found,
    so templates always work even with missing catalogs.

    Args:
        locale: BCP-47 locale code, e.g. "en", "he", "ar".

    Returns:
        A callable that translates a message ID to the locale string.
    """
    try:
        import gettext as _gettext

        translation = _gettext.translation(
            domain="messages",
            localedir=str(_LOCALES_DIR),
            languages=[locale, _FALLBACK_LOCALE],
        )
        return translation.gettext
    except Exception:
        logger.debug("No translation catalog for locale %r — using identity", locale)
        return lambda s: s


def format_date(date_str: str | None, locale: str) -> str:
    """Format a YYYY-MM or YYYY-MM-DD date string for the given locale.

    Examples:
        format_date("2025-03", "en") → "March 2025"
        format_date("2025-03", "he") → "מרץ 2025"
        format_date(None, "en") → ""

    Args:
        date_str: ISO date string (YYYY-MM or YYYY-MM-DD), or None.
        locale: BCP-47 locale code.

    Returns:
        Human-readable date string, or empty string if input is None/invalid.
    """
    if not date_str:
        return ""
    try:
        from datetime import date

        from babel.dates import format_date as babel_format_date

        parts = date_str.split("-")
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        d = date(year, month, day)
        # "MMMM yyyy" → "March 2025" / "מרץ 2025"
        return babel_format_date(d, format="MMMM yyyy", locale=locale)
    except Exception:
        logger.debug("Date formatting failed for %r locale %r", date_str, locale)
        return date_str
