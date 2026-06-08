"""Batch generation and evaluation helpers."""

import json
from pathlib import Path
from typing import Any

from writing_agent.config import Settings, get_settings
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
) -> dict[str, Any]:
    """Run a set of writing tasks. Failures do not stop later tasks."""

    resolved_settings = settings or get_settings()
    tasks = load_jsonl_tasks(tasks_path)
    results: list[dict[str, Any]] = []
    success = 0
    failure = 0
    for task in tasks:
        task_id = str(task.get("id") or f"task-{len(results) + 1}")
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
                    "output_dir": str(output_dir),
                    "output_format": output_format,
                    "rag_enabled": True,
                    "rag_mode": rag_mode,
                    "rag_collection": collection,
                    "rag_top_k": int(task.get("top_k", 5)),
                },
                settings=resolved_settings,
                thread_id=f"batch-{task_id}",
            )
            success += 1
            results.append({"id": task_id, "status": "success", "result": result})
        except Exception as exc:
            failure += 1
            results.append({"id": task_id, "status": "failed", "error": str(exc)})
    return {"success": success, "failure": failure, "results": results}


def evaluate_batch_directory(input_dir: Path | str) -> dict[str, Any]:
    """Evaluate all markdown files in a directory and summarize metrics."""

    markdown_files = sorted(Path(input_dir).glob("*.md"))
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
