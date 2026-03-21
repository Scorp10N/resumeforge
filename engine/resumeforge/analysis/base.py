"""Analysis base — BaseAnalyzer ABC and AnalysisResult model."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from resumeforge.data.schema import ResumeContext


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Finding(BaseModel):
    message: str
    severity: Severity = Severity.INFO
    field: str | None = None  # which section/bullet this applies to
    suggestion: str | None = None


class AnalysisResult(BaseModel):
    analyzer: str
    score: float  # 0.0–1.0
    max_score: float = 1.0
    label: str = ""  # human-readable score label, e.g. "73%"
    findings: list[Finding] = []
    metadata: dict[str, object] = {}

    def model_post_init(self, __context: object) -> None:
        if not self.label:
            pct = int((self.score / self.max_score) * 100) if self.max_score else 0
            self.label = f"{pct}%"


class BaseAnalyzer(ABC):
    """Abstract base class for all resume analyzers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this analyzer, e.g. 'ats_score'."""
        ...

    @abstractmethod
    def analyze(self, context: ResumeContext, **kwargs: Any) -> AnalysisResult:
        """Run the analysis and return a result."""
        ...
