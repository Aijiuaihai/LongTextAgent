"""Multi-model benchmark runner built on baseline runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from writing_agent.config import Settings, get_settings
from writing_agent.evaluation.batch import build_baseline_summary, run_batch_tasks


def utc_now() -> str:
    """Return an ISO UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


class BenchmarkCombination(BaseModel):
    """One model benchmark combination."""

    combo_id: str
    model: str
    embedding_model: str
    rag_mode: str
    mode: str
    max_agent_rounds: int


class BenchmarkResult(BaseModel):
    """Result for one benchmark combination."""

    combo_id: str
    model: str
    embedding_model: str
    rag_mode: str
    mode: str
    max_agent_rounds: int
    status: str
    baseline_summary_path: str = ""
    metrics: dict[str, Any] = Field(default_factory=dict)
    error_message: str = ""


class BenchmarkReport(BaseModel):
    """Complete benchmark report."""

    started_at: str
    finished_at: str
    total_combinations: int
    success_count: int
    failed_count: int
    combinations: list[BenchmarkResult]


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def plan_model_benchmark(
    *,
    models: str,
    embedding_models: str,
    rag_modes: str,
    mode: str,
    max_agent_rounds: int,
) -> list[BenchmarkCombination]:
    """Create the Cartesian product of benchmark dimensions."""

    combinations: list[BenchmarkCombination] = []
    for model in _split_csv(models):
        for embedding_model in _split_csv(embedding_models):
            for rag_mode in _split_csv(rag_modes):
                combo_id = (
                    f"{model}__{embedding_model}__{rag_mode}__{mode}__r{max_agent_rounds}"
                ).replace(":", "-").replace("/", "-")
                combinations.append(
                    BenchmarkCombination(
                        combo_id=combo_id,
                        model=model,
                        embedding_model=embedding_model,
                        rag_mode=rag_mode,
                        mode=mode,
                        max_agent_rounds=max_agent_rounds,
                    )
                )
    return combinations


def _settings_for_combo(settings: Settings, combo: BenchmarkCombination) -> Settings:
    return settings.model_copy(
        update={
            "ollama_model": combo.model,
            "openai_model": combo.model,
            "ollama_embedding_model": combo.embedding_model,
        }
    )


def _overall_score(metrics: dict[str, Any]) -> float:
    rule = float(metrics.get("average_rule_score", 0) or 0)
    citation = float(metrics.get("average_citation_valid_rate", 0) or 0)
    failure_penalty = float(metrics.get("failed_count", 0) or 0) * 0.1
    return max(0.0, (rule * 0.6) + (citation * 0.4) - failure_penalty)


def _write_summary_markdown(path: Path, results: list[BenchmarkResult]) -> None:
    rows = sorted(
        [result for result in results if result.status == "success"],
        key=lambda item: _overall_score(item.metrics),
        reverse=True,
    )
    lines = [
        "# Model Benchmark Summary",
        "",
        (
            "| combo | overall_score | citation_valid_rate | rule_score | "
            "failed | duration | errors | fallback |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for result in rows:
        metrics = result.metrics
        lines.append(
            "| "
            f"{result.combo_id} | "
            f"{_overall_score(metrics):.3f} | "
            f"{float(metrics.get('average_citation_valid_rate', 0) or 0):.3f} | "
            f"{float(metrics.get('average_rule_score', 0) or 0):.3f} | "
            f"{int(metrics.get('failed_count', 0) or 0)} | "
            f"{float(metrics.get('average_run_duration_seconds', 0) or 0):.3f} | "
            f"{float(metrics.get('average_agent_errors', 0) or 0):.3f} | "
            f"{float(metrics.get('average_fallback_count', 0) or 0):.3f} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_model_benchmark(
    *,
    tasks: Path | str,
    models: str,
    embedding_models: str,
    rag_modes: str,
    mode: str = "multi",
    max_agent_rounds: int = 2,
    output_dir: Path | str = "outputs/model_benchmark",
    dry_run: bool = False,
    fail_fast: bool = False,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Run or plan a model benchmark."""

    resolved_settings = settings or get_settings()
    combinations = plan_model_benchmark(
        models=models,
        embedding_models=embedding_models,
        rag_modes=rag_modes,
        mode=mode,
        max_agent_rounds=max_agent_rounds,
    )
    if dry_run:
        return {
            "dry_run": True,
            "total_combinations": len(combinations),
            "combinations": [combo.model_dump(mode="json") for combo in combinations],
        }

    root = Path(output_dir) / datetime.now().strftime("%Y%m%d-%H%M%S")
    per_combo = root / "per_combo"
    per_combo.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    results: list[BenchmarkResult] = []
    for combo in combinations:
        combo_dir = per_combo / combo.combo_id
        try:
            combo_dir.mkdir(parents=True, exist_ok=True)
            combo_settings = _settings_for_combo(resolved_settings, combo)
            batch_result = run_batch_tasks(
                tasks,
                output_dir=combo_dir,
                rag_mode=combo.rag_mode,
                collection="",
                output_format="markdown",
                mode=combo.mode,
                max_agent_rounds=combo.max_agent_rounds,
                settings=combo_settings,
                run_id="baseline",
            )
            summary = build_baseline_summary(
                batch_result=batch_result,
                rag_mode=combo.rag_mode,
                collection="",
                settings=combo_settings,
                mode=combo.mode,
                max_agent_rounds=combo.max_agent_rounds,
            )
            summary_path = combo_dir / "baseline_summary.json"
            summary_path.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            results.append(
                BenchmarkResult(
                    **combo.model_dump(mode="json"),
                    status="success",
                    baseline_summary_path=str(summary_path),
                    metrics=summary,
                )
            )
        except Exception as exc:
            results.append(
                BenchmarkResult(
                    **combo.model_dump(mode="json"),
                    status="failed",
                    error_message=str(exc),
                )
            )
            if fail_fast:
                break

    report = BenchmarkReport(
        started_at=started_at,
        finished_at=utc_now(),
        total_combinations=len(combinations),
        success_count=sum(1 for result in results if result.status == "success"),
        failed_count=sum(1 for result in results if result.status == "failed"),
        combinations=results,
    )
    report_path = root / "benchmark_report.json"
    report_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    summary_path = root / "benchmark_summary.md"
    _write_summary_markdown(summary_path, results)
    return {
        "dry_run": False,
        "run_dir": str(root),
        "benchmark_report": str(report_path),
        "benchmark_summary": str(summary_path),
        **report.model_dump(mode="json"),
    }
