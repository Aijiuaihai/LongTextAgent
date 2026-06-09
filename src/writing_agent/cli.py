"""Typer CLI entrypoint."""

import json
import sys
import time
import webbrowser
from pathlib import Path
from typing import Annotated
from urllib.error import URLError
from urllib.request import urlopen

import typer
from rich.console import Console
from rich.table import Table

from writing_agent.agents import get_agent_spec, list_agent_specs
from writing_agent.agents.metrics import summarize_agent_metrics
from writing_agent.checkpoints import inspect_thread, list_threads
from writing_agent.config import get_settings
from writing_agent.evaluation.batch import (
    build_baseline_summary,
    evaluate_batch_directory,
    run_batch_tasks,
)
from writing_agent.evaluation.compare import (
    compare_baseline_summaries,
    render_baseline_comparison,
)
from writing_agent.evaluation.evaluator import evaluate_markdown
from writing_agent.evaluation.llm_judge import judge_document_with_llm
from writing_agent.graph.multi_agent_workflow import (
    resume_multi_agent_workflow,
    run_multi_agent_workflow,
)
from writing_agent.graph.workflow import (
    generate_thread_id,
    resume_writing_workflow,
    run_writing_workflow,
)
from writing_agent.llm import format_connection_help, get_chat_model
from writing_agent.models import DocumentType, WritingRequest
from writing_agent.observability.langsmith import configure_langsmith, is_langsmith_enabled
from writing_agent.rag.collections import (
    delete_collection,
    export_collection_manifest,
    get_collection_stats,
    list_collections,
    rebuild_collection,
)
from writing_agent.rag.diff import diff_collections, diff_manifests, summarize_manifest_diff
from writing_agent.rag.retriever import VectorRetriever
from writing_agent.rag.vector_index import (
    add_documents_to_index,
    load_chroma_index,
    reset_chroma_index,
)
from writing_agent.tools.document_loader import load_sources
from writing_agent.tools.docx_preflight import validate_docx_template
from writing_agent.verification.repair import repair_citations_in_file
from writing_agent.verification.report import citation_result_to_json, print_citation_report
from writing_agent.verification.verifier import verify_citations_in_file

app = typer.Typer(help="Long-form writing agent CLI.", no_args_is_help=True)
collections_app = typer.Typer(help="Manage local Chroma collections.")
template_app = typer.Typer(help="Inspect and validate DOCX templates.")
agents_app = typer.Typer(help="Inspect multi-agent roles and traces.")
app.add_typer(collections_app, name="collections")
app.add_typer(template_app, name="template")
app.add_typer(agents_app, name="agents")
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
        settings.ollama_model if settings.llm_provider == "ollama" else settings.openai_model
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


def build_trace_check_report() -> dict[str, object]:
    """Build secret-safe LangSmith trace check report."""

    settings = get_settings()
    warnings = configure_langsmith(settings)
    return {
        "langsmith_tracing": settings.langsmith_tracing,
        "langsmith_project": settings.langsmith_project,
        "api_key_detected": settings.langsmith_api_key is not None,
        "will_upload_trace": is_langsmith_enabled(settings),
        "warnings": warnings,
    }


