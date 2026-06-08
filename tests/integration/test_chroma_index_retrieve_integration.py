import os

import pytest

from writing_agent.config import Settings
from writing_agent.models import SourceNote
from writing_agent.rag.retriever import VectorRetriever
from writing_agent.rag.vector_index import build_chroma_index

pytestmark = [pytest.mark.integration, pytest.mark.chroma]


class FakeEmbeddings:
    def embed_documents(self, texts):
        return [[float(len(text) % 10), 1.0, 0.0] for text in texts]

    def embed_query(self, text):
        return [float(len(text) % 10), 1.0, 0.0]


def _enabled(name: str) -> bool:
    return os.getenv(name, "").lower() == "true"


def test_chroma_index_retrieves_from_temp_persistence(tmp_path) -> None:
    if not (_enabled("RUN_INTEGRATION_TESTS") and _enabled("RUN_CHROMA_TESTS")):
        pytest.skip("Set RUN_INTEGRATION_TESTS=true and RUN_CHROMA_TESTS=true.")

    settings = Settings(output_dir=tmp_path / "outputs")
    notes = [
        SourceNote(
            path="data/source.md",
            title="Source",
            content_preview="knowledge base",
            full_text="林业知识库需要结构化资料、检索索引和问答评估。",
        )
    ]

    vector_store = build_chroma_index(
        notes,
        collection_name="integration_demo",
        persist_dir=tmp_path / "chroma",
        settings=settings,
        embedding_model=FakeEmbeddings(),
    )
    results = VectorRetriever(vector_store).retrieve("知识库 检索", top_k=1)

    assert results
    assert results[0].source_path == "data/source.md"
