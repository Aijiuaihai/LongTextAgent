from pathlib import Path

from writing_agent.graph.workflow import run_writing_workflow
from writing_agent.models import WritingRequest


def test_workflow_smoke_exports_markdown(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path("outputs").mkdir()

    request = WritingRequest(
        topic="Smart forestry management proposal",
        document_type="proposal",
        audience="technical reviewers",
        target_length="3000 words",
        style="formal and concrete",
    )

    result = run_writing_workflow(request, checkpointer=False, use_llm=False)

    output_path = Path(result["output_path"])
    assert output_path.exists()
    assert "Smart forestry management proposal" in output_path.read_text(encoding="utf-8")
    assert result["current_step"] == "export_document"
