"""Chroma vector index helpers."""

import shutil
from pathlib import Path

from writing_agent.config import Settings, get_settings
from writing_agent.models import SourceNote
from writing_agent.rag.chunker import simple_chunk_text
from writing_agent.rag.embeddings import get_embedding_model
from writing_agent.rag.models import DocumentChunk

DEFAULT_COLLECTION = "writing_agent_sources"


def default_persist_dir(settings: Settings | None = None) -> Path:
    """Return the default Chroma persistence directory."""

    resolved = settings or get_settings()
    return resolved.output_dir / "chroma"


def _get_chroma_class() -> type[object]:
    try:
        from langchain_chroma import Chroma
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("Install langchain-chroma and chromadb to use vector RAG.") from exc
    return Chroma


def _get_document_class() -> type[object]:
    try:
        from langchain_core.documents import Document
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("Install langchain-core to build vector documents.") from exc
    return Document


def source_notes_to_chunks(source_notes: list[SourceNote]) -> list[DocumentChunk]:
    """Convert source notes into document chunks."""

    chunks: list[DocumentChunk] = []
    for note in source_notes:
        chunks.extend(
            simple_chunk_text(
                note.full_text,
                source_path=note.path,
                title=note.title,
                metadata={"source_title": note.title},
            )
        )
    return chunks


def _chunks_to_documents(chunks: list[DocumentChunk]) -> list[object]:
    Document = _get_document_class()
    documents = []
    for chunk in chunks:
        metadata = {
            **chunk.metadata,
            "chunk_id": chunk.chunk_id,
            "source_path": chunk.source_path,
            "title": chunk.title,
        }
        documents.append(Document(page_content=chunk.text, metadata=metadata))
    return documents


def load_chroma_index(
    collection_name: str = DEFAULT_COLLECTION,
    persist_dir: Path | str | None = None,
    *,
    settings: Settings | None = None,
    embedding_model: object | None = None,
) -> object:
    """Load a Chroma vector store."""

    Chroma = _get_chroma_class()
    resolved_dir = Path(persist_dir) if persist_dir is not None else default_persist_dir(settings)
    resolved_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=collection_name,
        persist_directory=str(resolved_dir),
        embedding_function=embedding_model or get_embedding_model(settings),
    )


def build_chroma_index(
    source_notes: list[SourceNote],
    collection_name: str = DEFAULT_COLLECTION,
    persist_dir: Path | str | None = None,
    *,
    settings: Settings | None = None,
    embedding_model: object | None = None,
) -> object:
    """Build a Chroma vector store from source notes."""

    chunks = source_notes_to_chunks(source_notes)
    vector_store = load_chroma_index(
        collection_name,
        persist_dir,
        settings=settings,
        embedding_model=embedding_model,
    )
    if chunks:
        vector_store.add_documents(
            _chunks_to_documents(chunks),
            ids=[chunk.chunk_id for chunk in chunks],
        )
    return vector_store


def add_documents_to_index(
    source_notes: list[SourceNote],
    collection_name: str = DEFAULT_COLLECTION,
    persist_dir: Path | str | None = None,
    *,
    settings: Settings | None = None,
    embedding_model: object | None = None,
) -> object:
    """Add source notes to an existing Chroma collection."""

    return build_chroma_index(
        source_notes,
        collection_name,
        persist_dir,
        settings=settings,
        embedding_model=embedding_model,
    )


def reset_chroma_index(
    collection_name: str = DEFAULT_COLLECTION,
    persist_dir: Path | str | None = None,
    *,
    settings: Settings | None = None,
) -> None:
    """Reset a local Chroma collection directory."""

    resolved_dir = Path(persist_dir) if persist_dir is not None else default_persist_dir(settings)
    collection_dir = resolved_dir / collection_name
    if collection_dir.exists():
        shutil.rmtree(collection_dir)
    # Chroma may store collections in shared sqlite files, so also delete the full
    # persistence directory when resetting the default local index.
    if resolved_dir.exists() and collection_name == DEFAULT_COLLECTION:
        shutil.rmtree(resolved_dir)
