"""Persistent web job management."""

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from writing_agent.agents.metrics import summarize_agent_metrics
from writing_agent.checkpoints import update_thread_metadata
from writing_agent.config import Settings, get_settings
from writing_agent.graph.multi_agent_workflow import (
    resume_multi_agent_workflow,
    run_multi_agent_workflow,
)
from writing_agent.graph.workflow import (
    build_workflow,
    generate_thread_id,
    resume_writing_workflow,
    run_writing_workflow,
)
from writing_agent.web.services.event_service import append_event, list_events
from writing_agent.web.services.schemas import (
    JobCreateRequest,
    JobCreateResponse,
    JobEvent,
    JobRecord,
    JobStatus,
    ResumeRequest,
    utc_now,
)

JOB_LOCK = threading.Lock()
WORKFLOW_STEPS = [
    "parse_request",
    "load_sources",
    "plan_outline",
    "write_sections",
    "review_document",
    "revise_document",
    "assemble_document",
    "export_document",
]


def jobs_path(settings: Settings | None = None) -> Path:
    """Return persisted jobs JSON path."""

    resolved = settings or get_settings()
    return resolved.output_dir / "web_jobs" / "jobs.json"


def _atomic_write(path: Path, data: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _read_jobs(settings: Settings | None = None) -> list[JobRecord]:
    path = jobs_path(settings)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [JobRecord.model_validate(item) for item in data]


def _write_jobs(jobs: list[JobRecord], settings: Settings | None = None) -> None:
    _atomic_write(jobs_path(settings), [job.model_dump(mode="json") for job in jobs])


def list_jobs(settings: Settings | None = None) -> list[JobRecord]:
    """List known web jobs."""

    with JOB_LOCK:
        jobs = _read_jobs(settings)
    return [job.model_copy(update={"events": list_events(job.job_id, settings)}) for job in jobs]


def get_job(job_id: str, settings: Settings | None = None) -> JobRecord | None:
    """Return one job record."""

    for job in list_jobs(settings):
        if job.job_id == job_id:
            return job
    return None


def save_job(job: JobRecord, settings: Settings | None = None) -> None:
    """Create or replace a job record."""

    job.updated_at = utc_now()
    job.events = list_events(job.job_id, settings)
    with JOB_LOCK:
        jobs = _read_jobs(settings)
        replaced = False
        for index, existing in enumerate(jobs):
            if existing.job_id == job.job_id:
                jobs[index] = job
                replaced = True
                break
        if not replaced:
            jobs.append(job)
        _write_jobs(jobs, settings)


def add_job_event(
    job: JobRecord,
    event: str,
    *,
    message: str = "",
    step: str = "",
    settings: Settings | None = None,
    payload: dict[str, object] | None = None,
) -> JobEvent:
    """Append an event and mirror it into the job metadata."""

    item = append_event(
        job.job_id,
        event,
        message=message,
        step=step,
        settings=settings,
        payload=payload,
    )
    job.events = list_events(job.job_id, settings)
    save_job(job, settings)
    return item


def create_job(
    request: JobCreateRequest,
    *,
    settings: Settings | None = None,
) -> JobCreateResponse:
    """Create a pending job."""

    thread_id = request.thread_id or generate_thread_id("web-writing")
    job = JobRecord(
        job_id=uuid.uuid4().hex,
        thread_id=thread_id,
        topic=request.topic,
        request=request.model_dump(mode="json"),
    )
    save_job(job, settings)
    add_job_event(job, "started", message="Job created.", settings=settings)
    return JobCreateResponse(
        job_id=job.job_id,
        thread_id=thread_id,
        status=job.status,
        created_at=job.created_at,
    )


def _set_status(
    job: JobRecord,
    status: JobStatus,
    *,
    settings: Settings | None = None,
    current_step: str | None = None,
    error_message: str | None = None,
) -> None:
    job.status = status
    if current_step is not None:
        job.current_step = current_step
    if error_message is not None:
        job.error_message = error_message
    save_job(job, settings)


def run_job(
    job_id: str,
    *,
    settings: Settings | None = None,
    runner: object | None = None,
) -> None:
    """Execute a pending job using the existing writing workflow."""

    resolved_settings = settings or get_settings()
    job = get_job(job_id, resolved_settings)
    if job is None:
        return
    payload = JobCreateRequest.model_validate(job.request)
    _set_status(job, "running", settings=resolved_settings, current_step="starting")
    add_job_event(job, "started", message="Workflow started.", settings=resolved_settings)
    for step in WORKFLOW_STEPS:
        add_job_event(
            job,
            "step_started",
            step=step,
            message=f"Starting {step}.",
            settings=resolved_settings,
        )
    try:
        initial_state = {
            "request": payload.to_writing_request(),
            "output_dir": str(resolved_settings.output_dir),
            "output_format": payload.output_format,
            "docx_template": payload.docx_template,
            "rag_enabled": payload.rag,
            "rag_mode": payload.rag_mode,
            "rag_collection": payload.collection,
            "rag_top_k": payload.top_k,
            "mode": payload.mode,
            "review_outline": payload.review_outline if payload.mode == "multi" else False,
            "review_final": payload.review_final if payload.mode == "multi" else False,
        }
        if runner is not None:
            result = runner(
                initial_state,
                settings=resolved_settings,
                thread_id=job.thread_id,
                use_llm=payload.use_llm,
            )
        elif payload.mode == "multi":
            result = run_multi_agent_workflow(
                initial_state,
                settings=resolved_settings,
                thread_id=job.thread_id,
                max_rounds=payload.max_agent_rounds,
            )
        else:
            result = run_writing_workflow(
                initial_state,
                settings=resolved_settings,
                thread_id=job.thread_id,
                use_llm=payload.use_llm,
            )
        for step in WORKFLOW_STEPS:
            add_job_event(
                job,
                "step_finished",
                step=step,
                message=f"Finished {step}.",
                settings=resolved_settings,
            )
        job.current_step = str(result.get("current_step", ""))
        job.output_files = {
            str(key): str(value)
            for key, value in dict(result.get("output_paths") or {}).items()
        }
        if result.get("output_path") and not job.output_files:
            job.output_files = {"markdown": str(result["output_path"])}
        job.agent_results = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in result.get("agent_results", [])
        ]
        job.supervisor_decisions = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in result.get("supervisor_decisions", [])
        ]
        job.evaluation_result = dict(result.get("evaluation_result", {}) or {})
        job.agent_metrics = dict(
            result.get("agent_metrics")
            or summarize_agent_metrics(job.thread_id, result).model_dump(mode="json")
        )
        for agent_result in job.agent_results:
            add_job_event(
                job,
                "agent_finished",
                message=str(agent_result.get("status", "")),
                step=str(agent_result.get("agent_name", "")),
                settings=resolved_settings,
                payload={"agent_result": agent_result},
            )
        for decision in job.supervisor_decisions:
            add_job_event(
                job,
                "supervisor_decision",
                message=str(decision.get("reason", "")),
                step="supervisor",
                settings=resolved_settings,
                payload={"decision": decision},
            )
        if job.agent_results:
            add_job_event(
                job,
                "trace_updated",
                message="Agent trace updated.",
                step="agents",
                settings=resolved_settings,
                payload={"trace": build_job_agent_trace(job)},
            )
        if job.evaluation_result:
            add_job_event(
                job,
                "evaluation_completed",
                message="Evaluation completed.",
                step="evaluator",
                settings=resolved_settings,
                payload={"evaluation_result": job.evaluation_result},
            )
        if result.get("__interrupt__"):
            job.status = "interrupted"
            job.interrupt_payload = result.get("__interrupt__")
            step = _interrupt_step(job.interrupt_payload)
            if step:
                job.current_step = step
            add_job_event(
                job,
                "interrupted",
                message="Workflow interrupted for human review.",
                step=step,
                settings=resolved_settings,
            )
        else:
            job.status = "completed"
            add_job_event(
                job,
                "exported",
                message="Document exported.",
                settings=resolved_settings,
                payload={"output_files": job.output_files},
            )
            add_job_event(
                job,
                "completed",
                message="Workflow completed.",
                settings=resolved_settings,
            )
        save_job(job, resolved_settings)
        update_thread_metadata(
            job.thread_id,
            result,
            interrupted=job.status == "interrupted",
            settings=resolved_settings,
        )
    except Exception as exc:
        _set_status(job, "failed", settings=resolved_settings, error_message=str(exc))
        add_job_event(job, "failed", message=str(exc), settings=resolved_settings)


