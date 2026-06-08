import json

from writing_agent.rag.diff import diff_manifests, summarize_manifest_diff


def test_diff_manifests_reports_source_and_chunk_changes(tmp_path) -> None:
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    old.write_text(
        json.dumps(
            {
                "collection_name": "old",
                "sources": [
                    {
                        "source_path": "data/a.md",
                        "content_hash": "old-hash",
                        "chunk_count": 1,
                    }
                ],
                "chunks": [
                    {
                        "source_path": "data/a.md",
                        "chunk_id": "data/a.md#chunk-1",
                        "text_hash": "old-chunk",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    new.write_text(
        json.dumps(
            {
                "collection_name": "new",
                "sources": [
                    {
                        "source_path": "data/a.md",
                        "content_hash": "new-hash",
                        "chunk_count": 1,
                    },
                    {
                        "source_path": "data/b.md",
                        "content_hash": "b-hash",
                        "chunk_count": 1,
                    },
                ],
                "chunks": [
                    {
                        "source_path": "data/a.md",
                        "chunk_id": "data/a.md#chunk-1",
                        "text_hash": "new-chunk",
                    },
                    {
                        "source_path": "data/b.md",
                        "chunk_id": "data/b.md#chunk-1",
                        "text_hash": "b-chunk",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = diff_manifests(old, new)
    summary = summarize_manifest_diff(result)

    assert result.source_added == 1
    assert result.source_changed == 1
    assert result.chunk_added == 1
    assert result.chunk_changed == 1
    assert summary["warnings"]

