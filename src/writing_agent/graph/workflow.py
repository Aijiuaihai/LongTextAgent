"""LangGraph workflow construction and execution helpers."""

import sqlite3
from pathlib import Path
from uuid import uuid4

from writing_agent.config import Settings, get_settings
from writing_agent.graph.nodes import (
    assemble_document_node,
    export_document_node,
    load_sources_node,
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
        return "__end__"
    return "write_sections"


def _route_after_assemble(state: WritingState) -> str:
    if state.get("pause_before_export"):
        return "__end__"
    return "export_document"


def _build_sqlite_checkpointer(settings: Settings) -> object:
    settings.checkpoint_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.checkpoint_db_path, check_same_thread=False)
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise RuntimeError(
            "Install langgraph-checkpoint-sqlite to enable SQLite checkpoints."
        ) from exc

    saver = SqliteSaver(conn)
    saver.setup()
    return saver


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
    builder.add_node("write_sections", write_sections_node)
    builder.add_node("review_document", review_document_node)
    builder.add_node("revise_document", revise_document_node)
    builder.add_node("assemble_document", assemble_document_node)
    builder.add_node("export_document", export_document_node)

    builder.add_edge(START, "parse_request")
    builder.add_edge("parse_request", "load_sources")
    builder.add_edge("load_sources", "plan_outline")
    builder.add_conditional_edges(
        "plan_outline",
        _route_after_outline,
        {"write_sections": "write_sections", "__end__": END},
    )
    builder.add_edge("write_sections", "review_document")
    builder.add_edge("review_document", "revise_document")
    builder.add_edge("revise_document", "assemble_document")
    builder.add_conditional_edges(
        "assemble_document",
        _route_after_assemble,
        {"export_document": "export_document", "__end__": END},
    )
    builder.add_edge("export_document", END)

    if checkpointer is False:
        return builder.compile()
    if checkpointer is None:
        checkpointer = _build_sqlite_checkpointer(settings or get_settings())
    return builder.compile(checkpointer=checkpointer)


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

    app = build_workflow(settings=settings, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id or str(uuid4())}}
    result = app.invoke(state, config=config)
    if "output_path" in result:
        result["output_path"] = str(Path(result["output_path"]))
    return result