def resume_job(
    job_id: str,
    request: ResumeRequest,
    *,
    settings: Settings | None = None,
) -> JobRecord:
    """Resume an interrupted job."""

    resolved_settings = settings or get_settings()
    job = get_job(job_id, resolved_settings)
    if job is None:
        raise KeyError(f"Unknown job: {job_id}")
    _set_status(job, "running", settings=resolved_settings)
    add_job_event(job, "resumed", message="Human review submitted.", settings=resolved_settings)
    try:
        payload = JobCreateRequest.model_validate(job.request)
        if payload.mode == "multi":
            result = resume_multi_agent_workflow(
                job.thread_id,
                request.review,
                settings=resolved_settings,
            )
        else:
            result = resume_writing_workflow(
                job.thread_id,
                request.review,
                settings=resolved_settings,
            )
        job.current_step = str(result.get("current_step", ""))
        job.output_files = {
            str(key): str(value)
            for key, value in dict(result.get("output_paths") or {}).items()
        }
        if result.get("output_path") and not job.output_files:
            job.output_files = {"markdown": str(result["output_path"])}
        job.status = "interrupted" if result.get("__interrupt__") else "completed"
        job.interrupt_payload = result.get("__interrupt__")
        step = _interrupt_step(job.interrupt_payload)
        if step:
            job.current_step = step
        job.agent_results = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in result.get("agent_results", [])
        ]
        job.supervisor_decisions = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in result.get("supervisor_decisions", [])
        ]
        job.evaluation_result = dict(result.get("evaluation_result", {}) or {})
        job.agent_metrics = dict(
            result.get("agent_metrics")
            or summarize_agent_metrics(job.thread_id, result).model_dump(mode="json")
        )
        for agent_result in job.agent_results:
            add_job_event(
                job,
                "agent_finished",
                message=str(agent_result.get("status", "")),
                step=str(agent_result.get("agent_name", "")),
                settings=resolved_settings,
                payload={"agent_result": agent_result},
            )
        if job.agent_results:
            add_job_event(
                job,
                "trace_updated",
                message="Agent trace updated.",
                step="agents",
                settings=resolved_settings,
                payload={"trace": build_job_agent_trace(job)},
            )
        add_job_event(
            job,
            "interrupted" if job.status == "interrupted" else "completed",
            message="Workflow resumed.",
            step=step,
            settings=resolved_settings,
        )
        save_job(job, resolved_settings)
        return job
    except Exception as exc:
        _set_status(job, "failed", settings=resolved_settings, error_message=str(exc))
        add_job_event(job, "failed", message=str(exc), settings=resolved_settings)
        raise


