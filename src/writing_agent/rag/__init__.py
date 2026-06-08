"""Minimal local retrieval components."""

from writing_agent.rag.chunker import simple_chunk_text
from writing_agent.rag.index import build_local_index
from writing_agent.rag.retriever import retrieve

__all__ = ["build_local_index", "retrieve", "simple_chunk_text"]

