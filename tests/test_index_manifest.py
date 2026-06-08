from writing_agent.config import Settings
from writing_agent.models import SourceNote
from writing_agent.rag.manifest import build_index_manifest, load_manifest, save_index_manifest
from writing_agent.rag.vector_index import source_notes_to_chunks


def test_index_manifest_round_trip(tmp_path) -> None:
    settings = Settings(output_dir=tmp_path / "outputs")
    notes = [
        SourceNote(path="data/a.md", title="A", content_preview="preview", full_text="text")
    ]
    chunks = source_notes_to_chunks(notes)

    manifest = build_index_manifest(
        collection_name="demo",
        source_notes=notes,
        chunks=chunks,
        settings=settings,
    )
    save_index_manifest(manifest, settings=settings)
    loaded = load_manifest("demo", settings)

    assert loaded is not None
    assert loaded["collection_name"] == "demo"
    assert loaded["chunk_count"] == len(chunks)

