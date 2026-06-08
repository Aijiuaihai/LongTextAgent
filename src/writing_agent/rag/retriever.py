"""Simple term-overlap retriever."""

import re
from collections import Counter

from writing_agent.models import DocumentChunk


def _terms(text: str) -> list[str]:
    return re.findall(r"[\w\u4e00-\u9fff]+", text.lower())


def _score(query_terms: Counter[str], chunk: DocumentChunk) -> float:
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
    query_terms = Counter(_terms(query))
    scored = [(_score(query_terms, chunk), index, chunk) for index, chunk in enumerate(chunks)]
    scored = [item for item in scored if item[0] > 0]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [chunk for _, _, chunk in scored[:top_k]]
