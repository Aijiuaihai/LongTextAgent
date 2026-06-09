from writing_agent.config import Settings
from writing_agent.graph.multi_agent_workflow import run_multi_agent_workflow
from writing_agent.models import WritingRequest


def test_multi_agent_workflow_smoke_exports_markdown(tmp_path) -> None:
    result = run_multi_agent_workflow(
        {
            "request": WritingRequest(topic="Multi Agent Demo"),
            "output_dir": str(tmp_path),
            "output_format": "markdown",
            "rag_enabled": False,
            "rag_top_k": 2,
        },
        settings=Settings(output_dir=tmp_path),
        checkpointer=False,
        thread_id="multi-smoke",
        max_rounds=1,
    )

    assert result["output_path"].endswith(".md")
    assert result["evaluation_result"]
    assert result["agent_results"]
