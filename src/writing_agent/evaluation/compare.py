"""Baseline summary comparison."""

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class RegressionFlag(BaseModel):
    """One baseline regression finding."""

    metric: str
    severity: Literal["warning", "fail"]
    message: str
    base_value: float | int
    candidate_value: float | int


class BaselineComparisonResult(BaseModel):
    """Comparison between two baseline summaries."""

    base_path: str
    candidate_path: str
    base: dict[str, Any]
    candidate: dict[str, Any]
    delta_rule_score: float
    delta_citation_valid_rate: float
    delta_insufficient_evidence_count: float
    delta_high_severity_findings: float = 0.0
    delta_run_duration_seconds: float = 0.0
    regression_flags: list[RegressionFlag] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    status: Literal["pass", "warning", "fail"] = "pass"


def load_baseline_summary(path: Path | str) -> dict[str, Any]:
    """Load a baseline_summary.json file."""

    return json.loads(Path(path).read_text(encoding="utf-8"))


def _relative_drop(base: float, candidate: float) -> float:
    if base == 0:
        return 0.0 if candidate >= base else 1.0
    return (base - candidate) / base


def _relative_increase(base: float, candidate: float) -> float:
    if base == 0:
        return 1.0 if candidate > 0 else 0.0
    return (candidate - base) / base


def compare_baseline_summaries(
    base_path: Path | str,
    candidate_path: Path | str,
) -> BaselineComparisonResult:
    """Compare two baseline summaries and flag regressions."""

    base = load_baseline_summary(base_path)
    candidate = load_baseline_summary(candidate_path)
    base_rule = float(base.get("average_rule_score", 0.0) or 0.0)
    candidate_rule = float(candidate.get("average_rule_score", 0.0) or 0.0)
    base_citation = float(base.get("average_citation_valid_rate", 0.0) or 0.0)
    candidate_citation = float(candidate.get("average_citation_valid_rate", 0.0) or 0.0)
    base_insufficient = float(base.get("average_insufficient_evidence_count", 0.0) or 0.0)
    candidate_insufficient = float(
        candidate.get("average_insufficient_evidence_count", 0.0) or 0.0
    )
    base_high = float(base.get("average_high_severity_findings", 0.0) or 0.0)
    candidate_high = float(candidate.get("average_high_severity_findings", 0.0) or 0.0)
    base_duration = float(base.get("average_run_duration_seconds", 0.0) or 0.0)
    candidate_duration = float(candidate.get("average_run_duration_seconds", 0.0) or 0.0)
    flags: list[RegressionFlag] = []
    improvements: list[str] = []
    if _relative_drop(base_rule, candidate_rule) > 0.05:
        flags.append(
            RegressionFlag(
                metric="average_rule_score",
                severity="warning",
                message="Average rule score dropped by more than 5%.",
                base_value=base_rule,
                candidate_value=candidate_rule,
            )
        )
    if _relative_drop(base_citation, candidate_citation) > 0.03:
        flags.append(
            RegressionFlag(
                metric="average_citation_valid_rate",
                severity="warning",
                message="Citation valid rate dropped by more than 3%.",
                base_value=base_citation,
                candidate_value=candidate_citation,
            )
        )
    if _relative_increase(base_insufficient, candidate_insufficient) > 0.20:
        flags.append(
            RegressionFlag(
                metric="average_insufficient_evidence_count",
                severity="warning",
                message="Insufficient-evidence count rose by more than 20%.",
                base_value=base_insufficient,
                candidate_value=candidate_insufficient,
            )
        )
    base_failed = int(base.get("failed_count", 0) or 0)
    candidate_failed = int(candidate.get("failed_count", 0) or 0)
    if candidate_failed > base_failed:
        flags.append(
            RegressionFlag(
                metric="failed_count",
                severity="fail",
                message="Failed task count increased.",
                base_value=base_failed,
                candidate_value=candidate_failed,
            )
        )
    if (
        base.get("mode") == "single"
        and candidate.get("mode") == "multi"
        and base_duration > 0
        and candidate_duration > base_duration * 3
        and candidate_rule - base_rule < 0.03
    ):
        flags.append(
            RegressionFlag(
                metric="average_run_duration_seconds",
                severity="warning",
                message=(
                    "Multi-agent run is more than 3x slower without at least "
                    "3% rule-score improvement."
                ),
                base_value=base_duration,
                candidate_value=candidate_duration,
            )
        )
    if candidate_citation > base_citation:
        improvements.append("citation_valid_rate improved")
    if candidate_high < base_high:
        improvements.append("high_severity_findings decreased")

    status: Literal["pass", "warning", "fail"] = "pass"
    if any(flag.severity == "fail" for flag in flags):
        status = "fail"
    elif flags:
        status = "warning"
    return BaselineComparisonResult(
        base_path=str(base_path),
        candidate_path=str(candidate_path),
        base=base,
        candidate=candidate,
        delta_rule_score=candidate_rule - base_rule,
        delta_citation_valid_rate=candidate_citation - base_citation,
        delta_insufficient_evidence_count=candidate_insufficient - base_insufficient,
        delta_high_severity_findings=candidate_high - base_high,
        delta_run_duration_seconds=candidate_duration - base_duration,
        regression_flags=flags,
        improvements=improvements,
        status=status,
    )


def render_baseline_comparison(result: BaselineComparisonResult) -> dict[str, Any]:
    """Return a compact JSON-serializable comparison view."""

    return {
        "status": result.status,
        "base": {
            "commit_hash": result.base.get("commit_hash", ""),
            "model_name": result.base.get("model_name", ""),
            "embedding_model": result.base.get("embedding_model", ""),
            "mode": result.base.get("mode", "single"),
            "max_agent_rounds": result.base.get("max_agent_rounds", 0),
            "rag_mode": result.base.get("rag_mode", ""),
            "collection": result.base.get("collection", ""),
            "task_count": result.base.get("task_count", 0),
            "success_count": result.base.get("success_count", 0),
            "failed_count": result.base.get("failed_count", 0),
        },
        "candidate": {
            "commit_hash": result.candidate.get("commit_hash", ""),
            "model_name": result.candidate.get("model_name", ""),
            "embedding_model": result.candidate.get("embedding_model", ""),
            "mode": result.candidate.get("mode", "single"),
            "max_agent_rounds": result.candidate.get("max_agent_rounds", 0),
            "rag_mode": result.candidate.get("rag_mode", ""),
            "collection": result.candidate.get("collection", ""),
            "task_count": result.candidate.get("task_count", 0),
            "success_count": result.candidate.get("success_count", 0),
            "failed_count": result.candidate.get("failed_count", 0),
        },
        "delta_rule_score": result.delta_rule_score,
        "delta_citation_valid_rate": result.delta_citation_valid_rate,
        "delta_insufficient_evidence_count": result.delta_insufficient_evidence_count,
        "delta_high_severity_findings": result.delta_high_severity_findings,
        "delta_run_duration_seconds": result.delta_run_duration_seconds,
        "regression_flags": [flag.model_dump(mode="json") for flag in result.regression_flags],
        "improvements": result.improvements,
    }
