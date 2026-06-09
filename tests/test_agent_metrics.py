from writing_agent.agents.metrics import summarize_agent_metrics


def test_summarize_agent_metrics_counts_agent_outputs() -> None:
    summary = summarize_agent_metrics(
        "thread-1",
        {
            "mode": "multi",
            "agent_results": [
                {
                    "agent_name": "writer",
                    "status": "success",
                    "warnings": ["fallback output used"],
                    "errors": ["bad json"],
                    "duration_seconds": 1.5,
                }
            ],
            "evidence_packs": [
                {"results": [{"score": 0.8}, {"score": 0.4}], "insufficient_evidence": False}
            ],
            "section_drafts": [
                {
                    "citations": ["a#chunk_001"],
                    "insufficient_evidence": False,
                }
            ],
            "citation_audits": [
                {"valid_citations": 1, "invalid_citations": 2, "downgraded_citations": 1}
            ],
            "review_findings": [{"severity": "high"}, {"severity": "low"}],
            "supervisor_decisions": [{"decision": "edit"}],
            "current_round": 1,
        },
    )

    assert summary.total_agents_run == 1
    assert summary.total_errors == 1
    assert summary.total_warnings == 1
    assert summary.researcher["retrieved_chunks"] == 2
    assert summary.citation_auditor["invalid_citations"] == 2
    assert summary.reviewer["high_severity_findings"] == 1
    assert summary.supervisor["fallback_count"] == 1
