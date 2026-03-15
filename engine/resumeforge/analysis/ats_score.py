"""ATS keyword score analyzer."""

from __future__ import annotations

import re
from typing import Any

from resumeforge.analysis.base import AnalysisResult, BaseAnalyzer, Finding, Severity
from resumeforge.data.schema import JobDescription, ResumeContext


class ATSScoreAnalyzer(BaseAnalyzer):
    """Measures how many JD keywords appear in the resume."""

    @property
    def name(self) -> str:
        return "ats_score"

    def analyze(self, context: ResumeContext, **kwargs: Any) -> AnalysisResult:
        job: JobDescription | None = kwargs.get("job") or context.job

        if job is None:
            return AnalysisResult(
                analyzer=self.name,
                score=0.0,
                label="N/A — no job description provided",
                findings=[Finding(message="Provide a job description to calculate ATS score.", severity=Severity.INFO)],
            )

        all_keywords = list(dict.fromkeys(job.requirements + job.nice_to_have))
        if not all_keywords:
            return AnalysisResult(analyzer=self.name, score=1.0, label="100% (no keywords defined)")

        resume_text = _flatten(context).lower()
        found: list[str] = []
        missing: list[str] = []

        for kw in all_keywords:
            pattern = re.compile(r"\b" + re.escape(kw.lower()) + r"\b")
            if pattern.search(resume_text):
                found.append(kw)
            else:
                missing.append(kw)

        score = len(found) / len(all_keywords)
        findings: list[Finding] = []

        for kw in missing:
            sev = Severity.ERROR if kw in job.requirements else Severity.WARNING
            findings.append(
                Finding(
                    message=f'Keyword "{kw}" not found in resume.',
                    severity=sev,
                    suggestion=f'Consider adding "{kw}" where genuinely applicable.',
                )
            )

        return AnalysisResult(
            analyzer=self.name,
            score=score,
            findings=findings,
            metadata={"found": found, "missing": missing, "total": len(all_keywords)},
        )


def _flatten(context: ResumeContext) -> str:
    parts: list[str] = [context.profile.summary, context.profile.title]
    for pos in context.experience.positions:
        parts += [pos.title, pos.company] + [b.text for b in pos.bullets]
    for cat in context.skills.categories:
        parts += cat.items
    for proj in context.projects.projects:
        parts += [proj.description] + proj.technologies
    for cert in context.certifications.certifications:
        parts.append(cert.name)
    return " ".join(filter(None, parts))
