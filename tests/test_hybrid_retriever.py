from writing_agent.rag.models import DocumentChunk, RetrievalResult
from writing_agent.rag.retriever import HybridRetriever


def test_hybrid_retriever_fuses_vector_and_keyword_scores() -> None:
    class FakeVectorRetriever:
        def retrieve(self, query, top_k=5):
            return [
                RetrievalResult(
                    chunk_id="a#chunk-1",
                    source_path="a",
                    score=1.0,
                    text="vector result",
                    metadata={},
                )
            ]

    chunks = [
        DocumentChunk(
            chunk_id="b#chunk-1",
            source_path="b",
            title="Sensors",
            text="sensor deployment plan",
            metadata={},
        )
    ]

    results = HybridRetriever(
        vector_retriever=FakeVectorRetriever(),
        keyword_chunks=chunks,
    ).retrieve("sensor deployment", top_k=2)

    assert {result.chunk_id for result in results} == {"a#chunk-1", "b#chunk-1"}

