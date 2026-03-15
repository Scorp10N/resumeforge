"""Export base — BaseExporter ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from resumeforge.data.schema import ResumeContext


class ExportError(Exception):
    """Raised when an export operation fails."""


class BaseExporter(ABC):
    """Abstract base class for all resume exporters."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Short name for this format, e.g. 'pdf', 'docx', 'md'."""

    @abstractmethod
    def export(
        self,
        context: ResumeContext,
        template_dir: Path,
        output_path: Path,
    ) -> Path:
        """Render the resume and write it to output_path.

        Args:
            context: Fully assembled ResumeContext.
            template_dir: Path to the selected template directory.
            output_path: Destination file path (without extension — exporter adds it).

        Returns:
            Absolute path to the generated file.

        Raises:
            ExportError: If rendering or writing fails.
        """

    def _resolve_output(self, output_path: Path) -> Path:
        """Ensure output path has the correct extension."""
        ext = f".{self.format_name}"
        if output_path.suffix.lower() != ext:
            output_path = output_path.with_suffix(ext)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        return output_path