@app.command("trace-check")
def trace_check() -> None:
    """Check LangSmith tracing configuration without printing secrets."""

    console.print(build_trace_check_report())


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option("--host", help="Bind host.")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Bind port.")] = 8000,
    reload: Annotated[
        bool,
        typer.Option("--reload/--no-reload", help="Enable uvicorn reload for local development."),
    ] = False,
    open_browser: Annotated[
        bool,
        typer.Option("--open-browser/--no-open-browser", help="Open the web console in a browser."),
    ] = False,
) -> None:
    """Start the simple web frontend."""

    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover - dependency guard
        console.print("[red]Install the web dependencies with `python -m pip install -e .`.[/red]")
        raise typer.Exit(code=1) from exc
    url = f"http://{host}:{port}"
    console.print(f"[green]Serving LongTextAgent:[/green] {url}")
    if host == "0.0.0.0":
        console.print(
            "[yellow]Warning:[/yellow] binding 0.0.0.0 may expose the local console. "
            "You are responsible for network security."
        )
    if open_browser:
        webbrowser.open(url)
    uvicorn.run("writing_agent.web.app:app", host=host, port=port, reload=reload)


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
        typer.Option("--output-format", help="markdown, docx, or both."),
    ] = "markdown",
    docx_template: Annotated[
        Path | None,
        typer.Option("--docx-template", help="Optional .docx template path."),
    ] = None,
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
    rag_mode: Annotated[
        str,
        typer.Option("--rag-mode", help="keyword, vector, or hybrid."),
    ] = "hybrid",
    collection: Annotated[
        str | None,
        typer.Option("--collection", help="Chroma collection name for vector RAG."),
    ] = None,
    rebuild_index: Annotated[
        bool,
        typer.Option("--rebuild-index/--no-rebuild-index", help="Rebuild collection from sources."),
    ] = False,
    top_k: Annotated[int, typer.Option("--top-k", help="Retrieved source chunks per section.")] = 5,
    mode: Annotated[
        str,
        typer.Option("--mode", help="single or multi workflow mode."),
    ] = "single",
    max_agent_rounds: Annotated[
        int,
        typer.Option("--max-agent-rounds", help="Maximum bounded multi-agent edit rounds."),
    ] = 2,
    agent_debug: Annotated[
        bool,
        typer.Option("--agent-debug/--no-agent-debug", help="Print multi-agent trace summary."),
    ] = False,
    review_outline: Annotated[
        bool,
        typer.Option(
            "--review-outline/--no-review-outline",
            help="Pause multi-agent mode after planning.",
        ),
    ] = False,
    review_final: Annotated[
        bool,
        typer.Option(
            "--review-final/--no-review-final",
            help="Pause multi-agent mode before evaluation.",
        ),
    ] = False,
) -> None:
    """Run the long-form writing workflow."""

    settings = get_settings()
    if docx_template is not None:
        preflight = validate_docx_template(docx_template)
        if preflight.status == "fail":
            console.print("[red]DOCX template preflight failed.[/red]")
            console.print(preflight.model_dump(mode="json"))
            raise typer.Exit(code=1)
        if preflight.status == "warning":
            console.print("[yellow]DOCX template preflight warnings:[/yellow]")
            console.print(preflight.model_dump(mode="json"))
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
    initial_state = {
        "request": request,
        "output_format": output_format,
        "output_dir": str(settings.output_dir),
        "docx_template": str(docx_template) if docx_template else "",
        "pause_after_outline": pause_after_outline,
        "pause_before_export": pause_before_export,
        "rag_enabled": rag,
        "rag_mode": rag_mode,
        "rag_collection": collection or "",
        "rag_rebuild_index": rebuild_index,
        "rag_top_k": top_k,
        "mode": mode,
        "review_outline": review_outline if mode == "multi" else False,
        "review_final": review_final if mode == "multi" else False,
    }
    if mode == "multi":
        result = run_multi_agent_workflow(
            initial_state,
            settings=settings,
            thread_id=resolved_thread_id,
            max_rounds=max_agent_rounds,
        )
    elif mode == "single":
        result = run_writing_workflow(
            initial_state,
            settings=settings,
            thread_id=resolved_thread_id,
        )
    else:
        console.print("[red]--mode must be single or multi.[/red]")
        raise typer.Exit(code=1)
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
        output_paths = result.get("output_paths")
        console.print(f"[green]Exported:[/green] {output_paths or result.get('output_path')}")
    if agent_debug and result.get("agent_results"):
        console.print("[bold]Agent results[/bold]")
        for item in result.get("agent_results", []):
            console.print(item)


@agents_app.command("list")
def agents_list() -> None:
    """List available multi-agent roles."""

    table = Table(title="Multi-agent roles")
    table.add_column("agent")
    table.add_column("responsibility")
    table.add_column("input")
    table.add_column("output")
    for spec in list_agent_specs():
        table.add_row(spec.name, spec.responsibility, spec.input_schema, spec.output_schema)
    console.print(table)


@agents_app.command("inspect")
def agents_inspect(
    agent: Annotated[str, typer.Option("--agent", help="Agent name.")],
) -> None:
    """Inspect one multi-agent role."""

    spec = get_agent_spec(agent)
    if spec is None:
        console.print(f"[red]Unknown agent:[/red] {agent}")
        raise typer.Exit(code=1)
    console.print(json.dumps(spec.model_dump(mode="json"), ensure_ascii=False, indent=2))


