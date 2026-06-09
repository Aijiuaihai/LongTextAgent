"""Generated document endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse

from writing_agent.web.services.document_service import (
    evaluate_document,
    list_documents,
    preview_document,
    repair_document_citations,
    resolve_document_id,
    verify_document_citations,
)
from writing_agent.web.services.schemas import CitationActionRequest, EvaluateRequest

router = APIRouter()


@router.get("/documents")
def documents(request: Request) -> list[dict[str, object]]:
    """List generated documents."""

    return list_documents(request.app.state.settings)


@router.get("/documents/{document_id}/preview")
def document_preview(document_id: str, request: Request) -> dict[str, object]:
    """Preview a generated document."""

    return preview_document(document_id, request.app.state.settings)


@router.get("/documents/{document_id}/download")
def document_download(document_id: str, request: Request) -> FileResponse:
    """Download a generated document."""

    path = resolve_document_id(document_id, request.app.state.settings)
    return FileResponse(path, filename=path.name)


@router.post("/documents/{document_id}/verify-citations")
def document_verify(
    document_id: str,
    payload: CitationActionRequest,
    request: Request,
) -> dict[str, object]:
    """Verify citations for a generated markdown document."""

    try:
        return verify_document_citations(
            document_id,
            collection=payload.collection,
            settings=request.app.state.settings,
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)  # type: ignore[return-value]


@router.post("/documents/{document_id}/repair-citations")
def document_repair(
    document_id: str,
    payload: CitationActionRequest,
    request: Request,
) -> dict[str, object]:
    """Repair citations for a generated markdown document."""

    try:
        return repair_document_citations(
            document_id,
            collection=payload.collection,
            mode=payload.mode,
            settings=request.app.state.settings,
        )
    except (ValueError, FileNotFoundError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)  # type: ignore[return-value]


@router.post("/documents/{document_id}/evaluate")
def document_evaluate(
    document_id: str,
    payload: EvaluateRequest,
    request: Request,
) -> dict[str, object]:
    """Evaluate a generated markdown document."""

    try:
        return evaluate_document(
            document_id,
            llm_judge=payload.llm_judge,
            verify_citations=payload.verify_citations,
            collection=payload.collection,
            settings=request.app.state.settings,
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)  # type: ignore[return-value]

