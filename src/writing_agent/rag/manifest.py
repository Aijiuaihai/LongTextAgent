"""Index manifest generation and persistence."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from writing_agent.config import Settings, get_settings
from writing_agent.models import SourceNote
from writing_agent.rag.models import DocumentChunk


def manifest_dir(settings: Settings | None = None) -> Path:
    """Return default index manifest directory."""

    resolved = settings or get_settings()
    return resolved.output_dir / "index_manifests"


def manifest_path(collection: str, settings: Settings | None = None) -> Path:
    """Return manifest path for a collection."""

    return manifest_dir(settings) / f"{collection}.json"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_index_manifest(
    *,
    collection_name: str,
    source_notes: list[SourceNote],
    chunks: list[DocumentChunk],
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable index manifest."""

    resolved = settings or get_settings()
    now = datetime.now(timezone.utc).isoformat()
    sources = []
    for note in source_notes:
        source_chunks = [chunk for chunk in chunks if chunk.source_path == note.path]
        sources.append(
            {
                "source_path": note.path,
                "title": note.title,
                "chunk_count": len(source_chunks),
                "content_hash": _hash_text(note.full_text),
            }
        )
    return {
        "collection_name": collection_name,
        "created_at": now,
        "updated_at": now,
        "embedding_provider": resolved.embedding_provider,
        "embedding_model": resolved.ollama_embedding_model
        if resolved.embedding_provider == "ollama"
        else resolved.openai_model,
        "chunk_count": len(chunks),
        "source_count": len(source_notes),
        "sources": sources,
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "source_path": chunk.source_path,
                "title": chunk.title,
                "chunk_index": chunk.metadata.get("chunk_index"),
                "text_hash": _hash_text(chunk.text),
                "metadata": chunk.metadata,
            }
            for chunk in chunks
        ],
    }


def save_index_manifest(
    manifest: dict[str, Any],
    *,
    settings: Settings | None = None,
) -> Path:
    """Persist a manifest in the default manifest directory."""

    path = manifest_path(str(manifest["collection_name"]), settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_manifest(collection: str, settings: Settings | None = None) -> dict[str, Any] | None:
    """Load a collection manifest if it exists."""

    path = manifest_path(collection, settings)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_manifests(settings: Settings | None = None) -> list[dict[str, Any]]:
    """List all persisted manifests."""

    directory = manifest_dir(settings)
    if not directory.exists():
        return []
    manifests = []
    for path in sorted(directory.glob("*.json")):
        manifests.append(json.loads(path.read_text(encoding="utf-8")))
    return manifests
