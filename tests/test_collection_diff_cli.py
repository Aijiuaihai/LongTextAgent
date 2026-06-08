import json

from typer.testing import CliRunner

from writing_agent import cli


def test_collections_diff_cli_json(tmp_path) -> None:
    runner = CliRunner()
    old = tmp_path / "old.json"
    new = tmp_path / "new.json"
    old.write_text(
        json.dumps({"collection_name": "old", "sources": [], "chunks": []}),
        encoding="utf-8",
    )
    new.write_text(
        json.dumps({"collection_name": "new", "sources": [], "chunks": []}),
        encoding="utf-8",
    )

    result = runner.invoke(
        cli.app,
        [
            "collections",
            "diff",
            "--old-manifest",
            str(old),
            "--new-manifest",
            str(new),
            "--json",
        ],
    )

    assert result.exit_code == 0
    assert '"old_collection": "old"' in result.output