@agents_app.command("trace")
def agents_trace(
    thread_id: Annotated[str, typer.Option("--thread-id", help="Workflow thread id.")],
) -> None:
    """Show persisted multi-agent trace summary for a thread."""

    summary = inspect_thread(thread_id, get_settings())
    if summary is None:
        console.print(f"[red]No metadata found for thread:[/red] {thread_id}")
        raise typer.Exit(code=1)
    table = Table(title=f"Agent trace: {thread_id}")
    table.add_column("agent")
    table.add_column("status")
    table.add_column("duration")
    table.add_column("warnings")
    table.add_column("errors")
    for item in summary.get("agent_results", []):
        table.add_row(
            str(item.get("agent_name", "")),
            str(item.get("status", "")),
            f"{float(item.get('duration_seconds', 0) or 0):.3f}",
            str(len(item.get("warnings", []))),
            str(len(item.get("errors", []))),
        )
    console.print(table)
    if summary.get("supervisor_decisions"):
        console.print("[bold]Supervisor decisions[/bold]")
        console.print(summary["supervisor_decisions"])


@agents_app.command("metrics")
def agents_metrics(
    thread_id: Annotated[str, typer.Option("--thread-id", help="Workflow thread id.")],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print metrics as JSON."),
    ] = False,
) -> None:
    """Show persisted agent metrics for a thread."""

    summary = inspect_thread(thread_id, get_settings())
    if summary is None:
        console.print(f"[red]No metadata found for thread:[/red] {thread_id}")
        raise typer.Exit(code=1)
    metrics = summary.get("agent_metrics") or summarize_agent_metrics(
        thread_id,
        summary,
    ).model_dump(mode="json")
    if json_output:
        console.print(json.dumps(metrics, ensure_ascii=False, indent=2))
        return
    table = Table(title=f"Agent metrics: {thread_id}")
    table.add_column("agent")
    table.add_column("metric")
    table.add_column("value")
    for agent_name in [
        "researcher",
        "planner",
        "writer",
        "citation_auditor",
        "reviewer",
        "editor",
        "formatter",
        "evaluator",
        "supervisor",
    ]:
        values = metrics.get(agent_name, {}) if isinstance(metrics, dict) else {}
        if isinstance(values, dict):
            for metric_name, value in values.items():
                table.add_row(agent_name, str(metric_name), str(value))
    if isinstance(metrics, dict):
        table.add_row("total", "agents_run", str(metrics.get("total_agents_run", 0)))
        table.add_row("total", "errors", str(metrics.get("total_errors", 0)))
        table.add_row("total", "warnings", str(metrics.get("total_warnings", 0)))
    console.print(table)


@app.command("index")
def index_command(
    source: Annotated[
        list[str],
        typer.Option("--source", help="Local source path. Can be repeated."),
    ],
    collection: Annotated[str, typer.Option("--collection", help="Chroma collection name.")],
    reset: Annotated[
        bool,
        typer.Option("--reset", help="Reset the collection before indexing."),
    ] = False,
) -> None:
    """Build or update a local Chroma index."""

    settings = get_settings()
    if reset:
        reset_chroma_index(collection, settings=settings)
        console.print(f"[yellow]Reset collection:[/yellow] {collection}")
    notes = load_sources(source)
    add_documents_to_index(notes, collection_name=collection, settings=settings)
    console.print(f"[green]Indexed sources:[/green] {len(notes)}")
    console.print(f"[bold]collection:[/bold] {collection}")


@app.command("retrieve")
def retrieve_command(
    query: Annotated[str, typer.Option("--query", help="Retrieval query.")],
    collection: Annotated[str, typer.Option("--collection", help="Chroma collection name.")],
    top_k: Annotated[int, typer.Option("--top-k", help="Number of chunks to return.")] = 5,
) -> None:
    """Retrieve chunks from a local Chroma collection."""

    vector_store = load_chroma_index(collection_name=collection, settings=get_settings())
    results = VectorRetriever(vector_store).retrieve(query, top_k=top_k)
    table = Table(title=f"Retrieval: {collection}")
    table.add_column("chunk_id")
    table.add_column("score")
    table.add_column("source_path")
    table.add_column("preview")
    for result in results:
        table.add_row(
            result.chunk_id,
            f"{result.score:.3f}",
            result.source_path,
            result.text[:160],
        )
    console.print(table)


