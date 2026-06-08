from writing_agent.rag.chunker import simple_chunk_text


def test_simple_chunk_text_preserves_source_metadata() -> None:
    text = "Paragraph one about forestry.\n\nParagraph two about sensors and patrols."

    chunks = simple_chunk_text(text, source_path="source.md", title="Source", chunk_size=40)

    assert chunks
    assert chunks[0].source_path == "source.md"
    assert chunks[0].chunk_id.startswith("source.md#chunk-")
    assert any("forestry" in chunk.text for chunk in chunks)
