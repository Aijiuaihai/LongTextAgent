"""Typer CLI entrypoint."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from writing_agent.config import get_settings
from writing_agent.graph.workflow import run_writing_workflow
from writing_agent.llm import format_connection_help, get_chat_model
from writing_agent.models import DocumentType, WritingRequest

app = typer.Typer(help="Long-form writing agent CLI.", no_args_is_help=True)
console = Console()


FORESTRY_EXAMPLE = """# Forestry Report Request

Topic: 智慧林务系统建设计划书
Audience: 项目负责人和技术评审
Target length: 5000字
Style: 正式、技术导向、少空话

Constraints:
- 聚焦系统建设目标、技术路线、风险控制和实施计划
- 对缺少依据的数据明确标注依据不足
"""

PROJECT_PLAN_EXAMPLE = """# Project Plan Request

Topic: AI-assisted long-form document writing agent
Audience: engineering leads and product stakeholders
Target length: 4000 words
Style: practical, technical, roadmap-oriented

Constraints:
- Include staged workflow design
- Identify risks and future RAG extension points
"""


@app.command()
def run(
    topic: Annotated[str, typer.Option("--topic", help="Writing topic.")],
    document_type: Annotated[
        DocumentType,
        typer.Option("--type", help="Document type."),
    ] = DocumentType.REPORT,
    audience: Annotated[str, typer.Option("--audience", help="Target audience.")] = (
        "general readers"
    ),
    length: Annotated[str, typer.Option("--length", help="Target document length.")] = (
        "3000 words"
    ),
    style: Annotated[str, typer.Option("--style", help="Writing style.")] = "formal",
    source: Annotated[
        list[str] | None,
        typer.Option("--source", help="Local source path. Can be repeated."),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option("--output-format", help="markdown or docx."),
    ] = "markdown",
    pause_after_outline: Annotated[
        bool,
        typer.Option("--pause-after-outline", help="Pause after outline planning."),
    ] = False,
    pause_before_export: Annotated[
        bool,
        typer.Option("--pause-before-export", help="Pause after final draft assembly."),
    ] = False,
) -> None:
    """Run the long-form writing workflow."""

    settings = get_settings()
    request = WritingRequest(
        topic=topic,
        document_type=document_type,
        audience=audience,
        target_length=length,
        style=style,
        source_paths=source or [],
    )
    console.print("[bold]Starting writing workflow[/bold]")
    result = run_writing_workflow(
        {
            "request": request,
            "output_format": output_format,
            "output_dir": str(settings.output_dir),
            "pause_after_outline": pause_after_outline,
            "pause_before_export": pause_before_export,
        },
        settings=settings,
    )
    for error in result.get("errors", []):
        console.print(f"[yellow]Warning:[/yellow] {error}")
    if result.get("awaiting_human_review"):
        console.print(f"[yellow]Paused for human review at:[/yellow] {result.get('current_step')}")
    else:
        console.print(f"[green]Exported:[/green] {result.get('output_path')}")


@app.command("init-example")
def init_example(
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite existing example files."),
    ] = False,
) -> None:
    """Create example request files."""

    examples_dir = Path("examples")
    examples_dir.mkdir(parents=True, exist_ok=True)
    files = {
        examples_dir / "forestry_report_request.md": FORESTRY_EXAMPLE,
        examples_dir / "project_plan_request.md": PROJECT_PLAN_EXAMPLE,
    }
    for path, content in files.items():
        if path.exists() and not force:
            console.print(f"[yellow]Skipped existing:[/yellow] {path}")
            continue
        path.write_text(content, encoding="utf-8")
        console.print(f"[green]Wrote:[/green] {path}")


@app.command("check-model")
def check_model() -> None:
    """Check whether the configured model responds."""

    settings = get_settings()
    console.print("[bold]Configuration[/bold]")
    console.print(settings.safe_summary())
    try:
        model = get_chat_model(settings)
        response = model.invoke("Reply with a short readiness confirmation.")
        content = getattr(response, "content", response)
    except Exception as exc:
        console.print(f"[red]Model check failed:[/red] {exc}")
        console.print(format_connection_help(settings))
        raise typer.Exit(code=1) from exc
    console.print("[green]Model responded.[/green]")
    console.print(str(content)[:500])


if __name__ == "__main__":
    app()
