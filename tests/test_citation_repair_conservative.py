from writing_agent.verification.repair import INSUFFICIENT_NOTE, repair_citations_in_file


def test_conservative_repair_downgrades_invalid_citation(tmp_path) -> None:
    markdown = tmp_path / "doc.md"
    markdown.write_text(
        "## Section\n\n### 参考依据\n\n- [source: data/a.md#fake]",
        encoding="utf-8",
    )
    manifest = {
        "sources": [{"source_path": "data/a.md"}],
        "chunks": [{"chunk_id": "data/a.md#chunk-1", "source_path": "data/a.md"}],
    }

    result = repair_citations_in_file(
        markdown,
        index_manifest=manifest,
        mode="conservative",
    )

    assert result.downgraded_count == 1
    assert result.replaced_count == 0
    assert INSUFFICIENT_NOTE in result.repaired_text
    assert result.after is not None
    assert result.after.invalid_citations == 0

