"""Job API endpoints."""

import json
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from writing_agent.models import DocumentType
from writing_agent.web.services.event_service import stream_events
from writing_agent.web.services.file_service import save_upload_file
from writing_agent.web.services.job_service import (
    cancel_job,
    create_job,
    get_job,
    get_job_agent_metrics,
    get_job_agent_trace,
    list_jobs,
    resume_job,
    run_job,
)
from writing_agent.web.services.schemas import JobCreateRequest, ResumeRequest

router = APIRouter()


@router.post("/jobs")
def create_job_endpoint(
    payload: JobCreateRequest,
    background_tasks: BackgroundTasks,
    request: Request,
) -> dict[str, object]:
    """Create and start a writing job."""

    response = create_job(payload, settings=request.app.state.settings)
    background_tasks.add_task(run_job, response.job_id, settings=request.app.state.settings)
    return response.model_dump(mode="json")


@router.get("/jobs")
def list_jobs_endpoint(request: Request) -> list[dict[str, object]]:
    """List writing jobs."""

    return [
        job.model_dump(mode="json", exclude={"events", "request", "interrupt_payload"})
        for job in list_jobs(request.app.state.settings)
    ]


@router.get("/jobs/{job_id}")
def get_job_endpoint(job_id: str, request: Request) -> dict[str, object]:
    """Return one job detail."""

    job = get_job(job_id, request.app.state.settings)
    if job is None:
        return JSONResponse({"error": "job not found"}, status_code=404)  # type: ignore[return-value]
    return job.model_dump(mode="json")


@router.post("/jobs/{job_id}/resume")
def resume_job_endpoint(
    job_id: str,
    payload: ResumeRequest,
    request: Request,
) -> dict[str, object]:
    """Resume an interrupted job."""

    try:
        job = resume_job(job_id, payload, settings=request.app.state.settings)
    except KeyError:
        return JSONResponse({"error": "job not found"}, status_code=404)  # type: ignore[return-value]
    return job.model_dump(mode="json")


@router.post("/jobs/{job_id}/cancel")
def cancel_job_endpoint(job_id: str, request: Request) -> dict[str, object]:
    """Mark a job as cancellation requested."""

    try:
        job = cancel_job(job_id, request.app.state.settings)
    except KeyError:
        return JSONResponse({"error": "job not found"}, status_code=404)  # type: ignore[return-value]
    return job.model_dump(mode="json")


@router.get("/jobs/{job_id}/events")
def job_events(job_id: str, request: Request) -> StreamingResponse:
    """Stream job events as SSE."""

    return StreamingResponse(
        stream_events(job_id, settings=request.app.state.settings),
        media_type="text/event-stream",
    )


@router.get("/jobs/{job_id}/agent-metrics")
def job_agent_metrics(job_id: str, request: Request) -> dict[str, object]:
    """Return agent metrics for one job."""

    try:
        return get_job_agent_metrics(job_id, request.app.state.settings)
    except KeyError:
        return JSONResponse({"error": "job not found"}, status_code=404)  # type: ignore[return-value]


@router.get("/jobs/{job_id}/agent-trace")
def job_agent_trace(job_id: str, request: Request) -> dict[str, object]:
    """Return graph-friendly agent trace for one job."""

    try:
        return get_job_agent_trace(job_id, request.app.state.settings)
    except KeyError:
        return JSONResponse({"error": "job not found"}, status_code=404)  # type: ignore[return-value]


@router.post("/generate")
def generate_compat(
    background_tasks: BackgroundTasks,
    request: Request,
    topic: Annotated[str, Form()] = "",
    document_type: Annotated[DocumentType, Form(alias="type")] = DocumentType.REPORT,
    audience: Annotated[str, Form()] = "general readers",
    length: Annotated[str, Form()] = "3000 words",
    style: Annotated[str, Form()] = "formal and concise",
    request_text: Annotated[str, Form()] = "",
    output_format: Annotated[str, Form()] = "markdown",
    rag: Annotated[bool, Form()] = True,
    rag_mode: Annotated[str, Form()] = "hybrid",
    collection: Annotated[str, Form()] = "",
    top_k: Annotated[int, Form()] = 5,
    use_llm: Annotated[bool, Form()] = True,
    mode: Annotated[str, Form()] = "single",
    max_agent_rounds: Annotated[int, Form()] = 2,
    agent_debug: Annotated[bool, Form()] = False,
    review_outline: Annotated[bool, Form()] = False,
    review_final: Annotated[bool, Form()] = False,
    request_file: Annotated[UploadFile | None, File()] = None,
    source_files: Annotated[list[UploadFile] | None, File()] = None,
) -> dict[str, object]:
    """Compatibility endpoint for the initial simple frontend."""

    settings = request.app.state.settings
    source_paths: list[str] = []
    constraints: list[str] = []
    if request_text.strip():
        constraints.append(f"User requirement text:\n{request_text.strip()}")
    if request_file is not None and request_file.filename:
        saved = save_upload_file(request_file, settings=settings)
        source_paths.append(str(saved["path"]))
        constraints.append(f"Uploaded requirement document: {saved['path']}")
    for upload in source_files or []:
        if upload.filename:
            saved = save_upload_file(upload, settings=settings)
            source_paths.append(str(saved["path"]))
    payload = JobCreateRequest(
        topic=topic.strip() or "Untitled long-form writing task",
        document_type=document_type,
        audience=audience,
        target_length=length,
        style=style,
        source_paths=source_paths,
        constraints=constraints,
        collection=collection,
        rag=rag,
        rag_mode=rag_mode,
        top_k=top_k,
        output_format=output_format,
        use_llm=use_llm,
        mode="multi" if mode == "multi" else "single",
        max_agent_rounds=max_agent_rounds,
        agent_debug=agent_debug,
        review_outline=review_outline,
        review_final=review_final,
    )
    response = create_job(payload, settings=settings)
    background_tasks.add_task(run_job, response.job_id, settings=settings)
    return {
        **response.model_dump(mode="json"),
        "topic": payload.topic,
        "output_path": "",
        "output_paths": {},
        "errors": [],
        "request": json.loads(payload.model_dump_json()),
    }
