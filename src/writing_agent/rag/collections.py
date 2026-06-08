"""Local Chroma collection management helpers."""

import json
import shutil
from pathlib import Path
from typing import Any

from writing_agent.config import Settings, get_settings
from writing_agent.rag.manifest import list_manifests, load_manifest, manifest_path
from writing_agent.rag.vector_index import add_documents_to_index, default_persist_dir
from writing_agent.tools.document_loader import load_sources


def list_collections(settings: Settings | None = None) -> list[dict[str, Any]]:
    """List known collections from manifests."""

    return [
        {
            "collection_name": item.get("collection_name", ""),
            "updated_at": item.get("updated_at", ""),
            "source_count": item.get("source_count", 0),
            "chunk_count": item.get("chunk_count", 0),
        }
        for item in list_manifests(settings)
    ]


def get_collection_stats(collection: str, settings: Settings | None = None) -> dict[str, Any]:
    """Return collection stats from manifest."""

    manifest = load_manifest(collection, settings)
    if manifest is None:
        return {"collection_name": collection, "exists": False}
    return {
        "collection_name": collection,
        "exists": True,
        "source_count": manifest.get("source_count", 0),
        "chunk_count": manifest.get("chunk_count", 0),
        "embedding_provider": manifest.get("embedding_provider", ""),
        "embedding_model": manifest.get("embedding_model", ""),
        "updated_at": manifest.get("updated_at", ""),
    }


def delete_collection(collection: str, settings: Settings | None = None) -> bool:
    """Delete local collection metadata and best-effort Chroma persistence."""

    resolved = settings or get_settings()
    manifest = manifest_path(collection, resolved)
    existed = manifest.exists()
    if existed:
        manifest.unlink()
    persist_dir = default_persist_dir(resolved)
    possible_dir = persist_dir / collection
    if possible_dir.exists() and possible_dir.is_dir():
        shutil.rmtree(possible_dir)
    return existed


def rebuild_collection(
    collection: str,
    sources: list[str],
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Rebuild a collection from source paths."""

    delete_collection(collection, settings)
    notes = load_sources(sources)
    add_documents_to_index(notes, collection_name=collection, settings=settings)
    return get_collection_stats(collection, settings)


def export_collection_manifest(
    collection: str,
    output_path: Path | str,
    settings: Settings | None = None,
) -> Path:
    """Export a manifest to a user-selected path."""

    manifest = load_manifest(collection, settings)
    if manifest is None:
        raise FileNotFoundError(f"No manifest found for collection: {collection}")
    resolved = Path(output_path)
    resolved.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return resolved
