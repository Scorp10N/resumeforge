"""Tests for the i18n utilities."""
from __future__ import annotations

from resumeforge.core.i18n import format_date, get_translator


class TestGetTranslator:
    def test_english_passthrough(self) -> None:
        t = get_translator("en")
        assert t("Professional Summary") == "Professional Summary"
        assert t("Experience") == "Experience"

    def test_hebrew_translation(self) -> None:
        t = get_translator("he")
        assert t("Experience") == "ניסיון מקצועי"
        assert t("Education") == "השכלה"

    def test_unknown_locale_fallback(self) -> None:
        t = get_translator("zz")  # fake locale
        # Should not raise; returns identity
        assert t("Professional Summary") == "Professional Summary"


class TestFormatDate:
    def test_english_month_year(self) -> None:
        result = format_date("2025-03", "en")
        assert "March" in result
        assert "2025" in result

    def test_hebrew_month_year(self) -> None:
        result = format_date("2025-03", "he")
        assert "2025" in result
        # Hebrew month name contains Hebrew characters
        assert any("\u0590" <= c <= "\u05FF" for c in result)

    def test_none_returns_empty(self) -> None:
        assert format_date(None, "en") == ""

    def test_invalid_date_returns_original(self) -> None:
        result = format_date("not-a-date", "en")
        assert result == "not-a-date"

    def test_full_date_string(self) -> None:
        result = format_date("2024-06-15", "en")
        assert "June" in result or "2024" in result
