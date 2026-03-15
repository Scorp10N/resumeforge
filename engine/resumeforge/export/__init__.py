"""Export package — all exporters and factory function."""

from __future__ import annotations

from resumeforge.export.base import BaseExporter, ExportError
from resumeforge.export.docx_export import DocxExporter
from resumeforge.export.markdown import MarkdownExporter
from resumeforge.export.pdf import PdfExporter

__all__ = [
    "BaseExporter",
    "ExportError",
    "MarkdownExporter",
    "DocxExporter",
    "PdfExporter",
    "get_exporter",
]

_REGISTRY: dict[str, type[BaseExporter]] = {
    "md": MarkdownExporter,
    "markdown": MarkdownExporter,
    "docx": DocxExporter,
    "pdf": PdfExporter,
}


def get_exporter(format: str) -> BaseExporter:  # noqa: A002
    """Return an exporter instance for the given format name.

    Args:
        format: One of ``"md"``, ``"markdown"``, ``"docx"``, or ``"pdf"``.

    Returns:
        An instantiated :class:`BaseExporter` subclass.

    Raises:
        ValueError: If *format* is not recognised.
    """
    key = format.lower().lstrip(".")
    cls = _REGISTRY.get(key)
    if cls is None:
        supported = ", ".join(sorted(_REGISTRY))
        raise ValueError(
            f"Unknown export format {format!r}. Supported: {supported}"
        )
    return cls()
