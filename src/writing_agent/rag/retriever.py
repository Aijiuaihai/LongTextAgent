"""Simple term-overlap retriever."""

import re
from collections import Counter

from writing_agent.rag.models import DocumentChunk, RetrievalResult


def _terms(text: str) -> list[str]:
    return re.findall(r"[\w\u4e00-\u9fff]+", text.lower())


def keyword_score(query: str, chunk: DocumentChunk) -> float:
    """Score a chunk with simple term overlap."""

    query_terms = Counter(_terms(query))
    chunk_terms = Counter(_terms(chunk.text))
    if not query_terms or not chunk_terms:
        return 0.0
    overlap = sum(min(count, chunk_terms.get(term, 0)) for term, count in query_terms.items())
    title_bonus = sum(1 for term in query_terms if term in chunk.title.lower()) * 0.5
    return overlap + title_bonus


def retrieve(
    query: str,
    chunks: list[DocumentChunk],
    *,
    top_k: int = 5,
) -> list[DocumentChunk]:
    """Return top matching chunks by simple term overlap."""

    if top_k <= 0:
        return []
    scored = [(keyword_score(query, chunk), index, chunk) for index, chunk in enumerate(chunks)]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [chunk for _, _, chunk in scored[:top_k]]


class VectorRetriever:
    """Retriever backed by a Chroma vector store."""

    def __init__(self, vector_store: object) -> None:
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Retrieve normalized vector results."""

        if top_k <= 0:
            return []
        results = self.vector_store.similarity_search_with_relevance_scores(query, k=top_k)
        normalized: list[RetrievalResult] = []
        for document, score in results:
            metadata = dict(document.metadata or {})
            normalized.append(
                RetrievalResult(
                    chunk_id=str(metadata.get("chunk_id", "")),
                    source_path=str(metadata.get("source_path", "")),
                    score=float(score),
                    text=document.page_content,
                    metadata=metadata,
                )
            )
        return normalized


class HybridRetriever:
    """Hybrid retriever combining vector and keyword scores."""

    def __init__(
        self,
        *,
        vector_retriever: VectorRetriever | None = None,
        keyword_chunks: list[DocumentChunk] | None = None,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
    ) -> None:
        self.vector_retriever = vector_retriever
        self.keyword_chunks = keyword_chunks or []
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Retrieve with simple weighted score fusion."""

        fused: dict[str, RetrievalResult] = {}
        if self.vector_retriever is not None:
            for result in self.vector_retriever.retrieve(query, top_k=top_k):
                result.score *= self.vector_weight
                fused[result.chunk_id] = result

        keyword_scored = [
            (keyword_score(query, chunk), index, chunk)
            for index, chunk in enumerate(self.keyword_chunks)
        ]
        keyword_scored = [item for item in keyword_scored if item[0] > 0]
        max_keyword = max((score for score, _, _ in keyword_scored), default=1.0)
        for score, _, chunk in keyword_scored:
            normalized_score = (score / max_keyword) * self.keyword_weight
            existing = fused.get(chunk.chunk_id)
            if existing is None:
                fused[chunk.chunk_id] = RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    source_path=chunk.source_path,
                    score=normalized_score,
                    text=chunk.text,
                    metadata=chunk.metadata,
                )
            else:
                existing.score += normalized_score

        return sorted(fused.values(), key=lambda item: item.score, reverse=True)[:top_k]
