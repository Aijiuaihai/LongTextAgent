"""Local document loading utilities."""

from pathlib import Path

from writing_agent.models import SourceNote

SUPPORTED_EXTENSIONS = {".md", ".txt", ".docx", ".pdf"}
MAX_FULL_TEXT_CHARS = 40_000
PREVIEW_CHARS = 1_200


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_docx(path: Path) -> str:
    try:
        from docx import Document
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("Install python-docx to read .docx source files.") from exc

    document = Document(str(path))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n\n".join(paragraphs)


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("Install pypdf to read .pdf source files.") from exc

    reader = PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(page.strip() for page in pages if page.strip())


def _read_supported_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt"}:
        return _read_text(path)
    if suffix == ".docx":
        return _read_docx(path)
    if suffix == ".pdf":
        return _read_pdf(path)
    raise ValueError(f"Unsupported source file extension: {path}")


def _iter_source_files(paths: list[str]) -> list[Path]:
    files: list[Path] = []
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"Source path does not exist: {raw_path}")
        if path.is_dir():
            files.extend(
                child
                for child in sorted(path.rglob("*"))
                if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS
            )
        elif path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)
        else:
            raise ValueError(f"Unsupported source file extension: {path}")
    return files


def _truncate(text: str, limit: int) -> str:
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "\n\n[Truncated for context budget.]"


def load_sources(paths: list[str]) -> list[SourceNote]:
    """Load local source documents into normalized source notes."""

    notes: list[SourceNote] = []
    for path in _iter_source_files(paths):
        full_text = _truncate(_read_supported_file(path), MAX_FULL_TEXT_CHARS)
        notes.append(
            SourceNote(
                path=str(path),
                title=path.stem.replace("_", " ").replace("-", " ").strip() or path.name,
                content_preview=_truncate(full_text, PREVIEW_CHARS),
                full_text=full_text,
            )
        )
    return notes
