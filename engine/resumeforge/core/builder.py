"""Core resume builder — assembles ResumeContext from data sections."""

from __future__ import annotations

from resumeforge.data import store
from resumeforge.data.schema import ResumeContext


class ResumeBuilder:
    """Assembles a ResumeContext from stored data sections."""

    def build(
        self,
        *,
        template_name: str | None = None,
        output_format: str | None = None,
        job_slug: str | None = None,
        locale: str | None = None,
    ) -> ResumeContext:
        """Load all data sections and build a complete ResumeContext.

        Args:
            template_name: Override default template from meta.json.
            output_format: Override default format from meta.json.
            job_slug: Job slug to load for tailoring / ATS analysis.
            locale: Override default locale from meta.json.

        Returns:
            Fully assembled ResumeContext ready for export.
        """
        meta = store.get_meta()

        return ResumeContext(
            profile=store.get_profile(),
            experience=store.get_experience(),
            skills=store.get_skills(),
            education=store.get_education(),
            projects=store.get_projects(),
            certifications=store.get_certifications(),
            meta=meta,
            job=store.get_job(job_slug) if job_slug else None,
            locale=locale or meta.default_locale,
            template_name=template_name or meta.default_template,
            output_format=output_format or meta.default_format,
        )
