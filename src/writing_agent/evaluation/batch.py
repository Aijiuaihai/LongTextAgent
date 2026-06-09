"""Batch generation and evaluation helpers."""

import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from writing_agent.config import Settings, get_settings
from writing_agent.evaluation.batch_report import utc_now, write_failed_tasks, write_json
from writing_agent.evaluation.evaluator import evaluate_markdown
from writing_agent.graph.multi_agent_workflow import run_multi_agent_workflow
from writing_agent.graph.workflow import run_writing_workflow
from writing_agent.models import WritingRequest
from writing_agent.verification.verifier import verify_citations_in_file


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
    mode: str = "single",
    max_agent_rounds: int = 2,
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
            initial_state = {
                "request": request,
                "output_dir": str(task_output_dir),
                "output_format": output_format,
                "rag_enabled": True,
                "rag_mode": rag_mode,
                "rag_collection": collection,
                "rag_top_k": int(task.get("top_k", 5)),
            }
            if mode == "multi":
                result = run_multi_agent_workflow(
                    initial_state,
                    settings=resolved_settings,
                    thread_id=thread_id,
                    max_rounds=max_agent_rounds,
                )
            else:
                result = run_writing_workflow(
                    initial_state,
                    settings=resolved_settings,
                    thread_id=thread_id,
                )
            output_file = str(result.get("output_path") or "")
            agent_results = result.get("agent_results") or []
            citation_audits = result.get("citation_audits") or []
            review_findings = result.get("review_findings") or []
            citation_repair_count = 0
            for audit in citation_audits:
                if isinstance(audit, dict):
                    citation_repair_count += int(audit.get("repaired_citations", 0) or 0)
                    citation_repair_count += int(audit.get("downgraded_citations", 0) or 0)
                else:
                    citation_repair_count += int(getattr(audit, "repaired_citations", 0) or 0)
                    citation_repair_count += int(
                        getattr(audit, "downgraded_citations", 0) or 0
                    )
            high_severity_findings = sum(
                1
                for finding in review_findings
                if (
                    getattr(finding, "severity", "")
                    if not isinstance(finding, dict)
                    else finding.get("severity", "")
                )
                == "high"
            )
            duration = time.perf_counter() - started
            success += 1
            task_reports.append(
                {
                    "id": task_id,
                    "status": "success",
                    "output_file": output_file,
                    "error_message": "",
                    "duration_seconds": duration,
                    "thread_id": thread_id,
                    "mode": mode,
                    "agent_count": len(agent_results),
                    "round_count": int(result.get("current_round", 0) or 0),
                    "citation_repair_count": citation_repair_count,
                    "high_severity_findings": high_severity_findings,
                }
            )
        except Exception as exc:
            duration = time.perf_counter() - started
            failure += 1
            failed_tasks.append(task)
            task_reports.append(
                {
                    "id": task_id,
                    "status": "failed",
                    "output_file": "",
                    "error_message": str(exc),
                    "duration_seconds": duration,
                    "thread_id": thread_id,
                    "mode": mode,
                    "agent_count": 0,
                    "round_count": 0,
                    "citation_repair_count": 0,
                    "high_severity_findings": 0,
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
            "mode": mode,
            "max_agent_rounds": max_agent_rounds,
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


def _git_commit_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return ""


def _rule_score(evaluation: dict[str, Any]) -> float:
    score = 0.0
    score += 1.0 if evaluation.get("has_abstract") else 0.0
    score += 1.0 if evaluation.get("has_conclusion") else 0.0
    score += 1.0 if evaluation.get("has_references") else 0.0
    score += min(float(evaluation.get("section_count", 0)) / 5.0, 1.0)
    score += max(0.0, 1.0 - float(evaluation.get("repeated_paragraph_ratio", 0)))
    return score / 5.0


def build_baseline_summary(
    *,
    batch_result: dict[str, Any],
    rag_mode: str,
    collection: str,
    settings: Settings,
    mode: str = "single",
    max_agent_rounds: int = 2,
) -> dict[str, Any]:
    """Build baseline summary for a completed batch run."""

    run_dir = Path(batch_result["run_dir"])
    evaluation = evaluate_batch_directory(run_dir)
    markdown_files = sorted((run_dir / "task_outputs").glob("*.md"))
    citation_results = [
        verify_citations_in_file(path, collection=collection) for path in markdown_files
    ]
    total_citations = sum(item.total_citations for item in citation_results)
    valid_citations = sum(item.valid_citations for item in citation_results)
    citation_rate = valid_citations / total_citations if total_citations else 0.0
    evaluations = evaluation["evaluations"]
    average_rule_score = (
        sum(_rule_score(item) for item in evaluations) / len(evaluations) if evaluations else 0.0
    )
    task_results = batch_result.get("results", [])
    successful_results = [item for item in task_results if item.get("status") == "success"]
    result_count = len(successful_results)
    average_agent_count = (
        sum(float(item.get("agent_count", 0) or 0) for item in successful_results) / result_count
        if result_count
        else 0.0
    )
    average_rounds = (
        sum(float(item.get("round_count", 0) or 0) for item in successful_results) / result_count
        if result_count
        else 0.0
    )
    average_citation_repair_count = (
        sum(float(item.get("citation_repair_count", 0) or 0) for item in successful_results)
        / result_count
        if result_count
        else 0.0
    )
    average_high_severity_findings = (
        sum(float(item.get("high_severity_findings", 0) or 0) for item in successful_results)
        / result_count
        if result_count
        else 0.0
    )
    average_run_duration_seconds = (
        sum(float(item.get("duration_seconds", 0) or 0) for item in successful_results)
        / result_count
        if result_count
        else 0.0
    )
    return {
        "commit_hash": _git_commit_hash(),
        "model_name": settings.ollama_model
        if settings.llm_provider == "ollama"
        else settings.openai_model,
        "embedding_model": settings.ollama_embedding_model
        if settings.embedding_provider == "ollama"
        else settings.openai_model,
        "mode": mode,
        "max_agent_rounds": max_agent_rounds,
        "rag_mode": rag_mode,
        "collection": collection,
        "task_count": batch_result["success"] + batch_result["failure"],
        "success_count": batch_result["success"],
        "failed_count": batch_result["failure"],
        "average_rule_score": average_rule_score,
        "average_citation_valid_rate": citation_rate,
        "average_insufficient_evidence_count": evaluation["summary"][
            "average_insufficient_evidence_count"
        ],
        "average_agent_count": average_agent_count,
        "average_rounds": average_rounds,
        "average_citation_repair_count": average_citation_repair_count,
        "average_high_severity_findings": average_high_severity_findings,
        "average_run_duration_seconds": average_run_duration_seconds,
    }
