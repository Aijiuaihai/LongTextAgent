"""RAG data models."""

from typing import Any

from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    """A chunk of source text ready for retrieval."""

    chunk_id: str
    source_path: str
    title: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    """A normalized retrieval result."""

    chunk_id: str
    source_path: str
    score: float
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
