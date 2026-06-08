"""Paragraph-oriented text chunking for local sources."""

from datetime import datetime, timezone
from typing import Any

from writing_agent.rag.models import DocumentChunk


def _blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n")
    raw_blocks: list[str] = []
    current: list[str] = []
    for line in normalized.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            if current:
                raw_blocks.append("\n".join(current).strip())
                current = []
            raw_blocks.append(stripped)
            continue
        if not stripped:
            if current:
                raw_blocks.append("\n".join(current).strip())
                current = []
            continue
        current.append(stripped)
    if current:
        raw_blocks.append("\n".join(current).strip())
    return [block for block in raw_blocks if block]


def _chunk_id(source_path: str, index: int) -> str:
    prefix = source_path or "source"
    return f"{prefix}#chunk-{index}"


def _metadata(
    *,
    source_path: str,
    title: str,
    chunk_index: int,
    document_type: str | None,
    extra: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata = {
        "source_path": source_path,
        "chunk_index": chunk_index,
        "title": title,
        "document_type": document_type or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        metadata.update(extra)
    return metadata


def simple_chunk_text(
    text: str,
    *,
    source_path: str = "",
    title: str = "",
    chunk_size: int = 1200,
    overlap: int = 150,
    document_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> list[DocumentChunk]:
    """Split text into heading/paragraph-first chunks with light overlap."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")

    chunks: list[DocumentChunk] = []
    current = ""
    for block in _blocks(text):
        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunk_index = len(chunks) + 1
            chunks.append(
                DocumentChunk(
                    source_path=source_path,
                    chunk_id=_chunk_id(source_path, chunk_index),
                    title=title,
                    text=current,
                    metadata=_metadata(
                        source_path=source_path,
                        title=title,
                        chunk_index=chunk_index,
                        document_type=document_type,
                        extra=metadata,
                    ),
                )
            )
        if len(block) > chunk_size:
            start = 0
            while start < len(block):
                end = min(start + chunk_size, len(block))
                chunk_index = len(chunks) + 1
                chunks.append(
                    DocumentChunk(
                        source_path=source_path,
                        chunk_id=_chunk_id(source_path, chunk_index),
                        title=title,
                        text=block[start:end],
                        metadata=_metadata(
                            source_path=source_path,
                            title=title,
                            chunk_index=chunk_index,
                            document_type=document_type,
                            extra=metadata,
                        ),
                    )
                )
                if end == len(block):
                    break
                start = max(end - overlap, start + 1)
            current = ""
        else:
            current = block[-overlap:] if chunks and overlap else block

    if current:
        chunk_index = len(chunks) + 1
        chunks.append(
            DocumentChunk(
                source_path=source_path,
                chunk_id=_chunk_id(source_path, chunk_index),
                title=title,
                text=current,
                metadata=_metadata(
                    source_path=source_path,
                    title=title,
                    chunk_index=chunk_index,
                    document_type=document_type,
                    extra=metadata,
                ),
            )
        )
    return chunks
