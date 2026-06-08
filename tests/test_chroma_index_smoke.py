from writing_agent.models import SourceNote
from writing_agent.rag import vector_index


def test_build_chroma_index_uses_fake_vector_store(tmp_path, monkeypatch) -> None:
    added = {}

    class FakeDocument:
        def __init__(self, page_content, metadata) -> None:
            self.page_content = page_content
            self.metadata = metadata

    class FakeChroma:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        def add_documents(self, documents, ids) -> None:
            added["documents"] = documents
            added["ids"] = ids

    monkeypatch.setattr(vector_index, "_get_chroma_class", lambda: FakeChroma)
    monkeypatch.setattr(vector_index, "_get_document_class", lambda: FakeDocument)
    monkeypatch.setattr(vector_index, "get_embedding_model", lambda settings=None: object())

    notes = [
        SourceNote(
            path="source.md",
            title="Source",
            content_preview="forest sensors",
            full_text="forest sensors\n\nknowledge base construction",
        )
    ]

    vector_index.build_chroma_index(notes, "test_collection", tmp_path)

    assert added["ids"]
    assert added["documents"][0].metadata["source_path"] == "source.md"

