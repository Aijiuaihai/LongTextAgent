from writing_agent.models import DocumentChunk
from writing_agent.rag.retriever import retrieve


def test_retrieve_ranks_term_overlap() -> None:
    chunks = [
        DocumentChunk(
            source_path="a.md",
            chunk_id="a.md#chunk-1",
            title="Budget",
            text="cost budget procurement",
        ),
        DocumentChunk(
            source_path="b.md",
            chunk_id="b.md#chunk-1",
            title="Forestry Sensors",
            text="forest patrol sensor deployment",
        ),
    ]

    results = retrieve("sensor deployment plan", chunks, top_k=1)

    assert results[0].chunk_id == "b.md#chunk-1"
