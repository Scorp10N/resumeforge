"""Resume tailor — adapts resume content to a specific job description."""

from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from resumeforge.ai.provider import AIProvider
from resumeforge.data.schema import JobDescription, ResumeContext

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _render_prompt(template_name: str, **kwargs: object) -> str:
    env = Environment(loader=FileSystemLoader(str(_PROMPTS_DIR)), autoescape=False)
    tmpl = env.get_template(template_name)
    return tmpl.render(**kwargs)


class ResumeTailor:
    """AI-powered resume tailoring against a job description."""

    def __init__(self, provider: AIProvider) -> None:
        self.provider = provider

    def generate_summary(self, context: ResumeContext, job: JobDescription) -> str:
        """Generate a tailored professional summary for the job. Returns existing if AI off."""
        if not self.provider.enabled:
            return context.profile.summary

        prompt = _render_prompt(
            "tailor_to_job.j2",
            profile=context.profile,
            experience=context.experience,
            skills=context.skills,
            job_title=job.title,
            job_company=job.company,
            job_description=job.description,
            requirements=job.requirements,
        )
        result = self.provider.complete(prompt, max_tokens=400)
        return result.strip() if result else context.profile.summary

    def suggest_keywords(self, context: ResumeContext, job: JobDescription) -> list[str]:
        """Return keywords from the JD not found in the resume (gaps)."""
        resume_text = _flatten_resume(context).lower()
        missing = []
        for req in job.requirements + job.nice_to_have:
            if req.lower() not in resume_text:
                missing.append(req)
        return missing


def _flatten_resume(context: ResumeContext) -> str:
    """Combine all resume text for keyword matching."""
    parts: list[str] = [
        context.profile.summary,
        context.profile.title,
    ]
    for pos in context.experience.positions:
        parts.append(pos.title)
        parts.append(pos.company)
        parts.extend(b.text for b in pos.bullets)
    for cat in context.skills.categories:
        parts.extend(cat.items)
    for proj in context.projects.projects:
        parts.append(proj.description)
        parts.extend(proj.technologies)
    return " ".join(parts)
