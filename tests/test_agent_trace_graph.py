from writing_agent.web.services.job_service import build_job_agent_trace
from writing_agent.web.services.schemas import JobRecord


def test_build_job_agent_trace_returns_nodes_and_edges() -> None:
    job = JobRecord(
        job_id="job-1",
        thread_id="thread-1",
        topic="Trace",
        request={"topic": "Trace", "mode": "multi"},
        agent_results=[
            {"agent_name": "planner", "status": "success", "duration_seconds": 0.1},
            {"agent_name": "writer", "status": "failed", "errors": ["bad"]},
        ],
        supervisor_decisions=[{"decision": "edit"}],
        agent_metrics={"supervisor": {"rounds_used": 1}},
    )

    trace = build_job_agent_trace(job)

    assert len(trace["nodes"]) == 2
    assert trace["nodes"][1]["status"] == "failed"
    assert trace["edges"][0]["from"] == "0_planner"
    assert trace["rounds"] == 1
