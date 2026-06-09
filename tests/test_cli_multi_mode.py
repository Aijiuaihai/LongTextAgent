from typer.testing import CliRunner

from writing_agent import cli


def test_cli_run_multi_mode_uses_multi_workflow(monkeypatch) -> None:
    runner = CliRunner()
    called = {}

    def fake_multi(initial_state, **kwargs):
        called["mode"] = initial_state["mode"]
        called["max_rounds"] = kwargs["max_rounds"]
        return {
            "output_path": "outputs/demo.md",
            "output_paths": {"markdown": "outputs/demo.md"},
            "agent_results": [{"agent_name": "planner", "status": "success"}],
        }

    monkeypatch.setattr(cli, "run_multi_agent_workflow", fake_multi)

    result = runner.invoke(
        cli.app,
        [
            "run",
            "--topic",
            "Demo",
            "--mode",
            "multi",
            "--max-agent-rounds",
            "2",
            "--no-agent-debug",
        ],
    )

    assert result.exit_code == 0
    assert called == {"mode": "multi", "max_rounds": 2}

