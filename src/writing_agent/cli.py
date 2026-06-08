"""Typer CLI entrypoint."""

import json
import sys
import time
from pathlib import Path
from typing import Annotated
from urllib.error import URLError
from urllib.request import urlopen

import typer
from rich.console import Console
from rich.table import Table

from writing_agent.checkpoints import inspect_thread, list_threads
from writing_agent.config import get_settings
from writing_agent.graph.workflow import (
    generate_thread_id,
    resume_writing_workflow,
    run_writing_workflow,
)
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


def build_doctor_report() -> dict[str, object]:
    """Build a secret-safe environment diagnostics report."""

    settings = get_settings()
    python_version = ".".join(str(part) for part in sys.version_info[:3])
    python_ok = sys.version_info >= (3, 11)
    model_name = (
        settings.ollama_model
        if settings.llm_provider == "ollama"
        else settings.openai_model
    )
    return {
        "python_version": python_version,
        "python_requires": ">=3.11",
        "python_ok": python_ok,
        "cwd": str(Path.cwd()),
        "env_exists": Path(".env").exists(),
        "output_dir": str(settings.output_dir),
        "output_dir_exists": settings.output_dir.exists(),
        "data_dir": str(settings.data_dir),
        "data_dir_exists": settings.data_dir.exists(),
        "checkpoint_db_path": str(settings.checkpoint_db_path),
        "llm_provider": settings.llm_provider,
        "model": model_name or "",
    }


@app.command()
def doctor() -> None:
    """Inspect local runtime configuration without printing secrets."""

    report = build_doctor_report()
    table = Table(title="Writing Agent Doctor")
    table.add_column("Check")
    table.add_column("Value")
    for key, value in report.items():
        table.add_row(key, str(value))
    console.print(table)
    if not report["python_ok"]:
        console.print(
            "[red]Python 3.11+ is required.[/red] "
            "Create a 3.11 environment before installing the project."
        )


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
    thread_id: Annotated[
        str | None,
        typer.Option("--thread-id", help="Checkpoint thread id. Auto-generated when omitted."),
    ] = None,
    rag: Annotated[
        bool,
        typer.Option("--rag/--no-rag", help="Use minimal local RAG retrieval."),
    ] = True,
    top_k: Annotated[int, typer.Option("--top-k", help="Retrieved source chunks per section.")] = 5,
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
    resolved_thread_id = thread_id or generate_thread_id()
    console.print("[bold]Starting writing workflow[/bold]")
    console.print(f"[bold]thread_id:[/bold] {resolved_thread_id}")
    result = run_writing_workflow(
        {
            "request": request,
            "output_format": output_format,
            "output_dir": str(settings.output_dir),
            "pause_after_outline": pause_after_outline,
            "pause_before_export": pause_before_export,
            "rag_enabled": rag,
            "rag_top_k": top_k,
        },
        settings=settings,
        thread_id=resolved_thread_id,
    )
    for error in result.get("errors", []):
        console.print(f"[yellow]Warning:[/yellow] {error}")
    if result.get("awaiting_human_review"):
        console.print(f"[yellow]Paused for human review at:[/yellow] {result.get('current_step')}")
        console.print("[bold]Next step:[/bold]")
        console.print(
            f"writing-agent resume --thread-id {resolved_thread_id} --review-file review.md"
        )
        if result.get("__interrupt__"):
            console.print("[bold]Interrupt payload:[/bold]")
            console.print(result["__interrupt__"])
    else:
        console.print(f"[green]Exported:[/green] {result.get('output_path')}")


def _load_review_file(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    stripped = text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return text
    return text


@app.command()
def resume(
    thread_id: Annotated[str, typer.Option("--thread-id", help="Checkpoint thread id.")],
    review_file: Annotated[
        Path,
        typer.Option("--review-file", exists=True, file_okay=True, dir_okay=False),
    ],
) -> None:
    """Resume a workflow paused for human review."""

    settings = get_settings()
    review_payload = _load_review_file(review_file)
    result = resume_writing_workflow(thread_id, review_payload, settings=settings)
    for error in result.get("errors", []):
        console.print(f"[yellow]Warning:[/yellow] {error}")
    if result.get("awaiting_human_review"):
        console.print(f"[yellow]Paused again at:[/yellow] {result.get('current_step')}")
        console.print(f"writing-agent resume --thread-id {thread_id} --review-file review.md")
    else:
        console.print(f"[green]Resumed and exported:[/green] {result.get('output_path')}")


@app.command()
def threads() -> None:
    """List known checkpoint threads."""

    rows = list_threads(get_settings())
    table = Table(title="Writing Threads")
    table.add_column("thread_id")
    table.add_column("updated_at")
    table.add_column("current_step")
    table.add_column("interrupted")
    for row in rows:
        table.add_row(
            str(row.get("thread_id", "")),
            str(row.get("updated_at", "")),
            str(row.get("current_step", "")),
            str(row.get("interrupted", "")),
        )
    console.print(table)


@app.command("inspect")
def inspect_command(
    thread_id: Annotated[str, typer.Option("--thread-id", help="Checkpoint thread id.")],
) -> None:
    """Inspect a checkpoint thread summary."""

    summary = inspect_thread(thread_id, get_settings())
    if summary is None:
        console.print(f"[red]No metadata found for thread:[/red] {thread_id}")
        raise typer.Exit(code=1)
    table = Table(title=f"Thread {thread_id}")
    table.add_column("Field")
    table.add_column("Value")
    for key in [
        "request_topic",
        "current_step",
        "interrupted",
        "section_count",
        "review_finding_count",
        "final_document_exists",
        "output_path",
    ]:
        table.add_row(key, str(summary.get(key, "")))
    console.print(table)


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
    if settings.llm_provider == "ollama":
        try:
            with urlopen(settings.ollama_base_url, timeout=5) as response:
                console.print(
                    f"[green]Ollama base URL reachable:[/green] "
                    f"{settings.ollama_base_url} ({response.status})"
                )
        except (URLError, TimeoutError, ValueError) as exc:
            console.print(f"[yellow]Ollama base URL check failed:[/yellow] {exc}")
    elif settings.llm_provider == "openai_compatible" and not settings.openai_base_url:
        console.print("[red]OPENAI_BASE_URL is required for openai_compatible provider.[/red]")
        raise typer.Exit(code=1)

    started_at = time.perf_counter()
    try:
        model = get_chat_model(settings)
        response = model.invoke("Reply with a short readiness confirmation.")
        content = getattr(response, "content", response)
    except Exception as exc:
        console.print(f"[red]Model check failed:[/red] {exc}")
        console.print(format_connection_help(settings))
        console.print("Troubleshooting:")
        console.print("- Check whether `ollama serve` is running.")
        console.print("- Check `ollama list` contains the configured model.")
        console.print("- Check OLLAMA_BASE_URL, normally http://localhost:11434.")
        console.print("- In Windows Docker setups, consider host.docker.internal.")
        raise typer.Exit(code=1) from exc
    elapsed = time.perf_counter() - started_at
    console.print("[green]Model responded.[/green]")
    console.print(f"provider={settings.llm_provider}")
    model_name = (
        settings.ollama_model if settings.llm_provider == "ollama" else settings.openai_model
    )
    console.print(f"model={model_name}")
    if settings.llm_provider == "ollama":
        console.print(f"base_url={settings.ollama_base_url}")
    elif settings.openai_base_url:
        console.print(f"base_url={settings.openai_base_url}")
    console.print(f"elapsed_seconds={elapsed:.2f}")
    console.print(str(content)[:200])


if __name__ == "__main__":
    app()
