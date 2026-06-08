from writing_agent.verification.verifier import verify_citations_in_text


def test_verify_citations_against_manifest() -> None:
    manifest = {
        "sources": [{"source_path": "data/a.md"}],
        "chunks": [{"chunk_id": "data/a.md#chunk-1", "source_path": "data/a.md"}],
    }
    markdown = """# Demo

## Section A

### 参考依据

- [source: data/a.md#data/a.md#chunk-1]
"""

    result = verify_citations_in_text(markdown, index_manifest=manifest)

    assert result.total_citations == 1
    assert result.valid_citations == 1
    assert result.overall_status == "pass"


def test_verify_citations_flags_unknown_chunk() -> None:
    manifest = {"sources": [{"source_path": "data/a.md"}], "chunks": []}
    markdown = "## Section\n\n### 参考依据\n\n- [source: data/a.md#fake]"

    result = verify_citations_in_text(markdown, index_manifest=manifest)

    assert result.invalid_citations == 1
    assert result.fabricated_reference_count == 1
    assert result.overall_status == "fail"

