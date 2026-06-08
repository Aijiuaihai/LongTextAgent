"""LangGraph workflow construction and execution helpers."""

from datetime import datetime
from pathlib import Path

from writing_agent.checkpoints import get_checkpointer, update_thread_metadata
from writing_agent.config import Settings, get_settings
from writing_agent.graph.nodes import (
    assemble_document_node,
    export_document_node,
    final_review_node,
    load_sources_node,
    outline_review_node,
    parse_request_node,
    plan_outline_node,
    review_document_node,
    revise_document_node,
    write_sections_node,
)
from writing_agent.graph.state import WritingState
from writing_agent.models import WritingRequest


def _route_after_outline(state: WritingState) -> str:
    if state.get("pause_after_outline"):
        return "outline_review"
    return "write_sections"


def _route_after_assemble(state: WritingState) -> str:
    if state.get("pause_before_export"):
        return "final_review"
    return "export_document"


def build_workflow(
    settings: Settings | None = None,
    checkpointer: object | bool | None = None,
) -> object:
    """Build and compile the writing workflow graph."""

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("Install langgraph to build the writing workflow.") from exc

    builder = StateGraph(WritingState)
    builder.add_node("parse_request", parse_request_node)
    builder.add_node("load_sources", load_sources_node)
    builder.add_node("plan_outline", plan_outline_node)
    builder.add_node("outline_review", outline_review_node)
    builder.add_node("write_sections", write_sections_node)
    builder.add_node("review_document", review_document_node)
    builder.add_node("revise_document", revise_document_node)
    builder.add_node("assemble_document", assemble_document_node)
    builder.add_node("final_review", final_review_node)
    builder.add_node("export_document", export_document_node)

    builder.add_edge(START, "parse_request")
    builder.add_edge("parse_request", "load_sources")
    builder.add_edge("load_sources", "plan_outline")
    builder.add_conditional_edges(
        "plan_outline",
        _route_after_outline,
        {"outline_review": "outline_review", "write_sections": "write_sections"},
    )
    builder.add_edge("outline_review", "write_sections")
    builder.add_edge("write_sections", "review_document")
    builder.add_edge("review_document", "revise_document")
    builder.add_edge("revise_document", "assemble_document")
    builder.add_conditional_edges(
        "assemble_document",
        _route_after_assemble,
        {"final_review": "final_review", "export_document": "export_document"},
    )
    builder.add_edge("final_review", "export_document")
    builder.add_edge("export_document", END)

    if checkpointer is False:
        return builder.compile()
    if checkpointer is None:
        checkpointer = get_checkpointer(settings or get_settings())
    return builder.compile(checkpointer=checkpointer)


def generate_thread_id(prefix: str = "writing") -> str:
    """Generate a readable thread id."""

    return f"{prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def _state_from_result(
    app: object,
    config: dict[str, object],
    result: dict[str, object],
) -> WritingState:
    try:
        snapshot = app.get_state(config)  # type: ignore[attr-defined]
        state = dict(snapshot.values)
        if snapshot.interrupts:
            state["__interrupt__"] = result.get("__interrupt__", snapshot.interrupts)
            state["awaiting_human_review"] = True
        return state
    except Exception:
        return result  # type: ignore[return-value]


def run_writing_workflow(
    initial_state: WritingState | WritingRequest | dict[str, object],
    *,
    settings: Settings | None = None,
    checkpointer: object | bool | None = None,
    thread_id: str | None = None,
    use_llm: bool | None = None,
) -> WritingState:
    """Run the writing workflow and return the final state."""

    if isinstance(initial_state, WritingRequest):
        state: WritingState = {"request": initial_state}
    else:
        state = dict(initial_state)  # type: ignore[arg-type]

    if "request" not in state and "raw_request" not in state:
        state = {"request": state}
    if use_llm is not None:
        state["use_llm"] = use_llm

    resolved_settings = settings or get_settings()
    state.setdefault("output_dir", str(resolved_settings.output_dir))
    state.setdefault("output_format", "markdown")
    resolved_thread_id = thread_id or generate_thread_id()
    app = build_workflow(settings=resolved_settings, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": resolved_thread_id}}
    result = app.invoke(state, config=config)
    result = _state_from_result(app, config, result)
    if "output_path" in result:
        result["output_path"] = str(Path(result["output_path"]))
    result["thread_id"] = resolved_thread_id
    interrupted = bool(result.get("__interrupt__"))
    update_thread_metadata(
        resolved_thread_id,
        result,
        interrupted=interrupted,
        settings=resolved_settings,
    )
    return result


def resume_writing_workflow(
    thread_id: str,
    review_payload: object,
    *,
    settings: Settings | None = None,
    checkpointer: object | bool | None = None,
) -> WritingState:
    """Resume an interrupted workflow with human review input."""

    try:
        from langgraph.types import Command
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError("Install langgraph to resume interrupted workflows.") from exc

    resolved_settings = settings or get_settings()
    app = build_workflow(settings=resolved_settings, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke(Command(resume=review_payload), config=config)
    result = _state_from_result(app, config, result)
    if "output_path" in result:
        result["output_path"] = str(Path(result["output_path"]))
    result["thread_id"] = thread_id
    interrupted = bool(result.get("__interrupt__"))
    update_thread_metadata(thread_id, result, interrupted=interrupted, settings=resolved_settings)
    return result
