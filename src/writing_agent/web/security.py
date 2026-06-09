"""Security helpers for local-only web console file access."""

import re
from pathlib import Path
from typing import BinaryIO

from writing_agent.config import Settings, get_settings

ALLOWED_EXTENSIONS = {".md", ".txt", ".docx", ".pdf"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def sanitize_filename(filename: str) -> str:
    """Return a conservative filename safe for local storage."""

    name = Path(filename or "upload.txt").name
    stem = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", name).strip("._")
    clean = stem or "upload.txt"
    suffix = Path(clean).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {suffix or clean}")
    return clean


def ensure_within_directory(path: Path, directory: Path) -> Path:
    """Resolve a path and ensure it remains under a directory."""

    resolved_path = path.resolve()
    resolved_directory = directory.resolve()
    if resolved_path == resolved_directory or resolved_directory in resolved_path.parents:
        return resolved_path
    raise ValueError(f"Path is outside allowed directory: {path}")


def allowed_roots(settings: Settings | None = None) -> list[Path]:
    """Return directories the web console may read from."""

    resolved = settings or get_settings()
    return [resolved.data_dir, resolved.output_dir, Path("templates")]


def ensure_allowed_read_path(path: Path | str, settings: Settings | None = None) -> Path:
    """Resolve a user supplied path under an allowed root."""

    candidate = Path(path)
    for root in allowed_roots(settings):
        try:
            return ensure_within_directory(candidate, root)
        except ValueError:
            continue
    raise ValueError(f"Path is outside allowed roots: {path}")


def uploads_dir(settings: Settings | None = None) -> Path:
    """Return the data/uploads directory."""

    resolved = settings or get_settings()
    return resolved.data_dir / "uploads"


def ensure_deletable_upload(path: Path | str, settings: Settings | None = None) -> Path:
    """Only allow deletion inside data/uploads."""

    return ensure_within_directory(Path(path), uploads_dir(settings))


def read_limited_upload(stream: BinaryIO, limit: int = MAX_UPLOAD_BYTES) -> bytes:
    """Read an upload stream with a hard byte limit."""

    data = stream.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f"Uploaded file exceeds {limit} bytes.")
    return data

