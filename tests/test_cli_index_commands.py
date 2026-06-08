from typer.testing import CliRunner

from writing_agent import cli
from writing_agent.models import SourceNote


def test_cli_index_command_uses_loader_and_indexer(monkeypatch) -> None:
    runner = CliRunner()
    indexed = {}

    monkeypatch.setattr(
        cli,
        "load_sources",
        lambda paths: [
            SourceNote(path=paths[0], title="Source", content_preview="preview", full_text="text")
        ],
    )
    monkeypatch.setattr(cli, "reset_chroma_index", lambda collection, settings=None: None)

    def fake_add(notes, collection_name, settings=None):
        indexed["count"] = len(notes)
        indexed["collection"] = collection_name

    monkeypatch.setattr(cli, "add_documents_to_index", fake_add)

    result = runner.invoke(
        cli.app,
        ["index", "--source", "source.md", "--collection", "demo", "--reset"],
    )

    assert result.exit_code == 0
    assert indexed == {"count": 1, "collection": "demo"}
