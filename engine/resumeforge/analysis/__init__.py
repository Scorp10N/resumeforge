"""Analysis package — exports all analyzers and the run_all_analyzers entry point."""

from __future__ import annotations

from resumeforge.analysis.ats_score import ATSScoreAnalyzer
from resumeforge.analysis.base import AnalysisResult, BaseAnalyzer, Finding, Severity
from resumeforge.analysis.gap_analysis import GapAnalyzer
from resumeforge.analysis.grammar import GrammarAnalyzer
from resumeforge.analysis.quantification import QuantificationAnalyzer
from resumeforge.analysis.readability import ReadabilityAnalyzer
from resumeforge.analysis.report import AnalysisReport, run_all_analyzers, run_analysis

__all__ = [
    # Base types
    "BaseAnalyzer",
    "AnalysisResult",
    "Finding",
    "Severity",
    # Analyzers
    "ATSScoreAnalyzer",
    "GapAnalyzer",
    "GrammarAnalyzer",
    "QuantificationAnalyzer",
    "ReadabilityAnalyzer",
    # Report
    "AnalysisReport",
    "run_all_analyzers",
    "run_analysis",
]
