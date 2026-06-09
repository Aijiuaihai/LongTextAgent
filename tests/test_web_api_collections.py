from fastapi.testclient import TestClient

from writing_agent.config import Settings
from writing_agent.rag.models import RetrievalResult
from writing_agent.web import app as web_app
from writing_agent.web.app import create_app


class FakeRetriever:
    def __init__(self, _store):
        pass

    def retrieve(self, _query, top_k=5):
        return [
            RetrievalResult(
                chunk_id="source.md#chunk-1",
                source_path="source.md",
                score=1.0,
                text="text",
                metadata={},
            )
        ][:top_k]


def test_collections_api_uses_collection_helpers(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        web_app.collections,
        "list_collections",
        lambda settings=None: [{"collection_name": "demo", "source_count": 1, "chunk_count": 2}],
    )
    monkeypatch.setattr(
        web_app.collections,
        "rebuild_collection",
        lambda collection, sources, settings=None: {"collection_name": collection, "exists": True},
    )
    monkeypatch.setattr(web_app.collections, "load_chroma_index", lambda **kwargs: object())
    monkeypatch.setattr(web_app.collections, "VectorRetriever", FakeRetriever)
    client = TestClient(
        create_app(Settings(output_dir=tmp_path / "outputs", data_dir=tmp_path / "data"))
    )

    assert client.get("/api/collections").json()[0]["collection_name"] == "demo"
    assert client.post(
        "/api/collections",
        json={"collection": "demo", "source_paths": ["data/source.md"], "reset": True},
    ).json()["exists"]
    assert client.post(
        "/api/collections/demo/retrieve",
        json={"query": "knowledge", "top_k": 1},
    ).json()[0]["chunk_id"] == "source.md#chunk-1"

