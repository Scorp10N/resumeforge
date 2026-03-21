"""Analysis report — aggregates all analyzer results into a unified markdown report."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from resumeforge.analysis.ats_score import ATSScoreAnalyzer
from resumeforge.analysis.base import AnalysisResult, Severity
from resumeforge.analysis.gap_analysis import GapAnalyzer
from resumeforge.analysis.grammar import GrammarAnalyzer
from resumeforge.analysis.quantification import QuantificationAnalyzer
from resumeforge.analysis.readability import ReadabilityAnalyzer
from resumeforge.data.schema import AIConfig, ResumeContext


class AnalysisReport(BaseModel):
    generated_at: str
    overall_score: float
    overall_label: str
    results: list[AnalysisResult]
    total_findings: int
    critical_findings: int

    def to_markdown(self) -> str:
        lines: list[str] = [
            "# ResumeForge Analysis Report",
            f"Generated: {self.generated_at}",
            "",
            f"## Overall Score: {self.overall_label}",
            "",
        ]
        for result in self.results:
            lines.append(f"### {result.analyzer.replace('_', ' ').title()} — {result.label}")
            if result.findings:
                for f in result.findings:
                    icon = {"info": "ℹ️", "warning": "⚠️", "error": "❌"}.get(
                        f.severity.value, "•"
                    )
                    lines.append(f"- {icon} {f.message}")
                    if f.suggestion:
                        lines.append(f"  *Suggestion: {f.suggestion}*")
            else:
                lines.append("- ✅ No issues found.")
            lines.append("")

        lines.append(
            f"---\n*Total findings: {self.total_findings} "
            f"({self.critical_findings} critical)*"
        )
        return "\n".join(lines)


def run_all_analyzers(
    context: ResumeContext,
    ai_config: AIConfig | None = None,
) -> AnalysisReport:
    """Run all 5 analyzers and return an aggregated report.

    Args:
        context: The fully assembled resume context.
        ai_config: Optional AI configuration. When provided and enabled,
                   the grammar analyzer will use AI. Pass None for offline-only.
    """
    from resumeforge.ai.provider import AIProvider

    ai_provider: AIProvider | None = None
    if ai_config is not None:
        ai_provider = AIProvider(ai_config)

    analyzers: list[Any] = [
        ReadabilityAnalyzer(),
        QuantificationAnalyzer(),
        ATSScoreAnalyzer(),
        GapAnalyzer(),
        GrammarAnalyzer(ai_provider=ai_provider),
    ]

    kwargs: dict[str, Any] = {"job": context.job}
    results: list[AnalysisResult] = [a.analyze(context, **kwargs) for a in analyzers]

    # Weights: ATS and Gap doubled when a job is provided
    has_job = context.job is not None
    weights = [1.0, 1.0, 2.0 if has_job else 0.0, 2.0 if has_job else 0.0, 1.0]
    total_weight = sum(weights)
    if total_weight:
        overall = sum(r.score * w for r, w in zip(results, weights, strict=False)) / total_weight
    else:
        overall = sum(r.score for r in results) / len(results) if results else 0.0

    total_findings = sum(len(r.findings) for r in results)
    critical = sum(
        1
        for r in results
        for f in r.findings
        if f.severity == Severity.ERROR
    )

    return AnalysisReport(
        generated_at=datetime.now().isoformat(timespec="seconds"),
        overall_score=round(overall, 3),
        overall_label=f"{int(overall * 100)}%",
        results=results,
        total_findings=total_findings,
        critical_findings=critical,
    )


# Backwards-compatible alias used by existing tests
def run_analysis(context: ResumeContext) -> AnalysisReport:
    """Run analysis without AI (offline mode). Alias for run_all_analyzers."""
    return run_all_analyzers(context, ai_config=None)