@collections_app.command("list")
def collections_list() -> None:
    """List known local collections."""

    rows = list_collections(get_settings())
    table = Table(title="Collections")
    table.add_column("collection")
    table.add_column("updated_at")
    table.add_column("sources")
    table.add_column("chunks")
    for row in rows:
        table.add_row(
            str(row["collection_name"]),
            str(row["updated_at"]),
            str(row["source_count"]),
            str(row["chunk_count"]),
        )
    console.print(table)


@collections_app.command("stats")
def collections_stats(
    collection: Annotated[str, typer.Option("--collection", help="Collection name.")],
) -> None:
    """Show collection stats."""

    stats = get_collection_stats(collection, get_settings())
    console.print(stats)


@collections_app.command("delete")
def collections_delete(
    collection: Annotated[str, typer.Option("--collection", help="Collection name.")],
    yes: Annotated[bool, typer.Option("--yes", help="Skip confirmation.")] = False,
) -> None:
    """Delete a local collection manifest and best-effort persistence."""

    if not yes and not typer.confirm(f"Delete collection {collection}?"):
        console.print("[yellow]Cancelled.[/yellow]")
        return
    deleted = delete_collection(collection, get_settings())
    message = f"[green]Deleted:[/green] {collection}" if deleted else "[yellow]Not found.[/yellow]"
    console.print(message)


@collections_app.command("rebuild")
def collections_rebuild(
    collection: Annotated[str, typer.Option("--collection", help="Collection name.")],
    source: Annotated[list[str], typer.Option("--source", help="Source path. Can repeat.")],
) -> None:
    """Rebuild a local collection."""

    stats = rebuild_collection(collection, source, get_settings())
    console.print(stats)


@collections_app.command("export-manifest")
def collections_export_manifest(
    collection: Annotated[str, typer.Option("--collection", help="Collection name.")],
    output: Annotated[Path, typer.Option("--output", help="Manifest export path.")],
) -> None:
    """Export a collection manifest."""

    path = export_collection_manifest(collection, output, get_settings())
    console.print(f"[green]Exported manifest:[/green] {path}")


@collections_app.command("diff")
def collections_diff(
    old_manifest: Annotated[
        Path | None,
        typer.Option("--old-manifest", help="Old manifest JSON path."),
    ] = None,
    new_manifest: Annotated[
        Path | None,
        typer.Option("--new-manifest", help="New manifest JSON path."),
    ] = None,
    old_collection: Annotated[
        str | None,
        typer.Option("--old-collection", help="Old collection name."),
    ] = None,
    new_collection: Annotated[
        str | None,
        typer.Option("--new-collection", help="New collection name."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print JSON output."),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Optional JSON report path."),
    ] = None,
) -> None:
    """Compare two index manifests or two persisted collections."""

    if old_manifest and new_manifest:
        diff_result = diff_manifests(old_manifest, new_manifest)
    elif old_collection and new_collection:
        diff_result = diff_collections(old_collection, new_collection, get_settings())
    else:
        console.print(
            "[red]Provide either --old-manifest/--new-manifest "
            "or --old-collection/--new-collection.[/red]"
        )
        raise typer.Exit(code=1)
    payload = diff_result.model_dump(mode="json")
    payload["summary"] = summarize_manifest_diff(diff_result)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[green]Wrote diff report:[/green] {output}")
    if json_output:
        console.print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    table = Table(title="Collection Diff")
    table.add_column("metric")
    table.add_column("value")
    summary = payload["summary"]
    for key in [
        "old_collection",
        "new_collection",
        "source_added",
        "source_removed",
        "source_changed",
        "chunk_added",
        "chunk_removed",
        "chunk_changed",
    ]:
        table.add_row(key, str(summary[key]))
    console.print(table)
    for warning in summary["warnings"]:
        console.print(f"[yellow]Warning:[/yellow] {warning}")


