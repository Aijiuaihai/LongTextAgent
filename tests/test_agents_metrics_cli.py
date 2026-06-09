from typer.testing import CliRunner

from writing_agent import cli
from writing_agent.config import Settings


def test_agents_metrics_cli_json(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        cli,
        "get_settings",
        lambda: Settings(output_dir=tmp_path / "outputs"),
    )
    monkeypatch.setattr(
        cli,
        "inspect_thread",
        lambda thread_id, settings: {
            "thread_id": thread_id,
            "mode": "multi",
            "agent_metrics": {
                "thread_id": thread_id,
                "mode": "multi",
                "total_agents_run": 2,
                "total_duration_seconds": 1.0,
                "total_errors": 0,
                "total_warnings": 1,
                "researcher": {"retrieved_chunks": 3},
                "planner": {},
                "writer": {},
                "citation_auditor": {},
                "reviewer": {},
                "editor": {},
                "formatter": {},
                "evaluator": {},
                "supervisor": {},
            },
        },
    )

    result = CliRunner().invoke(
        cli.app,
        ["agents", "metrics", "--thread-id", "thread-1", "--json"],
    )

    assert result.exit_code == 0
    assert '"total_agents_run": 2' in result.output
