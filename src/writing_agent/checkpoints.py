"""Checkpoint and thread metadata helpers."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from writing_agent.config import Settings, get_settings


def metadata_path(settings: Settings | None = None) -> Path:
    """Return the thread metadata path."""

    resolved = settings or get_settings()
    return resolved.output_dir / "thread_metadata.json"


def get_checkpointer(settings: Settings | None = None) -> object:
    """Create a SQLite checkpointer for LangGraph."""

    resolved = settings or get_settings()
    resolved.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(resolved.checkpoint_db_path, check_same_thread=False)
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError(
            "Install langgraph-checkpoint-sqlite to enable SQLite checkpoints."
        ) from exc

    saver = SqliteSaver(conn)
    saver.setup()
    return saver


def _read_metadata(settings: Settings | None = None) -> dict[str, dict[str, Any]]:
    path = metadata_path(settings)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_metadata(data: dict[str, dict[str, Any]], settings: Settings | None = None) -> None:
    path = metadata_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def summarize_state(thread_id: str, state: dict[str, Any], interrupted: bool) -> dict[str, Any]:
    """Build a compact thread summary from workflow state."""

    request = state.get("request") or {}
    if hasattr(request, "topic"):
        topic = request.topic
    elif isinstance(request, dict):
        topic = request.get("topic", "")
    else:
        topic = ""

    section_drafts = state.get("section_drafts") or []
    review_findings = state.get("review_findings") or []
    final_document = state.get("final_document")

    def _json_safe(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, list):
            return [_json_safe(item) for item in value]
        if isinstance(value, dict):
            return {str(key): _json_safe(item) for key, item in value.items()}
        return value

    return {
        "thread_id": thread_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "current_step": state.get("current_step", ""),
        "interrupted": interrupted,
        "request_topic": topic,
        "section_count": len(section_drafts),
        "review_finding_count": len(review_findings),
        "final_document_exists": final_document is not None,
        "output_path": state.get("output_path", ""),
        "mode": state.get("mode", "multi" if state.get("agent_results") else "single"),
        "agent_results": _json_safe(state.get("agent_results", [])),
        "supervisor_decisions": _json_safe(state.get("supervisor_decisions", [])),
        "evaluation_result": _json_safe(state.get("evaluation_result", {})),
    }


def update_thread_metadata(
    thread_id: str,
    state: dict[str, Any],
    *,
    interrupted: bool,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Persist a compact thread metadata record."""

    data = _read_metadata(settings)
    data[thread_id] = summarize_state(thread_id, state, interrupted)
    _write_metadata(data, settings)
    return data[thread_id]


def list_threads(settings: Settings | None = None) -> list[dict[str, Any]]:
    """List known workflow threads."""

    data = _read_metadata(settings)
    return sorted(data.values(), key=lambda item: item.get("updated_at", ""), reverse=True)


def inspect_thread(thread_id: str, settings: Settings | None = None) -> dict[str, Any] | None:
    """Return a single thread metadata summary."""

    return _read_metadata(settings).get(thread_id)


def delete_thread(thread_id: str, settings: Settings | None = None) -> bool:
    """Delete a thread metadata record and best-effort checkpoint state."""

    resolved = settings or get_settings()
    data = _read_metadata(resolved)
    existed = thread_id in data
    if existed:
        del data[thread_id]
        _write_metadata(data, resolved)

    try:
        saver = get_checkpointer(resolved)
        if hasattr(saver, "delete_thread"):
            saver.delete_thread(thread_id)
    except Exception:
        pass
    return existed
