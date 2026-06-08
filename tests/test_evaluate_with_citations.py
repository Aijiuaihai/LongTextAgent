from pathlib import Path

from writing_agent.evaluation.evaluator import evaluate_markdown
from writing_agent.verification.verifier import verify_citations_in_file


def test_evaluate_can_be_augmented_with_citation_metrics(tmp_path) -> None:
    file_path = tmp_path / "doc.md"
    file_path.write_text(
        "# Demo\n\n## Section\n\n### 参考依据\n\n- [source: data/a.md#data/a.md#chunk-1]",
        encoding="utf-8",
    )
    manifest = {
        "sources": [{"source_path": "data/a.md"}],
        "chunks": [{"chunk_id": "data/a.md#chunk-1", "source_path": "data/a.md"}],
    }

    metrics = evaluate_markdown(Path(file_path))
    citation_result = verify_citations_in_file(file_path, index_manifest=manifest)
    metrics["citation_valid"] = citation_result.valid_citations

    assert metrics["citation_valid"] == 1
