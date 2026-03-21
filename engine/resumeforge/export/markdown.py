"""Markdown exporter — renders resume to Markdown via Jinja2 template."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from resumeforge.core.i18n import format_date as _format_date
from resumeforge.core.i18n import get_translator
from resumeforge.data.schema import ResumeContext
from resumeforge.export.base import BaseExporter, ExportError

logger = logging.getLogger(__name__)


class MarkdownExporter(BaseExporter):
    @property
    def format_name(self) -> str:
        return "md"

    def export(
        self,
        context: ResumeContext,
        template_dir: Path,
        output_path: Path,
    ) -> Path:
        output_path = self._resolve_output(output_path)

        tmpl_file = template_dir / "resume.md.j2"
        if not tmpl_file.exists():
            raise ExportError(f"Template file not found: {tmpl_file}")

        try:
            env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=False,
                trim_blocks=True,
                lstrip_blocks=True,
            )
            translator = get_translator(context.locale)
            env.globals["_"] = translator
            env.globals["format_date"] = _format_date
            tmpl = env.get_template("resume.md.j2")
            rendered = tmpl.render(
                profile=context.profile,
                experience=context.experience,
                skills=context.skills,
                education=context.education,
                projects=context.projects,
                certifications=context.certifications,
                meta=context.meta,
                job=context.job,
                locale=context.locale,
            )
            output_path.write_text(rendered, encoding="utf-8")
            logger.info("Markdown export → %s", output_path)
            return output_path
        except Exception as exc:
            raise ExportError(f"Markdown export failed: {exc}") from exc
