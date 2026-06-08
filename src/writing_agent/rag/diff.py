"""Diff utilities for collection manifests."""

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from writing_agent.config import Settings
from writing_agent.rag.manifest import manifest_path


class SourceDiff(BaseModel):
    """Diff entry for one source document."""

    source_path: str
    status: Literal["added", "removed", "changed", "unchanged"]
    old_hash: str = ""
    new_hash: str = ""
    old_chunk_count: int = 0
    new_chunk_count: int = 0


class ChunkDiff(BaseModel):
    """Diff entry for one chunk."""

    chunk_id: str
    source_path: str
    status: Literal["added", "removed", "changed", "unchanged"]
    old_hash: str = ""
    new_hash: str = ""


class ManifestDiffResult(BaseModel):
    """Diff summary for two manifests."""

    old_collection: str
    new_collection: str
    source_added: int = 0
    source_removed: int = 0
    source_changed: int = 0
    chunk_added: int = 0
    chunk_removed: int = 0
    chunk_changed: int = 0
    source_diffs: list[SourceDiff] = Field(default_factory=list)
    chunk_diffs: list[ChunkDiff] = Field(default_factory=list)


def _load_manifest(path: Path | str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _source_key(source: dict[str, Any]) -> str:
    return str(source.get("source_path", ""))


def _chunk_key(chunk: dict[str, Any]) -> tuple[str, str]:
    return str(chunk.get("source_path", "")), str(chunk.get("chunk_id", ""))


def _diff_sources(old_manifest: dict[str, Any], new_manifest: dict[str, Any]) -> list[SourceDiff]:
    old_sources = {_source_key(source): source for source in old_manifest.get("sources", [])}
    new_sources = {_source_key(source): source for source in new_manifest.get("sources", [])}
    diffs: list[SourceDiff] = []
    for source_path in sorted(set(old_sources) | set(new_sources)):
        old = old_sources.get(source_path)
        new = new_sources.get(source_path)
        if old is None:
            status: Literal["added", "removed", "changed", "unchanged"] = "added"
        elif new is None:
            status = "removed"
        elif old.get("content_hash") != new.get("content_hash"):
            status = "changed"
        else:
            status = "unchanged"
        diffs.append(
            SourceDiff(
                source_path=source_path,
                status=status,
                old_hash=str((old or {}).get("content_hash", "")),
                new_hash=str((new or {}).get("content_hash", "")),
                old_chunk_count=int((old or {}).get("chunk_count", 0) or 0),
                new_chunk_count=int((new or {}).get("chunk_count", 0) or 0),
            )
        )
    return diffs


def _diff_chunks(old_manifest: dict[str, Any], new_manifest: dict[str, Any]) -> list[ChunkDiff]:
    old_chunks = {_chunk_key(chunk): chunk for chunk in old_manifest.get("chunks", [])}
    new_chunks = {_chunk_key(chunk): chunk for chunk in new_manifest.get("chunks", [])}
    diffs: list[ChunkDiff] = []
    for key in sorted(set(old_chunks) | set(new_chunks)):
        old = old_chunks.get(key)
        new = new_chunks.get(key)
        if old is None:
            status: Literal["added", "removed", "changed", "unchanged"] = "added"
        elif new is None:
            status = "removed"
        elif old.get("text_hash") != new.get("text_hash"):
            status = "changed"
        else:
            status = "unchanged"
        source_path, chunk_id = key
        diffs.append(
            ChunkDiff(
                chunk_id=chunk_id,
                source_path=source_path,
                status=status,
                old_hash=str((old or {}).get("text_hash", "")),
                new_hash=str((new or {}).get("text_hash", "")),
            )
        )
    return diffs


def diff_manifests(
    old_manifest_path: Path | str,
    new_manifest_path: Path | str,
) -> ManifestDiffResult:
    """Diff two manifest JSON files."""

    old_manifest = _load_manifest(old_manifest_path)
    new_manifest = _load_manifest(new_manifest_path)
    source_diffs = _diff_sources(old_manifest, new_manifest)
    chunk_diffs = _diff_chunks(old_manifest, new_manifest)
    return ManifestDiffResult(
        old_collection=str(old_manifest.get("collection_name", "")),
        new_collection=str(new_manifest.get("collection_name", "")),
        source_added=sum(1 for item in source_diffs if item.status == "added"),
        source_removed=sum(1 for item in source_diffs if item.status == "removed"),
        source_changed=sum(1 for item in source_diffs if item.status == "changed"),
        chunk_added=sum(1 for item in chunk_diffs if item.status == "added"),
        chunk_removed=sum(1 for item in chunk_diffs if item.status == "removed"),
        chunk_changed=sum(1 for item in chunk_diffs if item.status == "changed"),
        source_diffs=source_diffs,
        chunk_diffs=chunk_diffs,
    )


def diff_collections(
    old_collection: str,
    new_collection: str,
    settings: Settings | None = None,
) -> ManifestDiffResult:
    """Diff two persisted collection manifests."""

    return diff_manifests(
        manifest_path(old_collection, settings),
        manifest_path(new_collection, settings),
    )


def summarize_manifest_diff(diff_result: ManifestDiffResult) -> dict[str, Any]:
    """Summarize diff counts and operational risk hints."""

    warnings: list[str] = []
    if diff_result.chunk_removed > 0:
        warnings.append(
            "Many removed chunks can invalidate citations in older generated documents."
        )
    if diff_result.source_changed > 0:
        warnings.append("Changed sources should trigger a fresh baseline-run.")
    return {
        "old_collection": diff_result.old_collection,
        "new_collection": diff_result.new_collection,
        "source_added": diff_result.source_added,
        "source_removed": diff_result.source_removed,
        "source_changed": diff_result.source_changed,
        "chunk_added": diff_result.chunk_added,
        "chunk_removed": diff_result.chunk_removed,
        "chunk_changed": diff_result.chunk_changed,
        "warnings": warnings,
    }
