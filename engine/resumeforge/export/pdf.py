"""PDF exporter — renders resume to PDF via Jinja2 HTML template + WeasyPrint."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from resumeforge.data.schema import ResumeContext
from resumeforge.export.base import BaseExporter, ExportError

logger = logging.getLogger(__name__)

_RTL_LOCALES = {"he", "ar", "fa", "ur"}


class PdfExporter(BaseExporter):
    @property
    def format_name(self) -> str:
        return "pdf"

    def export(
        self,
        context: ResumeContext,
        template_dir: Path,
        output_path: Path,
    ) -> Path:
        output_path = self._resolve_output(output_path)

        tmpl_file = template_dir / "resume.html.j2"
        if not tmpl_file.exists():
            raise ExportError(f"HTML template not found: {tmpl_file}")

        try:
            from weasyprint import HTML
        except ImportError as exc:
            raise ExportError(
                "weasyprint is not installed. Run: uv add weasyprint"
            ) from exc

        try:
            env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )
            tmpl = env.get_template("resume.html.j2")
            is_rtl = context.locale in _RTL_LOCALES
            rendered_html = tmpl.render(
                profile=context.profile,
                experience=context.experience,
                skills=context.skills,
                education=context.education,
                projects=context.projects,
                certifications=context.certifications,
                meta=context.meta,
                job=context.job,
                locale=context.locale,
                is_rtl=is_rtl,
            )

            HTML(string=rendered_html, base_url=str(template_dir)).write_pdf(
                str(output_path)
            )
            logger.info("PDF export → %s", output_path)
            return output_path

        except ExportError:
            raise
        except Exception as exc:
            raise ExportError(f"PDF export failed: {exc}") from exc
