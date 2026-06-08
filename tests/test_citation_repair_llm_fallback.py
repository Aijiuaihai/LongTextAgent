from writing_agent.verification import repair
from writing_agent.verification.repair import INSUFFICIENT_NOTE, repair_citations_in_file


class BadModel:
    def invoke(self, _messages):
        return "not json"


def test_llm_repair_falls_back_to_conservative(tmp_path, monkeypatch) -> None:
    markdown = tmp_path / "doc.md"
    markdown.write_text(
        "## Section\n\n### 参考依据\n\n- [source: data/a.md#fake]",
        encoding="utf-8",
    )
    manifest = {
        "sources": [{"source_path": "data/a.md"}],
        "chunks": [{"chunk_id": "data/a.md#chunk-1", "source_path": "data/a.md"}],
    }
    monkeypatch.setattr(repair, "get_chat_model", lambda settings: BadModel())

    result = repair_citations_in_file(
        markdown,
        index_manifest=manifest,
        mode="llm_assisted",
    )

    assert result.downgraded_count == 1
    assert INSUFFICIENT_NOTE in result.repaired_text

