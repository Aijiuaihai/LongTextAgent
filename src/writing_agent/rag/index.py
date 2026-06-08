"""Minimal in-memory local source index."""

import json
from pathlib import Path

from writing_agent.models import SourceNote
from writing_agent.rag.chunker import simple_chunk_text
from writing_agent.rag.models import DocumentChunk


def build_local_index(
    source_notes: list[SourceNote],
    *,
    chunk_size: int = 1200,
    overlap: int = 150,
    save_path: Path | None = None,
) -> list[DocumentChunk]:
    """Build a local in-memory chunk index from source notes."""

    chunks: list[DocumentChunk] = []
    for note in source_notes:
        chunks.extend(
            simple_chunk_text(
                note.full_text,
                source_path=note.path,
                title=note.title,
                chunk_size=chunk_size,
                overlap=overlap,
                metadata={"source_title": note.title},
            )
        )

    if save_path is not None:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_text(
            json.dumps([chunk.model_dump(mode="json") for chunk in chunks], ensure_ascii=False),
            encoding="utf-8",
        )
    return chunks
