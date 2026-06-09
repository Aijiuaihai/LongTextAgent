"""Agent-level metrics for multi-agent workflow observability."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> str:
    """Return an ISO UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


class AgentMetric(BaseModel):
    """One agent metric data point."""

    agent_name: str
    metric_name: str
    value: float
    unit: str = "count"
    tags: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class AgentMetricsSummary(BaseModel):
    """Aggregated per-agent metrics for one thread."""

    thread_id: str
    mode: str = "multi"
    total_agents_run: int = 0
    total_duration_seconds: float = 0.0
    total_errors: int = 0
    total_warnings: int = 0
    researcher: dict[str, float] = Field(default_factory=dict)
    planner: dict[str, float] = Field(default_factory=dict)
    writer: dict[str, float] = Field(default_factory=dict)
    citation_auditor: dict[str, float] = Field(default_factory=dict)
    reviewer: dict[str, float] = Field(default_factory=dict)
    editor: dict[str, float] = Field(default_factory=dict)
    formatter: dict[str, float] = Field(default_factory=dict)
    evaluator: dict[str, float] = Field(default_factory=dict)
    supervisor: dict[str, float] = Field(default_factory=dict)


def _dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_dump(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _dump(item) for key, item in value.items()}
    return value


def _metric_dict(value: Any) -> dict[str, Any]:
    dumped = _dump(value)
    return dumped if isinstance(dumped, dict) else {}


def _metric_list(value: Any) -> list[Any]:
    dumped = _dump(value)
    return dumped if isinstance(dumped, list) else []


def _severity_count(findings: list[Any], severity: str) -> int:
    return sum(1 for finding in findings if _metric_dict(finding).get("severity") == severity)


def summarize_agent_metrics(thread_id: str, state: dict[str, Any]) -> AgentMetricsSummary:
    """Build an AgentMetricsSummary from workflow state or thread metadata."""

    if "agent_metrics" in state and isinstance(state["agent_metrics"], dict):
        return AgentMetricsSummary.model_validate(state["agent_metrics"])

    agent_results = [_metric_dict(item) for item in _metric_list(state.get("agent_results", []))]
    evidence_packs = [_metric_dict(item) for item in _metric_list(state.get("evidence_packs", []))]
    section_drafts = [_metric_dict(item) for item in _metric_list(state.get("section_drafts", []))]
    if state.get("edited_drafts"):
        section_drafts = [_metric_dict(item) for item in _metric_list(state.get("edited_drafts"))]
    citation_audits = [
        _metric_dict(item) for item in _metric_list(state.get("citation_audits", []))
    ]
    review_findings = [
        _metric_dict(item) for item in _metric_list(state.get("review_findings", []))
    ]
    supervisor_decisions = [
        _metric_dict(item) for item in _metric_list(state.get("supervisor_decisions", []))
    ]
    output_paths = _metric_dict(state.get("output_paths", {}))
    plan = _metric_dict(state.get("plan", {}))
    sections = plan.get("sections", []) if isinstance(plan.get("sections"), list) else []
    evaluation = _metric_dict(state.get("evaluation_result", {}))
    rule_metrics = _metric_dict(evaluation.get("rule_metrics", {}))
    citation_verification = _metric_dict(evaluation.get("citation_verification", {}))

    retrieved_scores = [
        float(result.get("score", 0) or 0)
        for pack in evidence_packs
        for result in pack.get("results", [])
        if isinstance(result, dict)
    ]
    total_citations = sum(len(draft.get("citations", []) or []) for draft in section_drafts)
    invalid_citations = sum(
        int(audit.get("invalid_citations", 0) or 0) for audit in citation_audits
    )
    fallback_count = sum(
        1
        for result in agent_results
        for warning in result.get("warnings", []) or []
        if "fallback" in str(warning).lower()
    )

    return AgentMetricsSummary(
        thread_id=thread_id,
        mode=str(state.get("mode", "multi")),
        total_agents_run=len(agent_results),
        total_duration_seconds=sum(
            float(item.get("duration_seconds", 0) or 0) for item in agent_results
        ),
        total_errors=sum(len(item.get("errors", []) or []) for item in agent_results),
        total_warnings=sum(len(item.get("warnings", []) or []) for item in agent_results),
        researcher={
            "retrieved_chunks": float(
                sum(len(pack.get("results", []) or []) for pack in evidence_packs)
            ),
            "average_retrieval_score": (
                sum(retrieved_scores) / len(retrieved_scores) if retrieved_scores else 0.0
            ),
            "insufficient_evidence_sections": float(
                sum(1 for pack in evidence_packs if pack.get("insufficient_evidence"))
            ),
        },
        planner={
            "planned_sections": float(len(sections)),
            "estimated_total_words": float(
                sum(int(section.get("estimated_words", 0) or 0) for section in sections)
            ),
        },
        writer={
            "generated_sections": float(len(section_drafts)),
            "total_citations": float(total_citations),
            "insufficient_evidence_count": float(
                sum(1 for draft in section_drafts if draft.get("insufficient_evidence"))
            ),
        },
        citation_auditor={
            "valid_citations": float(
                sum(int(audit.get("valid_citations", 0) or 0) for audit in citation_audits)
            ),
            "invalid_citations": float(invalid_citations),
            "repaired_citations": float(
                sum(int(audit.get("repaired_citations", 0) or 0) for audit in citation_audits)
            ),
            "downgraded_citations": float(
                sum(int(audit.get("downgraded_citations", 0) or 0) for audit in citation_audits)
            ),
        },
        reviewer={
            "high_severity_findings": float(_severity_count(review_findings, "high")),
            "medium_severity_findings": float(_severity_count(review_findings, "medium")),
            "low_severity_findings": float(_severity_count(review_findings, "low")),
        },
        editor={
            "edited_sections": float(len(_metric_list(state.get("edited_drafts", [])))),
            "unresolved_findings": float(len(review_findings)),
        },
        formatter={
            "output_file_count": float(len(output_paths) or (1 if state.get("output_path") else 0)),
            "markdown_exported": float(
                "markdown" in output_paths or str(state.get("output_path", "")).endswith(".md")
            ),
            "docx_exported": float("docx" in output_paths),
        },
        evaluator={
            "rule_score": float(rule_metrics.get("overall_score", 0) or 0),
            "citation_valid_rate": float(
                (
                    citation_verification.get("valid_citations", 0)
                    / citation_verification.get("total_citations", 1)
                )
                if citation_verification.get("total_citations", 0)
                else 0
            ),
            "repetition_ratio": float(rule_metrics.get("repeated_paragraph_ratio", 0) or 0),
        },
        supervisor={
            "rounds_used": float(state.get("current_round", 0) or 0),
            "supervisor_decisions": float(len(supervisor_decisions)),
            "fallback_count": float(fallback_count),
        },
    )
