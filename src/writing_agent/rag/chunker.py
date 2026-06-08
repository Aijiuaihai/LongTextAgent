"""Paragraph-oriented text chunking for local sources."""

from writing_agent.models import DocumentChunk


def _paragraphs(text: str) -> list[str]:
    blocks = [block.strip() for block in text.replace("\r\n", "\n").split("\n\n")]
    return [block for block in blocks if block]


def simple_chunk_text(
    text: str,
    *,
    source_path: str = "",
    title: str = "",
    chunk_size: int = 1200,
    overlap: int = 150,
) -> list[DocumentChunk]:
    """Split text into paragraph-first chunks with light overlap."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0:
        raise ValueError("overlap must be non-negative")

    chunks: list[DocumentChunk] = []
    current = ""
    for paragraph in _paragraphs(text):
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(
                DocumentChunk(
                    source_path=source_path,
                    chunk_id=f"{source_path}#chunk-{len(chunks) + 1}",
                    title=title,
                    text=current,
                )
            )
        if len(paragraph) > chunk_size:
            start = 0
            while start < len(paragraph):
                end = min(start + chunk_size, len(paragraph))
                chunks.append(
                    DocumentChunk(
                        source_path=source_path,
                        chunk_id=f"{source_path}#chunk-{len(chunks) + 1}",
                        title=title,
                        text=paragraph[start:end],
                    )
                )
                if end == len(paragraph):
                    break
                start = max(end - overlap, start + 1)
            current = ""
        else:
            current = paragraph[-overlap:] if chunks and overlap else paragraph

    if current:
        chunks.append(
            DocumentChunk(
                source_path=source_path,
                chunk_id=f"{source_path}#chunk-{len(chunks) + 1}",
                title=title,
                text=current,
            )
        )
    return chunks

