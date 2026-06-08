"""Lightweight trace context helpers."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from writing_agent.config import Settings
from writing_agent.observability.langsmith import configure_langsmith, is_langsmith_enabled


@contextmanager
def trace_workflow_run(
    run_name: str,
    metadata: dict[str, Any],
    settings: Settings | None = None,
) -> Iterator[dict[str, Any]]:
    """No-op compatible trace context for workflow runs."""

    warnings = configure_langsmith(settings)
    yield {
        "run_name": run_name,
        "metadata": metadata,
        "enabled": is_langsmith_enabled(settings),
        "warnings": warnings,
    }
