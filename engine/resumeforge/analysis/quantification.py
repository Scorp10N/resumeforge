"""Quantification analyzer — checks how many bullets contain metrics."""

from __future__ import annotations

import re
from typing import Any

from resumeforge.analysis.base import AnalysisResult, BaseAnalyzer, Finding, Severity
from resumeforge.data.schema import ResumeContext

# Patterns indicating quantified impact
_METRIC_RE = re.compile(
    r"""
    (?:
        \d+[%xX]                          # percentages or multipliers
      | \$[\d\.,]+[KkMmBb]?              # dollar amounts
      | \d[\d\.,]*\s*(?:
            million|billion|thousand     # spelled-out numbers
          | [KkMmBb]                     # abbreviated
          | employees?|users?|clients?   # headcount
          | hours?|days?|weeks?|months?  # time savings
          | projects?|systems?|services? # deliverables
        )
      | \b(?:zero|doubled|tripled|halved)\b  # qualitative-quantitative
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

_TARGET_RATE = 0.60  # we want ≥60% of bullets to have metrics


class QuantificationAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "quantification"

    def analyze(self, context: ResumeContext, **kwargs: Any) -> AnalysisResult:

        all_bullets: list[str] = []
        for pos in context.experience.positions:
            all_bullets.extend(b.text for b in pos.bullets)
        for proj in context.projects.projects:
            all_bullets.extend(b.text for b in proj.bullets)

        if not all_bullets:
            return AnalysisResult(
                analyzer=self.name,
                score=0.0,
                label="No bullets found",
                findings=[Finding(message="No experience bullets found.", severity=Severity.WARNING)],
            )

        quantified = [b for b in all_bullets if _METRIC_RE.search(b)]
        unquantified = [b for b in all_bullets if not _METRIC_RE.search(b)]
        rate = len(quantified) / len(all_bullets)
        score = min(rate / _TARGET_RATE, 1.0)

        findings: list[Finding] = []
        for b in unquantified[:5]:  # surface top 5 weak bullets
            findings.append(
                Finding(
                    message=f'Bullet lacks measurable impact: "{b[:80]}..."' if len(b) > 80 else f'Bullet lacks measurable impact: "{b}"',
                    severity=Severity.WARNING,
                    suggestion="Add a metric: % improvement, $ saved, # users affected, time reduced, etc.",
                )
            )

        return AnalysisResult(
            analyzer=self.name,
            score=score,
            findings=findings,
            metadata={
                "total_bullets": len(all_bullets),
                "quantified": len(quantified),
                "rate": round(rate, 2),
            },
        )
