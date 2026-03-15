"""Readability analyzer — checks structure, length, and formatting."""

from __future__ import annotations

from typing import Any

from resumeforge.analysis.base import AnalysisResult, BaseAnalyzer, Finding, Severity
from resumeforge.data.schema import Bullet, ResumeContext

_MAX_BULLET_WORDS = 25
_MIN_BULLETS_PER_ROLE = 3
_MAX_BULLETS_PER_ROLE = 7


def _check_bullet_lengths(pos_id: str, bullets: list[Bullet]) -> tuple[int, list[Finding]]:
    """Return (pass_count, findings) for bullet-length checks."""
    pass_count = 0
    findings: list[Finding] = []
    for b in bullets:
        word_count = len(b.text.split())
        if word_count <= _MAX_BULLET_WORDS:
            pass_count += 1
        else:
            findings.append(Finding(
                message=f'Long bullet ({word_count} words): "{b.text[:60]}..."',
                severity=Severity.INFO,
                suggestion=f"Trim to under {_MAX_BULLET_WORDS} words for readability.",
                field=f"experience.{pos_id}.{b.id}",
            ))
    return pass_count, findings


class ReadabilityAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "readability"

    def analyze(self, context: ResumeContext, **kwargs: Any) -> AnalysisResult:
        findings: list[Finding] = []
        check_results: list[bool] = []

        # Check: profile has summary
        if context.profile.summary:
            check_results.append(True)
        else:
            check_results.append(False)
            findings.append(Finding(
                message="No professional summary found.",
                severity=Severity.WARNING,
                suggestion="Add a 2–3 sentence summary targeting your next role.",
            ))

        # Check: experience bullets per role
        for pos in context.experience.positions:
            n = len(pos.bullets)
            if _MIN_BULLETS_PER_ROLE <= n <= _MAX_BULLETS_PER_ROLE:
                check_results.append(True)
            elif n < _MIN_BULLETS_PER_ROLE:
                check_results.append(False)
                findings.append(Finding(
                    message=f'"{pos.title}" at {pos.company} has only {n} bullet(s). Aim for {_MIN_BULLETS_PER_ROLE}–{_MAX_BULLETS_PER_ROLE}.',
                    severity=Severity.WARNING,
                    field=f"experience.{pos.id}",
                ))
            else:
                check_results.append(False)
                findings.append(Finding(
                    message=f'"{pos.title}" at {pos.company} has {n} bullets. Consider trimming to {_MAX_BULLETS_PER_ROLE} max.',
                    severity=Severity.INFO,
                    field=f"experience.{pos.id}",
                ))

            # Check: bullet length
            bullet_passes, bullet_findings = _check_bullet_lengths(pos.id, pos.bullets)
            check_results.extend([True] * bullet_passes)
            check_results.extend([False] * (len(pos.bullets) - bullet_passes))
            findings.extend(bullet_findings)

        # Check: skills present
        if context.skills.categories:
            check_results.append(True)
        else:
            check_results.append(False)
            findings.append(Finding(
                message="No skill categories found.",
                severity=Severity.ERROR,
                suggestion="Add skill categories with at least 5 skills each.",
            ))

        checks = len(check_results)
        passes = sum(1 for r in check_results if r)
        score = passes / checks if checks else 0.0
        return AnalysisResult(
            analyzer=self.name,
            score=score,
            findings=findings,
            metadata={"checks": checks, "passes": passes},
        )