def cancel_job(job_id: str, settings: Settings | None = None) -> JobRecord:
    """Mark a job as cancellation requested."""

    job = get_job(job_id, settings)
    if job is None:
        raise KeyError(f"Unknown job: {job_id}")
    job.status = "cancel_requested"
    add_job_event(job, "cancel_requested", message="Cancellation requested.", settings=settings)
    save_job(job, settings)
    return job


def get_job_agent_metrics(job_id: str, settings: Settings | None = None) -> dict[str, object]:
    """Return persisted agent metrics for a web job."""

    job = get_job(job_id, settings)
    if job is None:
        raise KeyError(f"Unknown job: {job_id}")
    if job.agent_metrics:
        return job.agent_metrics
    return summarize_agent_metrics(
        job.thread_id,
        {
            "mode": job.request.get("mode", "single"),
            "agent_results": job.agent_results,
            "supervisor_decisions": job.supervisor_decisions,
            "evaluation_result": job.evaluation_result,
        },
    ).model_dump(mode="json")


def build_job_agent_trace(job: JobRecord) -> dict[str, object]:
    """Build a graph-friendly agent trace payload."""

    nodes: list[dict[str, object]] = []
    edges: list[dict[str, object]] = []
    previous_id = ""
    for index, result in enumerate(job.agent_results):
        agent_name = str(result.get("agent_name", f"agent_{index}"))
        node_id = f"{index}_{agent_name}"
        nodes.append(
            {
                "id": node_id,
                "label": agent_name,
                "status": str(result.get("status", "")),
                "duration_seconds": float(result.get("duration_seconds", 0) or 0),
                "warnings": list(result.get("warnings", []) or []),
                "errors": list(result.get("errors", []) or []),
                "output_summary": str(result.get("output", ""))[:500],
            }
        )
        if previous_id:
            edges.append({"from": previous_id, "to": node_id, "label": "next"})
        previous_id = node_id
    rounds = 0.0
    if job.agent_metrics:
        supervisor = job.agent_metrics.get("supervisor", {})
        if isinstance(supervisor, dict):
            rounds = float(supervisor.get("rounds_used", 0) or 0)
    return {
        "nodes": nodes,
        "edges": edges,
        "supervisor_decisions": job.supervisor_decisions,
        "rounds": rounds,
    }


def get_job_agent_trace(job_id: str, settings: Settings | None = None) -> dict[str, object]:
    """Return graph-friendly agent trace for a web job."""

    job = get_job(job_id, settings)
    if job is None:
        raise KeyError(f"Unknown job: {job_id}")
    return build_job_agent_trace(job)


def build_workflow_for_testing() -> object:
    """Expose workflow construction for tests without changing core imports."""

    return build_workflow(checkpointer=False)


def _interrupt_step(payload: object) -> str:
    """Extract a visible interrupt step from LangGraph payload variants."""

    if isinstance(payload, dict):
        return str(payload.get("step", ""))
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            return str(first.get("step", ""))
        value = getattr(first, "value", None)
        if isinstance(value, dict):
            return str(value.get("step", ""))
    value = getattr(payload, "value", None)
    if isinstance(value, dict):
        return str(value.get("step", ""))
    return ""
