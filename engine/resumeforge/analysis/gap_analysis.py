"""Gap analysis — identifies required skills from a job description missing from the resume."""

from __future__ import annotations

import re
from typing import Any

from resumeforge.analysis.base import AnalysisResult, BaseAnalyzer, Finding, Severity
from resumeforge.data.schema import JobDescription, ResumeContext


class GapAnalyzer(BaseAnalyzer):
    """Identifies required and nice-to-have skills from a JD that are absent from the resume."""

    @property
    def name(self) -> str:
        return "gap_analysis"

    def analyze(self, context: ResumeContext, **kwargs: Any) -> AnalysisResult:
        job: JobDescription | None = kwargs.get("job") or context.job

        if job is None:
            return AnalysisResult(
                analyzer=self.name,
                score=1.0,
                label="N/A — no job description provided",
                findings=[
                    Finding(
                        message="Provide a job description to run gap analysis.",
                        severity=Severity.INFO,
                    )
                ],
            )

        resume_text = _flatten_resume(context).lower()

        critical_gaps: list[str] = []
        nice_gaps: list[str] = []

        for skill in job.requirements:
            if not _skill_present(skill, resume_text):
                critical_gaps.append(skill)

        for skill in job.nice_to_have:
            if not _skill_present(skill, resume_text):
                nice_gaps.append(skill)

        total_required = len(job.requirements)
        covered_required = total_required - len(critical_gaps)
        score = covered_required / total_required if total_required else 1.0

        findings: list[Finding] = []

        for skill in critical_gaps:
            findings.append(
                Finding(
                    message=f'Required skill "{skill}" not found in resume.',
                    severity=Severity.ERROR,
                    suggestion=(
                        f'Add "{skill}" to your skills or demonstrate it in a bullet point.'
                    ),
                )
            )

        for skill in nice_gaps:
            findings.append(
                Finding(
                    message=f'Nice-to-have skill "{skill}" not found in resume.',
                    severity=Severity.WARNING,
                    suggestion=(
                        f'Consider adding "{skill}" if you have relevant experience.'
                    ),
                )
            )

        return AnalysisResult(
            analyzer=self.name,
            score=score,
            findings=findings,
            metadata={
                "critical_gaps": critical_gaps,
                "nice_to_have_gaps": nice_gaps,
                "required_covered": covered_required,
                "required_total": total_required,
            },
        )


def _skill_present(skill: str, resume_text: str) -> bool:
    """Return True if the skill appears as a word/phrase in the resume text."""
    pattern = re.compile(r"\b" + re.escape(skill.lower()) + r"\b")
    return bool(pattern.search(resume_text))


def _flatten_resume(context: ResumeContext) -> str:
    """Flatten all resume text into a single string for matching."""
    parts: list[str] = [context.profile.summary, context.profile.title]
    for pos in context.experience.positions:
        parts += [pos.title, pos.company]
        parts += [b.text for b in pos.bullets]
    for cat in context.skills.categories:
        parts += cat.items
    for item in context.skills.exploring:
        parts += item.items
    for proj in context.projects.projects:
        parts += [proj.name, proj.description]
        parts += proj.technologies
        parts += [b.text for b in proj.bullets]
    for cert in context.certifications.certifications:
        parts += [cert.name, cert.issuer]
    return " ".join(filter(None, parts))
