"""Batch generation and evaluation helpers."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from writing_agent.config import Settings, get_settings
from writing_agent.evaluation.batch_report import utc_now, write_failed_tasks, write_json
from writing_agent.evaluation.evaluator import evaluate_markdown
from writing_agent.graph.workflow import run_writing_workflow
from writing_agent.models import WritingRequest


def load_jsonl_tasks(path: Path | str) -> list[dict[str, Any]]:
    """Load batch tasks from a JSONL file."""

    tasks: list[dict[str, Any]] = []
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            tasks.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON on line {line_number}: {exc}") from exc
    return tasks


def run_batch_tasks(
    tasks_path: Path | str,
    *,
    output_dir: Path | str,
    rag_mode: str = "hybrid",
    collection: str = "",
    output_format: str = "markdown",
    settings: Settings | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run a set of writing tasks. Failures do not stop later tasks."""

    resolved_settings = settings or get_settings()
    tasks = load_jsonl_tasks(tasks_path)
    resolved_run_id = run_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = Path(output_dir) / resolved_run_id
    task_output_dir = run_dir / "task_outputs"
    task_output_dir.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    task_reports: list[dict[str, Any]] = []
    failed_tasks: list[dict[str, Any]] = []
    success = 0
    failure = 0
    for task in tasks:
        task_id = str(task.get("id") or f"task-{len(task_reports) + 1}")
        started = time.perf_counter()
        thread_id = f"batch-{resolved_run_id}-{task_id}"
        try:
            request = WritingRequest.model_validate(
                {
                    "topic": task["topic"],
                    "document_type": task.get("document_type", "report"),
                    "audience": task.get("audience", "general readers"),
                    "target_length": task.get("target_length", "3000 words"),
                    "style": task.get("style", "formal and concise"),
                    "constraints": task.get("constraints", []),
                    "source_paths": task.get("source_paths", []),
                }
            )
            result = run_writing_workflow(
                {
                    "request": request,
                    "output_dir": str(task_output_dir),
                    "output_format": output_format,
                    "rag_enabled": True,
                    "rag_mode": rag_mode,
                    "rag_collection": collection,
                    "rag_top_k": int(task.get("top_k", 5)),
                },
                settings=resolved_settings,
                thread_id=thread_id,
            )
            output_file = str(result.get("output_path") or "")
            success += 1
            task_reports.append(
                {
                    "id": task_id,
                    "status": "success",
                    "output_file": output_file,
                    "error_message": "",
                    "duration_seconds": time.perf_counter() - started,
                    "thread_id": thread_id,
                }
            )
        except Exception as exc:
            failure += 1
            failed_tasks.append(task)
            task_reports.append(
                {
                    "id": task_id,
                    "status": "failed",
                    "output_file": "",
                    "error_message": str(exc),
                    "duration_seconds": time.perf_counter() - started,
                    "thread_id": thread_id,
                }
            )
    report = {
        "run_id": resolved_run_id,
        "started_at": started_at,
        "finished_at": utc_now(),
        "total_tasks": len(tasks),
        "success_count": success,
        "failed_count": failure,
        "skipped_count": 0,
        "tasks": task_reports,
    }
    write_json(run_dir / "batch_report.json", report)
    write_failed_tasks(run_dir / "failed_tasks.jsonl", failed_tasks)
    write_json(
        run_dir / "run_config.json",
        {
            "tasks_path": str(tasks_path),
            "rag_mode": rag_mode,
            "collection": collection,
            "output_format": output_format,
        },
    )
    return {
        "run_id": resolved_run_id,
        "run_dir": str(run_dir),
        "success": success,
        "failure": failure,
        "results": task_reports,
    }


def evaluate_batch_directory(input_dir: Path | str) -> dict[str, Any]:
    """Evaluate all markdown files in a directory and summarize metrics."""

    root = Path(input_dir)
    search_dir = root / "task_outputs" if (root / "task_outputs").exists() else root
    markdown_files = sorted(search_dir.glob("*.md"))
    evaluations = [evaluate_markdown(path) for path in markdown_files]
    count = len(evaluations)
    if count == 0:
        return {
            "file_count": 0,
            "evaluations": [],
            "summary": {
                "average_words": 0,
                "average_sections": 0,
                "average_repeated_paragraph_ratio": 0,
                "average_insufficient_evidence_count": 0,
                "risk_term_total": 0,
            },
        }

    risk_total = sum(sum(item["risk_terms"].values()) for item in evaluations)
    summary = {
        "average_words": sum(item["words"] for item in evaluations) / count,
        "average_sections": sum(item["section_count"] for item in evaluations) / count,
        "average_repeated_paragraph_ratio": sum(
            item["repeated_paragraph_ratio"] for item in evaluations
        )
        / count,
        "average_insufficient_evidence_count": sum(
            item["insufficient_evidence_count"] for item in evaluations
        )
        / count,
        "risk_term_total": risk_total,
    }
    return {"file_count": count, "evaluations": evaluations, "summary": summary}
