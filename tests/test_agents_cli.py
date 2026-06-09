from typer.testing import CliRunner

from writing_agent import cli


def test_agents_cli_list_and_inspect() -> None:
    runner = CliRunner()

    listed = runner.invoke(cli.app, ["agents", "list"])
    inspected = runner.invoke(cli.app, ["agents", "inspect", "--agent", "writer"])

    assert listed.exit_code == 0
    assert "writer" in listed.output
    assert inspected.exit_code == 0
    assert "forbidden_actions" in inspected.output


def test_agents_cli_trace(monkeypatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        cli,
        "inspect_thread",
        lambda thread_id, settings=None: {
            "thread_id": thread_id,
            "agent_results": [
                {"agent_name": "planner", "status": "success", "duration_seconds": 0.1}
            ],
            "supervisor_decisions": [{"decision": "format"}],
        },
    )

    result = runner.invoke(cli.app, ["agents", "trace", "--thread-id", "demo"])

    assert result.exit_code == 0
    assert "planner" in result.output
