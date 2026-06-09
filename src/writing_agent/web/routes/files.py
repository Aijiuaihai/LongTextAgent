"""File management endpoints."""

from typing import Annotated

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import JSONResponse

from writing_agent.web.services.file_service import (
    delete_uploaded_file,
    list_data_files,
    save_upload_file,
)

router = APIRouter()


@router.post("/files/upload")
def upload_file(
    request: Request,
    file: Annotated[UploadFile, File()],
) -> dict[str, object]:
    """Upload one local source file."""

    return save_upload_file(file, settings=request.app.state.settings)


@router.get("/files")
def list_files(request: Request) -> list[dict[str, object]]:
    """List available data files."""

    return list_data_files(request.app.state.settings)


@router.delete("/files/{file_id}")
def delete_file(file_id: str, request: Request) -> dict[str, object]:
    """Delete an uploaded data file."""

    try:
        deleted = delete_uploaded_file(file_id, request.app.state.settings)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)  # type: ignore[return-value]
    return {"deleted": deleted}
