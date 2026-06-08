"""FastAPI frontend for the writing agent."""

from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from writing_agent.config import Settings, get_settings
from writing_agent.graph.workflow import generate_thread_id, run_writing_workflow
from writing_agent.models import DocumentType, WritingRequest
from writing_agent.tools.document_loader import load_sources

STATIC_DIR = Path(__file__).parent / "static"
SUPPORTED_UPLOAD_EXTENSIONS = {".md", ".txt", ".docx", ".pdf"}


class WebGenerationResult(BaseModel):
    """API response for one generation request."""

    thread_id: str
    topic: str
    output_path: str = ""
    output_paths: dict[str, str] = {}
    errors: list[str] = []


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the FastAPI app."""

    resolved_settings = settings or get_settings()
    app = FastAPI(title="LongTextAgent", version="0.1.0")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return (STATIC_DIR / "index.html").read_text(encoding="utf-8")

    @app.get("/static/{asset_name}")
    async def static_asset(asset_name: str) -> Response:
        path = STATIC_DIR / asset_name
        if not path.exists() or not path.is_file():
            return Response(status_code=404)
        media_type = "text/css" if path.suffix == ".css" else "application/javascript"
        return Response(path.read_text(encoding="utf-8"), media_type=media_type)

    @app.get("/api/config")
    async def config() -> dict[str, Any]:
        return resolved_settings.safe_summary()

    @app.post("/api/generate")
    async def generate(
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
        request_file: Annotated[UploadFile | None, File()] = None,
        source_files: Annotated[list[UploadFile] | None, File()] = None,
    ) -> JSONResponse:
        try:
            result = await run_in_threadpool(
                _generate_document,
                settings=resolved_settings,
                topic=topic,
                document_type=document_type,
                audience=audience,
                length=length,
                style=style,
                request_text=request_text,
                output_format=output_format,
                rag=rag,
                rag_mode=rag_mode,
                collection=collection,
                top_k=top_k,
                use_llm=use_llm,
                request_file=request_file,
                source_files=source_files or [],
            )
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)
        return JSONResponse(result.model_dump(mode="json"))

    return app


def _safe_upload_name(name: str) -> str:
    clean = Path(name or "upload.txt").name
    if Path(clean).suffix.lower() not in SUPPORTED_UPLOAD_EXTENSIONS:
        raise ValueError(f"Unsupported upload file extension: {clean}")
    return clean


def _save_upload(upload: UploadFile, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / _safe_upload_name(upload.filename or "upload.txt")
    content = upload.file.read()
    path.write_bytes(content)
    upload.file.seek(0)
    return path


def _read_requirement_file(path: Path) -> str:
    notes = load_sources([str(path)])
    if not notes:
        return ""
    return notes[0].full_text


def _build_request(
    *,
    topic: str,
    document_type: DocumentType,
    audience: str,
    length: str,
    style: str,
    request_text: str,
    requirement_file_text: str,
    requirement_file_path: Path | None,
    source_paths: list[str],
) -> WritingRequest:
    resolved_topic = topic.strip()
    if not resolved_topic and requirement_file_path is not None:
        resolved_topic = requirement_file_path.stem.replace("_", " ").replace("-", " ")
    if not resolved_topic:
        resolved_topic = "Untitled long-form writing task"
    constraints = []
    if request_text.strip():
        constraints.append(f"User requirement text:\n{request_text.strip()}")
    if requirement_file_text.strip():
        constraints.append(f"Uploaded requirement document:\n{requirement_file_text[:12000]}")
    return WritingRequest(
        topic=resolved_topic,
        document_type=document_type,
        audience=audience,
        target_length=length,
        style=style,
        constraints=constraints,
        source_paths=source_paths,
    )


def _generate_document(
    *,
    settings: Settings,
    topic: str,
    document_type: DocumentType,
    audience: str,
    length: str,
    style: str,
    request_text: str,
    output_format: str,
    rag: bool,
    rag_mode: str,
    collection: str,
    top_k: int,
    use_llm: bool,
    request_file: UploadFile | None,
    source_files: list[UploadFile],
) -> WebGenerationResult:
    thread_id = generate_thread_id("web-writing")
    upload_dir = settings.output_dir / "uploads" / thread_id
    source_paths: list[str] = []
    requirement_file_path: Path | None = None
    requirement_file_text = ""
    if request_file is not None and request_file.filename:
        requirement_file_path = _save_upload(request_file, upload_dir)
        source_paths.append(str(requirement_file_path))
        requirement_file_text = _read_requirement_file(requirement_file_path)
    for source_file in source_files:
        if source_file.filename:
            source_paths.append(str(_save_upload(source_file, upload_dir)))

    request = _build_request(
        topic=topic,
        document_type=document_type,
        audience=audience,
        length=length,
        style=style,
        request_text=request_text,
        requirement_file_text=requirement_file_text,
        requirement_file_path=requirement_file_path,
        source_paths=source_paths,
    )
    workflow_result = run_writing_workflow(
        {
            "request": request,
            "output_dir": str(settings.output_dir),
            "output_format": output_format,
            "rag_enabled": rag,
            "rag_mode": rag_mode,
            "rag_collection": collection,
            "rag_top_k": top_k,
        },
        settings=settings,
        thread_id=thread_id,
        use_llm=use_llm,
    )
    output_paths = workflow_result.get("output_paths") or {}
    return WebGenerationResult(
        thread_id=thread_id,
        topic=request.topic,
        output_path=str(workflow_result.get("output_path", "")),
        output_paths={str(key): str(value) for key, value in dict(output_paths).items()},
        errors=[str(error) for error in workflow_result.get("errors", [])],
    )


app = create_app()
