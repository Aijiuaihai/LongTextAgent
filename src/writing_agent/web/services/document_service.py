"""Generated document listing and actions."""

from pathlib import Path
from typing import Any

from writing_agent.config import Settings, get_settings
from writing_agent.evaluation.evaluator import evaluate_markdown
from writing_agent.evaluation.llm_judge import judge_document_with_llm
from writing_agent.verification.repair import repair_citations_in_file
from writing_agent.verification.verifier import verify_citations_in_file
from writing_agent.web.security import ensure_within_directory
from writing_agent.web.services.file_service import decode_path_id, encode_path_id

DOCUMENT_EXTENSIONS = {".md", ".docx"}


def _output_root(settings: Settings | None = None) -> Path:
    return (settings or get_settings()).output_dir


def resolve_document_id(document_id: str, settings: Settings | None = None) -> Path:
    """Resolve a document id under outputs/."""

    root = _output_root(settings)
    path = decode_path_id(document_id, root)
    if path.suffix.lower() not in DOCUMENT_EXTENSIONS:
        raise ValueError("Unsupported document type.")
    return ensure_within_directory(path, root)


def list_documents(settings: Settings | None = None) -> list[dict[str, Any]]:
    """List generated markdown/docx documents under outputs/."""

    root = _output_root(settings)
    if not root.exists():
        return []
    rows = []
    for path in sorted(root.rglob("*"), reverse=True):
        if not path.is_file() or path.suffix.lower() not in DOCUMENT_EXTENSIONS:
            continue
        if any(part in {"web_jobs", "uploads", "chroma", "index_manifests"} for part in path.parts):
            continue
        rows.append(
            {
                "document_id": encode_path_id(path, root),
                "name": path.name,
                "path": str(path),
                "extension": path.suffix.lower(),
                "size": path.stat().st_size,
                "updated_at": path.stat().st_mtime,
            }
        )
    return rows


def preview_document(document_id: str, settings: Settings | None = None) -> dict[str, Any]:
    """Return markdown content or docx metadata."""

    path = resolve_document_id(document_id, settings)
    if path.suffix.lower() == ".md":
        return {"type": "markdown", "content": path.read_text(encoding="utf-8")}
    return {"type": "docx", "name": path.name, "size": path.stat().st_size}


def verify_document_citations(
    document_id: str,
    *,
    collection: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Run citation verification for a markdown document."""

    path = resolve_document_id(document_id, settings)
    result = verify_citations_in_file(path, collection=collection)
    return result.model_dump(mode="json")


def repair_document_citations(
    document_id: str,
    *,
    collection: str | None = None,
    mode: str = "conservative",
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Repair markdown citations for a document."""

    path = resolve_document_id(document_id, settings)
    result = repair_citations_in_file(
        path,
        collection=collection,
        mode="llm_assisted" if mode == "llm_assisted" else "conservative",
        settings=settings,
    )
    return result.model_dump(mode="json")


def evaluate_document(
    document_id: str,
    *,
    llm_judge: bool = False,
    verify_citations: bool = False,
    collection: str | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Evaluate a markdown document."""

    path = resolve_document_id(document_id, settings)
    if path.suffix.lower() != ".md":
        raise ValueError("Only markdown documents can be evaluated.")
    result: dict[str, Any] = {"rule_metrics": evaluate_markdown(path)}
    if verify_citations:
        result["citation_verification"] = verify_citations_in_file(
            path,
            collection=collection,
        ).model_dump(mode="json")
    if llm_judge:
        result["llm_judge"] = judge_document_with_llm(path, settings=settings)
    return result

