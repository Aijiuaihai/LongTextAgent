from writing_agent.config import Settings
from writing_agent.rag.collections import (
    delete_collection,
    export_collection_manifest,
    get_collection_stats,
    list_collections,
)
from writing_agent.rag.manifest import save_index_manifest


def test_collection_management_from_manifest(tmp_path) -> None:
    settings = Settings(output_dir=tmp_path / "outputs")
    manifest = {
        "collection_name": "demo",
        "updated_at": "now",
        "source_count": 1,
        "chunk_count": 2,
        "embedding_provider": "ollama",
        "embedding_model": "bge-m3",
        "sources": [],
        "chunks": [],
    }
    save_index_manifest(manifest, settings=settings)

    assert list_collections(settings)[0]["collection_name"] == "demo"
    assert get_collection_stats("demo", settings)["chunk_count"] == 2
    exported = export_collection_manifest("demo", tmp_path / "manifest.json", settings)
    assert exported.exists()
    assert delete_collection("demo", settings) is True
    assert get_collection_stats("demo", settings)["exists"] is False
