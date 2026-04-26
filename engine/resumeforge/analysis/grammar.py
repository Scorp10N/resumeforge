"""Grammar analyzer — AI-assisted language quality check with full offline fallback."""

from __future__ import annotations

import re
from typing import Any

from resumeforge.analysis.base import AnalysisResult, BaseAnalyzer, Finding, Severity
from resumeforge.data.schema import ResumeContext

# ---------------------------------------------------------------------------
# Offline checks
# ---------------------------------------------------------------------------

# Weak filler phrases that add no value
_WEAK_PHRASES: list[str] = [
    r"\bresponsible for\b",
    r"\bhelped (with|to)\b",
    r"\bworked on\b",
    r"\bassisted (with|in)\b",
    r"\bvarious\b",
    r"\bseveral\b",
    r"\bmany\b",
    r"\bsome\b",
    r"\bstuff\b",
    r"\bthings\b",
]

# First-person pronouns (resumes should be written in third-person implied)
_FIRST_PERSON_RE = re.compile(r"\b(I|me|my|myself|we|our|us)\b", re.IGNORECASE)

# Passive voice indicators (simplified heuristic)
_PASSIVE_RE = re.compile(
    r"\b(was|were|been|is|are|be)\s+(being\s+)?\w+ed\b",
    re.IGNORECASE,
)

# Sentences that don't start with a strong action verb (past tense -ed or present -s/-ing)
_ACTION_VERB_START_RE = re.compile(r"^[A-Z][a-z]+(?:ed|d|s|ing)\b")

_WEAK_PHRASE_RES = [re.compile(p, re.IGNORECASE) for p in _WEAK_PHRASES]

# AI system prompt
_GRAMMAR_SYSTEM = (
    "You are a professional resume editor. "
    "Analyse the provided resume text for grammar errors, spelling mistakes, "
    "inconsistent tense, weak phrasing, and language quality issues. "
    "Return a JSON array of objects with keys: "
    '"issue" (string), "severity" ("error"|"warning"|"info"), '
    '"suggestion" (string). '
    "Return ONLY the JSON array, no prose."
)


class GrammarAnalyzer(BaseAnalyzer):
    """Checks language quality. Uses AI when enabled, falls back to offline heuristics."""

    def __init__(self, ai_provider: object | None = None) -> None:
        # Accept an injected AIProvider; if None, offline-only mode is used.
        self._ai = ai_provider

    @property
    def name(self) -> str:
        return "grammar"

    def analyze(self, context: ResumeContext, **kwargs: Any) -> AnalysisResult:
        findings: list[Finding] = []

        # Always run offline heuristics
        offline_findings = _offline_checks(context)
        findings.extend(offline_findings)

        # Attempt AI-assisted checks only if a provider is injected and enabled
        ai_findings = _ai_checks(context, self._ai)
        findings.extend(ai_findings)

        # Score: start at 1.0, deduct per severity
        deduction = sum(
            0.15
            if f.severity == Severity.ERROR
            else 0.07
            if f.severity == Severity.WARNING
            else 0.02
            for f in findings
        )
        score = max(0.0, 1.0 - deduction)

        ai_used = bool(ai_findings)
        return AnalysisResult(
            analyzer=self.name,
            score=round(score, 3),
            findings=findings,
            metadata={"ai_assisted": ai_used, "offline_issues": len(offline_findings)},
        )


# ---------------------------------------------------------------------------
# Offline heuristic helpers
# ---------------------------------------------------------------------------


def _offline_checks(context: ResumeContext) -> list[Finding]:
    findings: list[Finding] = []

    bullets: list[tuple[str, str]] = []  # (bullet_text, field_hint)
    for pos in context.experience.positions:
        for b in pos.bullets:
            bullets.append((b.text, f"experience.{pos.id}.{b.id}"))
    for proj in context.projects.projects:
        for b in proj.bullets:
            bullets.append((b.text, f"projects.{proj.id}.{b.id}"))

    for text, field in bullets:
        # First-person pronouns
        match = _FIRST_PERSON_RE.search(text)
        if match:
            findings.append(
                Finding(
                    message=f'First-person pronoun "{match.group()}" in bullet: "{text[:60]}"',
                    severity=Severity.WARNING,
                    field=field,
                    suggestion="Rewrite without first-person pronouns (e.g. 'Designed...' not 'I designed...').",
                )
            )

        # Weak phrases
        for pattern in _WEAK_PHRASE_RES:
            weak = pattern.search(text)
            if weak:
                findings.append(
                    Finding(
                        message=f'Weak phrase "{weak.group()}" in bullet: "{text[:60]}"',
                        severity=Severity.WARNING,
                        field=field,
                        suggestion="Replace with a strong action verb and specific outcome.",
                    )
                )
                break  # one warning per bullet is enough

        # Passive voice
        passive = _PASSIVE_RE.search(text)
        if passive:
            findings.append(
                Finding(
                    message=f'Possible passive voice in bullet: "{text[:60]}"',
                    severity=Severity.INFO,
                    field=field,
                    suggestion="Prefer active voice: start with a strong past-tense action verb.",
                )
            )

    # Check summary for first-person
    if context.profile.summary:
        match = _FIRST_PERSON_RE.search(context.profile.summary)
        if match:
            findings.append(
                Finding(
                    message=f'First-person pronoun "{match.group()}" in summary.',
                    severity=Severity.WARNING,
                    field="profile.summary",
                    suggestion="Write the summary in third-person implied (no 'I', 'my', etc.).",
                )
            )

    return findings


def _ai_checks(context: ResumeContext, ai_provider: object | None) -> list[Finding]:
    """Return AI-generated findings, or [] if AI is unavailable/disabled."""
    if ai_provider is None:
        return []

    # Validate the provider has .enabled and .complete
    if not (hasattr(ai_provider, "enabled") and hasattr(ai_provider, "complete")):
        return []

    if not ai_provider.enabled:
        return []

    # Build a compact resume text for the AI to inspect
    lines: list[str] = []
    if context.profile.summary:
        lines.append(f"Summary: {context.profile.summary}")
    for pos in context.experience.positions:
        lines.append(f"\n{pos.title} at {pos.company}:")
        for b in pos.bullets:
            lines.append(f"  - {b.text}")
    resume_text = "\n".join(lines)

    raw = ai_provider.complete(
        prompt=f"Review this resume text for language quality:\n\n{resume_text}",
        system=_GRAMMAR_SYSTEM,
        temperature=0.2,
        max_tokens=1000,
    )

    return _parse_ai_response(raw)


def _parse_ai_response(raw: str) -> list[Finding]:
    """Parse the JSON array returned by the AI into Finding objects."""
    import json

    if not raw.strip():
        return []

    # Extract JSON array from the response (AI may wrap it in markdown)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []

    try:
        items: list[dict[str, str]] = json.loads(match.group())
    except (json.JSONDecodeError, ValueError):
        return []

    findings: list[Finding] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        issue = str(item.get("issue", "")).strip()
        suggestion = str(item.get("suggestion", "")).strip()
        sev_raw = str(item.get("severity", "info")).strip().lower()
        if sev_raw == "error":
            sev = Severity.ERROR
        elif sev_raw == "warning":
            sev = Severity.WARNING
        else:
            sev = Severity.INFO

        if issue:
            findings.append(
                Finding(
                    message=issue,
                    severity=sev,
                    suggestion=suggestion or None,
                )
            )

    return findings
