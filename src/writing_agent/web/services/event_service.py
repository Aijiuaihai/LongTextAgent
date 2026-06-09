"""Local event storage and SSE helpers."""

import json
import time
from collections.abc import Iterator
from pathlib import Path

from writing_agent.config import Settings, get_settings
from writing_agent.web.services.schemas import JobEvent


def event_dir(settings: Settings | None = None) -> Path:
    """Return the local event storage directory."""

    resolved = settings or get_settings()
    return resolved.output_dir / "web_jobs" / "events"


def event_path(job_id: str, settings: Settings | None = None) -> Path:
    """Return JSON event path for one job."""

    return event_dir(settings) / f"{job_id}.json"


def _atomic_write(path: Path, payload: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def list_events(job_id: str, settings: Settings | None = None) -> list[JobEvent]:
    """List events for one job."""

    path = event_path(job_id, settings)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [JobEvent.model_validate(item) for item in data]


def append_event(
    job_id: str,
    event: str | JobEvent,
    *,
    message: str = "",
    step: str = "",
    settings: Settings | None = None,
    payload: dict[str, object] | None = None,
) -> JobEvent:
    """Append a local job event."""

    item = (
        event
        if isinstance(event, JobEvent)
        else JobEvent(event=event, message=message, step=step, payload=payload or {})
    )
    events = list_events(job_id, settings)
    events.append(item)
    _atomic_write(
        event_path(job_id, settings),
        [saved.model_dump(mode="json") for saved in events],
    )
    return item


def stream_events(
    job_id: str,
    *,
    settings: Settings | None = None,
    poll_interval: float = 0.5,
    idle_timeout: float = 30.0,
) -> Iterator[str]:
    """Yield existing and new events as Server-Sent Events."""

    sent = 0
    started = time.monotonic()
    while True:
        events = list_events(job_id, settings)
        for event in events[sent:]:
            yield (
                f"event: {event.event}\n"
                f"data: {event.model_dump_json()}\n\n"
            )
        sent = len(events)
        if events and events[-1].event in {"completed", "failed", "cancelled", "interrupted"}:
            break
        if time.monotonic() - started > idle_timeout:
            yield "event: ping\ndata: {}\n\n"
            break
        time.sleep(poll_interval)

