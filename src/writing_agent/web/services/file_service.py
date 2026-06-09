"""File upload and listing services for the web console."""

import base64
from pathlib import Path

from fastapi import UploadFile

from writing_agent.config import Settings, get_settings
from writing_agent.web.security import (
    ALLOWED_EXTENSIONS,
    ensure_deletable_upload,
    ensure_within_directory,
    read_limited_upload,
    sanitize_filename,
    uploads_dir,
)


def encode_path_id(path: Path, root: Path) -> str:
    """Encode a relative path as a URL-safe id."""

    relative = path.resolve().relative_to(root.resolve()).as_posix()
    return base64.urlsafe_b64encode(relative.encode("utf-8")).decode("ascii")


def decode_path_id(file_id: str, root: Path) -> Path:
    """Decode a URL-safe id under a root directory."""

    try:
        relative = base64.urlsafe_b64decode(file_id.encode("ascii")).decode("utf-8")
    except Exception as exc:
        raise ValueError("Invalid file id.") from exc
    return ensure_within_directory(root / relative, root)


def save_upload_file(
    upload: UploadFile,
    *,
    settings: Settings | None = None,
) -> dict[str, str | int]:
    """Persist an uploaded source file under data/uploads."""

    resolved = settings or get_settings()
    directory = uploads_dir(resolved)
    directory.mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(upload.filename or "upload.txt")
    output_path = directory / filename
    content = read_limited_upload(upload.file)
    output_path.write_bytes(content)
    return {
        "file_id": encode_path_id(output_path, resolved.data_dir),
        "path": str(output_path),
        "name": output_path.name,
        "size": len(content),
    }


def list_data_files(settings: Settings | None = None) -> list[dict[str, str | int]]:
    """List supported files under data/."""

    resolved = settings or get_settings()
    root = resolved.data_dir
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            rows.append(
                {
                    "file_id": encode_path_id(path, root),
                    "path": str(path),
                    "name": path.name,
                    "size": path.stat().st_size,
                }
            )
    return rows


def delete_uploaded_file(file_id: str, settings: Settings | None = None) -> bool:
    """Delete a file only if it is inside data/uploads."""

    resolved = settings or get_settings()
    path = decode_path_id(file_id, resolved.data_dir)
    deletable = ensure_deletable_upload(path, resolved)
    if not deletable.exists() or not deletable.is_file():
        return False
    deletable.unlink()
    return True