@template_app.command("preflight")
def template_preflight(
    template: Annotated[
        Path,
        typer.Option("--template", help="DOCX template path."),
    ],
    style_mapping: Annotated[
        Path | None,
        typer.Option("--style-mapping", help="Optional style mapping JSON."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print JSON output."),
    ] = False,
) -> None:
    """Validate a DOCX template before generation."""

    result = validate_docx_template(template, style_mapping_path=style_mapping)
    if json_output:
        console.print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        table = Table(title="Template Preflight")
        table.add_column("field")
        table.add_column("value")
        table.add_row("status", result.status)
        table.add_row("missing_placeholders", ", ".join(result.missing_placeholders))
        table.add_row("missing_styles", ", ".join(result.missing_styles))
        table.add_row("warnings", "; ".join(result.warnings))
        table.add_row("recommendations", "; ".join(result.recommendations))
        table.add_row("error", result.error)
        console.print(table)
    if result.status == "fail":
        raise typer.Exit(code=1)


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
    thread = inspect_thread(thread_id, settings)
    if thread and thread.get("mode") == "multi":
        result = resume_multi_agent_workflow(thread_id, review_payload, settings=settings)
    else:
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


@app.command()
def evaluate(
    file: Annotated[
        Path,
        typer.Option("--file", exists=True, file_okay=True, dir_okay=False),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print JSON instead of a Rich table."),
    ] = False,
    llm_judge: Annotated[
        bool,
        typer.Option("--llm-judge", help="Also run optional LLM judge evaluation."),
    ] = False,
    verify_citations: Annotated[
        bool,
        typer.Option("--verify-citations", help="Verify source citations against index manifest."),
    ] = False,
    collection: Annotated[
        str | None,
        typer.Option("--collection", help="Collection name for citation verification."),
    ] = None,
    repair_citations: Annotated[
        bool,
        typer.Option(
            "--repair-citations",
            help="Conservatively repair invalid citations after verification.",
        ),
    ] = False,
) -> None:
    """Evaluate a generated markdown document with rule-based metrics."""

    rule_metrics = evaluate_markdown(file)
    result = {"rule_metrics": rule_metrics}
    if llm_judge:
        result["llm_judge"] = judge_document_with_llm(file, settings=get_settings())
    if verify_citations:
        citation_result = verify_citations_in_file(file, collection=collection)
        result["citation_verification"] = citation_result.model_dump(mode="json")
        rule_metrics.update(
            {
                "citation_total": citation_result.total_citations,
                "citation_valid": citation_result.valid_citations,
                "citation_invalid": citation_result.invalid_citations,
                "citation_status": citation_result.overall_status,
            }
        )
        if repair_citations:
            repair_result = repair_citations_in_file(
                file,
                collection=collection,
                mode="conservative",
            )
            result["citation_repair"] = repair_result.model_dump(mode="json")
    if json_output:
        console.print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    table = Table(title=f"Evaluation: {file}")
    table.add_column("Metric")
    table.add_column("Value")
    for key, value in rule_metrics.items():
        rendered = json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else str(value)
        table.add_row(key, rendered)
    console.print(table)
    if llm_judge:
        console.print("[bold]LLM Judge[/bold]")
        console.print(result["llm_judge"])
    if verify_citations:
        print_citation_report(citation_result, console)
        if repair_citations:
            console.print("[bold]Citation repair[/bold]")
            console.print(
                {
                    "output_path": repair_result.output_path,
                    "replaced": repair_result.replaced_count,
                    "downgraded": repair_result.downgraded_count,
                    "kept": repair_result.kept_count,
                    "before": repair_result.before.overall_status
                    if repair_result.before
                    else "",
                    "after": repair_result.after.overall_status if repair_result.after else "",
                }
            )


@app.command("verify-citations")
def verify_citations_command(
    file: Annotated[
        Path,
        typer.Option("--file", exists=True, file_okay=True, dir_okay=False),
    ],
    collection: Annotated[
        str | None,
        typer.Option("--collection", help="Collection name for manifest lookup."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print JSON instead of a Rich table."),
    ] = False,
) -> None:
    """Verify source_path and chunk_id references in a markdown file."""

    result = verify_citations_in_file(file, collection=collection)
    if json_output:
        console.print(citation_result_to_json(result))
        return
    print_citation_report(result, console)


@app.command("repair-citations")
def repair_citations_command(
    file: Annotated[
        Path,
        typer.Option("--file", exists=True, file_okay=True, dir_okay=False),
    ],
    collection: Annotated[
        str | None,
        typer.Option("--collection", help="Collection name for manifest lookup."),
    ] = None,
    mode: Annotated[
        str,
        typer.Option("--mode", help="conservative or llm_assisted."),
    ] = "conservative",
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Optional repaired markdown output path."),
    ] = None,
    in_place: Annotated[
        bool,
        typer.Option("--in-place", help="Overwrite file after writing a .bak backup."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print JSON repair report."),
    ] = False,
) -> None:
    """Repair invalid citations by replacement or insufficient-evidence downgrade."""

    if mode not in {"conservative", "llm_assisted"}:
        console.print("[red]--mode must be conservative or llm_assisted.[/red]")
        raise typer.Exit(code=1)
    try:
        result = repair_citations_in_file(
            file,
            collection=collection,
            mode=mode,  # type: ignore[arg-type]
            output=output,
            in_place=in_place,
            settings=get_settings(),
        )
    except FileNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    if json_output:
        console.print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return
    table = Table(title="Citation Repair")
    table.add_column("metric")
    table.add_column("value")
    table.add_row("mode", result.mode)
    table.add_row("output_path", result.output_path)
    table.add_row("replaced", str(result.replaced_count))
    table.add_row("downgraded", str(result.downgraded_count))
    table.add_row("kept", str(result.kept_count))
    table.add_row("before_status", result.before.overall_status if result.before else "")
    table.add_row("after_status", result.after.overall_status if result.after else "")
    console.print(table)


@app.command("batch-run")
def batch_run(
    tasks: Annotated[
        Path,
        typer.Option("--tasks", exists=True, file_okay=True, dir_okay=False),
    ],
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Batch output directory.")],
    rag_mode: Annotated[str, typer.Option("--rag-mode", help="keyword, vector, or hybrid.")] = (
        "hybrid"
    ),
    collection: Annotated[
        str,
        typer.Option("--collection", help="Chroma collection name."),
    ] = "",
    output_format: Annotated[
        str,
        typer.Option("--output-format", help="markdown, docx, or both."),
    ] = "markdown",
    mode: Annotated[
        str,
        typer.Option("--mode", help="single or multi workflow mode."),
    ] = "single",
    max_agent_rounds: Annotated[
        int,
        typer.Option("--max-agent-rounds", help="Maximum multi-agent review/edit rounds."),
    ] = 2,
    trace: Annotated[
        bool,
        typer.Option("--trace/--no-trace", help="Enable optional LangSmith tracing."),
    ] = False,
) -> None:
    """Run a JSONL batch of writing tasks."""

    if trace:
        trace_report = build_trace_check_report()
        if trace_report["warnings"]:
            console.print(trace_report["warnings"])
    result = run_batch_tasks(
        tasks,
        output_dir=output_dir,
        rag_mode=rag_mode,
        collection=collection,
        output_format=output_format,
        mode=mode,
        max_agent_rounds=max_agent_rounds,
        settings=get_settings(),
    )
    table = Table(title="Batch Run")
    table.add_column("status")
    table.add_column("count")
    table.add_row("success", str(result["success"]))
    table.add_row("failure", str(result["failure"]))
    console.print(table)
    for item in result["results"]:
        if item["status"] == "failed":
            console.print(f"[red]{item['id']} failed:[/red] {item['error_message']}")


@app.command("baseline-run")
def baseline_run(
    tasks: Annotated[
        Path,
        typer.Option("--tasks", exists=True, file_okay=True, dir_okay=False),
    ],
    collection: Annotated[str, typer.Option("--collection", help="Chroma collection name.")],
    rag_mode: Annotated[str, typer.Option("--rag-mode", help="keyword, vector, or hybrid.")] = (
        "hybrid"
    ),
    output_dir: Annotated[Path, typer.Option("--output-dir", help="Baseline output root.")] = (
        Path("outputs/baseline")
    ),
    mode: Annotated[
        str,
        typer.Option("--mode", help="single or multi workflow mode."),
    ] = "single",
    max_agent_rounds: Annotated[
        int,
        typer.Option("--max-agent-rounds", help="Maximum multi-agent review/edit rounds."),
    ] = 2,
) -> None:
    """Run a fixed baseline batch and write baseline_summary.json."""

    settings = get_settings()
    result = run_batch_tasks(
        tasks,
        output_dir=output_dir,
        rag_mode=rag_mode,
        collection=collection,
        output_format="markdown",
        mode=mode,
        max_agent_rounds=max_agent_rounds,
        settings=settings,
    )
    summary = build_baseline_summary(
        batch_result=result,
        rag_mode=rag_mode,
        collection=collection,
        settings=settings,
        mode=mode,
        max_agent_rounds=max_agent_rounds,
    )
    summary_path = Path(result["run_dir"]) / "baseline_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]Baseline summary:[/green] {summary_path}")
    console.print(summary)


@app.command("baseline-compare")
def baseline_compare(
    base: Annotated[
        Path,
        typer.Option("--base", exists=True, file_okay=True, dir_okay=False),
    ],
    candidate: Annotated[
        Path,
        typer.Option("--candidate", exists=True, file_okay=True, dir_okay=False),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print JSON output."),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option("--output", help="Optional JSON report path."),
    ] = None,
    fail_on_regression: Annotated[
        bool,
        typer.Option("--fail-on-regression", help="Exit nonzero on fail-level regression."),
    ] = False,
) -> None:
    """Compare two baseline_summary.json files."""

    result = compare_baseline_summaries(base, candidate)
    payload = render_baseline_comparison(result)
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[green]Wrote baseline comparison:[/green] {output}")
    if json_output:
        console.print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        table = Table(title="Baseline Compare")
        table.add_column("metric")
        table.add_column("value")
        table.add_row("status", result.status)
        table.add_row("delta_rule_score", f"{result.delta_rule_score:.4f}")
        table.add_row("delta_citation_valid_rate", f"{result.delta_citation_valid_rate:.4f}")
        table.add_row(
            "delta_insufficient_evidence_count",
            f"{result.delta_insufficient_evidence_count:.4f}",
        )
        table.add_row("delta_high_severity_findings", f"{result.delta_high_severity_findings:.4f}")
        table.add_row("delta_run_duration_seconds", f"{result.delta_run_duration_seconds:.4f}")
        table.add_row("regression_flags", str(len(result.regression_flags)))
        table.add_row("improvements", str(len(result.improvements)))
        console.print(table)
        for flag in result.regression_flags:
            console.print(f"[yellow]{flag.severity}[/yellow] {flag.metric}: {flag.message}")
        for improvement in result.improvements:
            console.print(f"[green]improvement[/green] {improvement}")
    if fail_on_regression and result.status == "fail":
        raise typer.Exit(code=1)


@app.command("batch-rerun-failed")
def batch_rerun_failed(
    failed_tasks: Annotated[
        Path,
        typer.Option("--failed-tasks", exists=True, file_okay=True, dir_okay=False),
    ],
    output_dir: Annotated[Path, typer.Option("--output-dir", help="New batch output directory.")],
    rag_mode: Annotated[str, typer.Option("--rag-mode", help="keyword, vector, or hybrid.")] = (
        "hybrid"
    ),
    collection: Annotated[
        str,
        typer.Option("--collection", help="Chroma collection name."),
    ] = "",
    output_format: Annotated[
        str,
        typer.Option("--output-format", help="markdown, docx, or both."),
    ] = "markdown",
) -> None:
    """Rerun failed tasks from a failed_tasks.jsonl file."""

    result = run_batch_tasks(
        failed_tasks,
        output_dir=output_dir,
        rag_mode=rag_mode,
        collection=collection,
        output_format=output_format,
        settings=get_settings(),
    )
    console.print(
        {
            "run_id": result["run_id"],
            "success": result["success"],
            "failure": result["failure"],
            "run_dir": result["run_dir"],
        }
    )


@app.command("batch-evaluate")
def batch_evaluate(
    input_dir: Annotated[Path, typer.Option("--input-dir", exists=True, file_okay=False)],
    json_output: Annotated[
        Path | None,
        typer.Option("--json-output", help="Optional JSON output path."),
    ] = None,
) -> None:
    """Evaluate every markdown file in a directory and summarize metrics."""

    result = evaluate_batch_directory(input_dir)
    if json_output is not None:
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[green]Wrote JSON:[/green] {json_output}")

    table = Table(title=f"Batch Evaluation: {input_dir}")
    table.add_column("metric")
    table.add_column("value")
    table.add_row("file_count", str(result["file_count"]))
    for key, value in result["summary"].items():
        table.add_row(key, f"{value:.3f}" if isinstance(value, float) else str(value))
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
