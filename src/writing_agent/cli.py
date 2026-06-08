"""Typer CLI entrypoint."""

import typer
from rich.console import Console

from writing_agent.config import get_settings

app = typer.Typer(help="Long-form writing agent CLI.")
console = Console()


@app.command()
def check_model() -> None:
    """Show the current model configuration."""

    settings = get_settings()
    console.print(settings.safe_summary())


if __name__ == "__main__":
    app()

