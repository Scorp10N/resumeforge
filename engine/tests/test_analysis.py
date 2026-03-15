"""Tests for the analysis engine."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from resumeforge.analysis.ats_score import ATSScoreAnalyzer
from resumeforge.analysis.gap_analysis import GapAnalyzer
from resumeforge.analysis.grammar import GrammarAnalyzer
from resumeforge.analysis.quantification import QuantificationAnalyzer
from resumeforge.analysis.readability import ReadabilityAnalyzer
from resumeforge.analysis.report import run_all_analyzers, run_analysis
from resumeforge.data.schema import (
    Bullet,
    Certifications,
    Education,
    Experience,
    JobDescription,
    Meta,
    Position,
    Profile,
    Project,
    Projects,
    ResumeContext,
    SkillCategory,
    Skills,
)


# ---------------------------------------------------------------------------
# Shared test fixture factory
# ---------------------------------------------------------------------------

def _make_context(
    summary: str = "Experienced security engineer.",
    bullets: list[str] | None = None,
    skills: list[str] | None = None,
    job: JobDescription | None = None,
    projects: list[Project] | None = None,
) -> ResumeContext:
    if bullets is None:
        bullets = ["Designed and deployed cloud security architecture.", "Reduced incidents by 40%."]
    if skills is None:
        skills = ["AWS", "Python", "Azure"]
    return ResumeContext(
        profile=Profile(name="Test", title="Engineer", summary=summary),
        experience=Experience(positions=[
            Position(
                company="Corp",
                title="Security Engineer",
                start_date="2022-01",
                is_current=True,
                bullets=[Bullet(text=b) for b in bullets],
            )
        ]),
        skills=Skills(categories=[SkillCategory(label="Cloud", items=skills)]),
        education=Education(),
        projects=Projects(projects=projects or []),
        certifications=Certifications(),
        meta=Meta(),
        job=job,
    )


# ---------------------------------------------------------------------------
# ATSScoreAnalyzer
# ---------------------------------------------------------------------------

class TestATSScoreAnalyzer:
    def test_no_job(self) -> None:
        ctx = _make_context()
        result = ATSScoreAnalyzer().analyze(ctx)
        assert result.label.startswith("N/A")
        assert result.score == 0.0

    def test_all_keywords_found(self) -> None:
        job = JobDescription(
            slug="j", title="Dev", company="X", description="...",
            requirements=["AWS", "Python"],
        )
        ctx = _make_context(skills=["AWS", "Python"], job=job)
        result = ATSScoreAnalyzer().analyze(ctx, job=job)
        assert result.score == 1.0

    def test_partial_match(self) -> None:
        job = JobDescription(
            slug="j", title="Dev", company="X", description="...",
            requirements=["AWS", "Python", "Kubernetes"],
        )
        ctx = _make_context(skills=["AWS", "Python"], job=job)
        result = ATSScoreAnalyzer().analyze(ctx, job=job)
        assert 0 < result.score < 1.0
        assert "Kubernetes" in result.metadata["missing"]

    def test_no_keywords_defined(self) -> None:
        job = JobDescription(slug="j", title="Dev", company="X", description="...", requirements=[])
        ctx = _make_context(job=job)
        result = ATSScoreAnalyzer().analyze(ctx, job=job)
        assert result.score == 1.0

    def test_missing_required_is_error_severity(self) -> None:
        job = JobDescription(
            slug="j", title="Dev", company="X", description="...",
            requirements=["Kubernetes"],
            nice_to_have=["Helm"],
        )
        ctx = _make_context(skills=["AWS"], job=job)
        result = ATSScoreAnalyzer().analyze(ctx, job=job)
        severities = {f.message: f.severity.value for f in result.findings}
        assert any("Kubernetes" in msg and sev == "error" for msg, sev in severities.items())
        assert any("Helm" in msg and sev == "warning" for msg, sev in severities.items())


# ---------------------------------------------------------------------------
# QuantificationAnalyzer
# ---------------------------------------------------------------------------

class TestQuantificationAnalyzer:
    def test_quantified_bullets(self) -> None:
        ctx = _make_context(bullets=["Reduced cost by 30%", "Increased revenue by $1M", "Automated 5 systems"])
        result = QuantificationAnalyzer().analyze(ctx)
        assert result.score == 1.0
        assert result.metadata["quantified"] == 3

    def test_no_metrics(self) -> None:
        ctx = _make_context(bullets=["Did some work", "Helped with projects"])
        result = QuantificationAnalyzer().analyze(ctx)
        assert result.score < 1.0
        assert len(result.findings) > 0

    def test_no_bullets(self) -> None:
        ctx = _make_context(bullets=[])
        result = QuantificationAnalyzer().analyze(ctx)
        assert result.score == 0.0

    def test_partial_quantification(self) -> None:
        ctx = _make_context(bullets=["Improved system performance.", "Reduced latency by 50ms."])
        result = QuantificationAnalyzer().analyze(ctx)
        assert result.metadata["quantified"] == 1
        assert result.score < 1.0


# ---------------------------------------------------------------------------
# ReadabilityAnalyzer
# ---------------------------------------------------------------------------

class TestReadabilityAnalyzer:
    def test_good_resume(self) -> None:
        ctx = _make_context(
            summary="Security expert.",
            bullets=["Did X.", "Did Y.", "Did Z."],
        )
        result = ReadabilityAnalyzer().analyze(ctx)
        assert result.score > 0.5

    def test_no_summary(self) -> None:
        ctx = _make_context(summary="")
        result = ReadabilityAnalyzer().analyze(ctx)
        messages = [f.message for f in result.findings]
        assert any("summary" in m.lower() for m in messages)

    def test_too_few_bullets_flagged(self) -> None:
        ctx = _make_context(bullets=["Only one bullet."])
        result = ReadabilityAnalyzer().analyze(ctx)
        messages = [f.message for f in result.findings]
        assert any("bullet" in m.lower() or "1 bullet" in m for m in messages)

    def test_no_skills_is_error(self) -> None:
        ctx = _make_context(skills=[])
        # Skills list is empty — rebuild with no skill categories
        ctx2 = ResumeContext(
            profile=ctx.profile,
            experience=ctx.experience,
            skills=Skills(categories=[]),
            education=ctx.education,
            projects=ctx.projects,
            certifications=ctx.certifications,
            meta=ctx.meta,
        )
        result = ReadabilityAnalyzer().analyze(ctx2)
        assert any(f.severity.value == "error" for f in result.findings)

    def test_long_bullet_flagged(self) -> None:
        long_bullet = "Designed and implemented a highly complex distributed system " \
                      "that involved many microservices and numerous integration points across teams."
        ctx = _make_context(bullets=[long_bullet, "Short bullet.", "Another bullet."])
        result = ReadabilityAnalyzer().analyze(ctx)
        messages = [f.message for f in result.findings]
        assert any("long bullet" in m.lower() for m in messages)


# ---------------------------------------------------------------------------
# GapAnalyzer
# ---------------------------------------------------------------------------

class TestGapAnalyzer:
    def test_no_job(self) -> None:
        ctx = _make_context()
        result = GapAnalyzer().analyze(ctx)
        assert result.score == 1.0
        assert result.label.startswith("N/A")

    def test_all_required_present(self) -> None:
        job = JobDescription(
            slug="j", title="Dev", company="X", description="...",
            requirements=["AWS", "Python"],
        )
        ctx = _make_context(skills=["AWS", "Python"], job=job)
        result = GapAnalyzer().analyze(ctx, job=job)
        assert result.score == 1.0
        assert result.metadata["critical_gaps"] == []

    def test_critical_gaps_detected(self) -> None:
        job = JobDescription(
            slug="j", title="Dev", company="X", description="...",
            requirements=["AWS", "Kubernetes", "Terraform"],
        )
        ctx = _make_context(skills=["AWS"], job=job)
        result = GapAnalyzer().analyze(ctx, job=job)
        assert result.score < 1.0
        gaps = result.metadata["critical_gaps"]
        assert "Kubernetes" in gaps
        assert "Terraform" in gaps
        assert "AWS" not in gaps

    def test_nice_to_have_gaps_are_warnings(self) -> None:
        job = JobDescription(
            slug="j", title="Dev", company="X", description="...",
            requirements=["AWS"],
            nice_to_have=["Helm", "Istio"],
        )
        ctx = _make_context(skills=["AWS"], job=job)
        result = GapAnalyzer().analyze(ctx, job=job)
        warning_msgs = [f.message for f in result.findings if f.severity.value == "warning"]
        assert any("Helm" in m for m in warning_msgs)
        assert any("Istio" in m for m in warning_msgs)

    def test_required_gaps_are_errors(self) -> None:
        job = JobDescription(
            slug="j", title="Dev", company="X", description="...",
            requirements=["Kubernetes"],
        )
        ctx = _make_context(skills=["AWS"], job=job)
        result = GapAnalyzer().analyze(ctx, job=job)
        error_msgs = [f.message for f in result.findings if f.severity.value == "error"]
        assert any("Kubernetes" in m for m in error_msgs)

    def test_no_requirements_defined(self) -> None:
        job = JobDescription(slug="j", title="Dev", company="X", description="...", requirements=[])
        ctx = _make_context(job=job)
        result = GapAnalyzer().analyze(ctx, job=job)
        assert result.score == 1.0


# ---------------------------------------------------------------------------
# GrammarAnalyzer
# ---------------------------------------------------------------------------

class TestGrammarAnalyzer:
    def test_offline_mode_no_provider(self) -> None:
        ctx = _make_context(bullets=["Responsible for managing the team.", "Did some work."])
        result = GrammarAnalyzer(ai_provider=None).analyze(ctx)
        assert isinstance(result.score, float)
        assert 0.0 <= result.score <= 1.0
        assert result.metadata["ai_assisted"] is False

    def test_offline_detects_weak_phrases(self) -> None:
        ctx = _make_context(bullets=["Responsible for deploying services.", "Helped with migrations."])
        result = GrammarAnalyzer(ai_provider=None).analyze(ctx)
        messages = [f.message for f in result.findings]
        assert any("responsible for" in m.lower() or "helped" in m.lower() for m in messages)

    def test_offline_detects_first_person(self) -> None:
        ctx = _make_context(bullets=["I built a CI/CD pipeline.", "Reduced costs by 20%."])
        result = GrammarAnalyzer(ai_provider=None).analyze(ctx)
        messages = [f.message for f in result.findings]
        assert any("first-person" in m.lower() for m in messages)

    def test_disabled_ai_provider_uses_offline_only(self) -> None:
        mock_ai = MagicMock()
        mock_ai.enabled = False
        ctx = _make_context()
        result = GrammarAnalyzer(ai_provider=mock_ai).analyze(ctx)
        mock_ai.complete.assert_not_called()
        assert result.metadata["ai_assisted"] is False

    def test_enabled_ai_provider_is_called(self) -> None:
        mock_ai = MagicMock()
        mock_ai.enabled = True
        mock_ai.complete.return_value = (
            '[{"issue": "Tense inconsistency", "severity": "warning", "suggestion": "Use past tense."}]'
        )
        ctx = _make_context()
        result = GrammarAnalyzer(ai_provider=mock_ai).analyze(ctx)
        mock_ai.complete.assert_called_once()
        assert result.metadata["ai_assisted"] is True
        messages = [f.message for f in result.findings]
        assert any("Tense inconsistency" in m for m in messages)

    def test_ai_returns_empty_string_gracefully(self) -> None:
        mock_ai = MagicMock()
        mock_ai.enabled = True
        mock_ai.complete.return_value = ""
        ctx = _make_context()
        result = GrammarAnalyzer(ai_provider=mock_ai).analyze(ctx)
        assert result.metadata["ai_assisted"] is False

    def test_ai_returns_malformed_json_gracefully(self) -> None:
        mock_ai = MagicMock()
        mock_ai.enabled = True
        mock_ai.complete.return_value = "not json at all"
        ctx = _make_context()
        result = GrammarAnalyzer(ai_provider=mock_ai).analyze(ctx)
        # Should not raise; ai_assisted will be False since no findings parsed
        assert result.metadata["ai_assisted"] is False

    def test_score_degrades_with_findings(self) -> None:
        ctx = _make_context(bullets=[
            "I was responsible for managing the team.",
            "Helped with various tasks.",
        ])
        result = GrammarAnalyzer(ai_provider=None).analyze(ctx)
        assert result.score < 1.0

    def test_clean_resume_scores_high(self) -> None:
        ctx = _make_context(
            summary="Results-driven security engineer with 5 years of experience.",
            bullets=["Deployed cloud security architecture reducing incidents by 40%.",
                     "Automated compliance checks saving 10 hours per week."],
        )
        result = GrammarAnalyzer(ai_provider=None).analyze(ctx)
        assert result.score > 0.5


# ---------------------------------------------------------------------------
# Report / run_all_analyzers
# ---------------------------------------------------------------------------

class TestReport:
    def test_run_analysis_returns_5_results(self) -> None:
        ctx = _make_context(
            bullets=["Reduced cost by 30%", "Led team of 10", "Deployed 3 services"],
        )
        report = run_analysis(ctx)
        assert 0.0 <= report.overall_score <= 1.0
        assert len(report.results) == 5
        assert report.generated_at

    def test_to_markdown(self) -> None:
        ctx = _make_context()
        report = run_analysis(ctx)
        md = report.to_markdown()
        assert "# ResumeForge Analysis Report" in md
        assert "Overall Score" in md

    def test_run_all_analyzers_offline(self) -> None:
        ctx = _make_context(
            bullets=["Reduced cost by 30%", "Led team of 10", "Deployed 3 services"],
        )
        report = run_all_analyzers(ctx, ai_config=None)
        assert len(report.results) == 5
        analyzer_names = [r.analyzer for r in report.results]
        assert "readability" in analyzer_names
        assert "quantification" in analyzer_names
        assert "ats_score" in analyzer_names
        assert "gap_analysis" in analyzer_names
        assert "grammar" in analyzer_names

    def test_run_all_analyzers_with_job(self) -> None:
        job = JobDescription(
            slug="j", title="Dev", company="X", description="...",
            requirements=["AWS", "Python"],
            nice_to_have=["Kubernetes"],
        )
        ctx = _make_context(skills=["AWS", "Python"], job=job)
        report = run_all_analyzers(ctx, ai_config=None)
        assert len(report.results) == 5
        assert 0.0 <= report.overall_score <= 1.0

    def test_markdown_contains_all_analyzer_sections(self) -> None:
        ctx = _make_context()
        report = run_analysis(ctx)
        md = report.to_markdown()
        for name in ("Readability", "Quantification", "Ats Score", "Gap Analysis", "Grammar"):
            assert name in md

    def test_critical_findings_count(self) -> None:
        # Resume with no skills → readability ERROR, gap ERROR if job has requirements
        job = JobDescription(
            slug="j", title="Dev", company="X", description="...",
            requirements=["Kubernetes"],
        )
        ctx = ResumeContext(
            profile=Profile(name="Test", title="Eng", summary=""),
            experience=Experience(positions=[
                Position(company="C", title="T", start_date="2022-01",
                         is_current=True, bullets=[Bullet(text="Did work.")])
            ]),
            skills=Skills(categories=[]),
            education=Education(),
            projects=Projects(),
            certifications=Certifications(),
            meta=Meta(),
            job=job,
        )
        report = run_all_analyzers(ctx, ai_config=None)
        assert report.critical_findings >= 1
