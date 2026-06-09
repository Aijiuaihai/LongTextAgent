"""Multi-agent LangGraph workflow construction and execution."""

from pathlib import Path
from typing import Any

from typing_extensions import TypedDict

from writing_agent.checkpoints import get_checkpointer, update_thread_metadata
from writing_agent.config import Settings, get_settings
from writing_agent.graph.multi_agent_nodes import (
    citation_auditor_agent_node,
    editor_agent_node,
    evaluator_agent_node,
    export_multi_agent_document_node,
    formatter_agent_node,
    human_review_final_node,
    human_review_outline_node,
    load_sources_agent_node,
    planner_agent_node,
    researcher_agent_node,
    reviewer_agent_node,
    route_after_supervisor,
    supervisor_review_decision_node,
    supervisor_start_node,
    writer_agent_node,
)
from writing_agent.graph.workflow import generate_thread_id
from writing_agent.models import WritingRequest


class MultiAgentGraphState(TypedDict, total=False):
    """Mutable state for the multi-agent LangGraph runtime."""

    request: WritingRequest | dict[str, Any]
    plan: object
    source_notes: list[object]
    evidence_packs: list[object]
    section_tasks: list[object]
    section_drafts: list[object]
    citation_audits: list[object]
    review_findings: list[object]
    edited_drafts: list[object]
    final_document: object
    evaluation_result: dict[str, Any]
    supervisor_decisions: list[object]
    agent_messages: list[object]
    agent_results: list[object]
    current_agent: str
    current_round: int
    max_rounds: int
    output_path: str
    output_paths: dict[str, str]
    output_format: str
    output_dir: str
    docx_template: str
    thread_id: str
    rag_enabled: bool
    rag_mode: str
    rag_top_k: int
    rag_collection: str
    review_outline: bool
    review_final: bool
    errors: list[str]


def _route_after_planner(state: MultiAgentGraphState) -> str:
    return "human_review_outline" if state.get("review_outline") else "researcher_agent"


def _route_after_formatter(state: MultiAgentGraphState) -> str:
    return "human_review_final" if state.get("review_final") else "evaluator_agent"


def build_multi_agent_workflow(
    settings: Settings | None = None,
    checkpointer: object | bool | None = None,
) -> object:
    """Build and compile the bounded multi-agent workflow."""

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install langgraph to build the multi-agent workflow.") from exc

    builder = StateGraph(MultiAgentGraphState)
    builder.add_node("supervisor_start", supervisor_start_node)
    builder.add_node("load_sources", load_sources_agent_node)
    builder.add_node("planner_agent", planner_agent_node)
    builder.add_node("human_review_outline", human_review_outline_node)
    builder.add_node("researcher_agent", researcher_agent_node)
    builder.add_node("writer_agent", writer_agent_node)
    builder.add_node("citation_auditor_agent", citation_auditor_agent_node)
    builder.add_node("reviewer_agent", reviewer_agent_node)
    builder.add_node("supervisor_review_decision", supervisor_review_decision_node)
    builder.add_node("editor_agent", editor_agent_node)
    builder.add_node("formatter_agent", formatter_agent_node)
    builder.add_node("human_review_final", human_review_final_node)
    builder.add_node("evaluator_agent", evaluator_agent_node)
    builder.add_node("export_document", export_multi_agent_document_node)

    builder.add_edge(START, "supervisor_start")
    builder.add_edge("supervisor_start", "load_sources")
    builder.add_edge("load_sources", "planner_agent")
    builder.add_conditional_edges(
        "planner_agent",
        _route_after_planner,
        {"human_review_outline": "human_review_outline", "researcher_agent": "researcher_agent"},
    )
    builder.add_edge("human_review_outline", "researcher_agent")
    builder.add_edge("researcher_agent", "writer_agent")
    builder.add_edge("writer_agent", "citation_auditor_agent")
    builder.add_edge("citation_auditor_agent", "reviewer_agent")
    builder.add_edge("reviewer_agent", "supervisor_review_decision")
    builder.add_conditional_edges(
        "supervisor_review_decision",
        route_after_supervisor,
        {"editor_agent": "editor_agent", "formatter_agent": "formatter_agent"},
    )
    builder.add_edge("editor_agent", "citation_auditor_agent")
    builder.add_conditional_edges(
        "formatter_agent",
        _route_after_formatter,
        {"human_review_final": "human_review_final", "evaluator_agent": "evaluator_agent"},
    )
    builder.add_edge("human_review_final", "evaluator_agent")
    builder.add_edge("evaluator_agent", "export_document")
    builder.add_edge("export_document", END)

    if checkpointer is False:
        return builder.compile()
    if checkpointer is None:
        checkpointer = get_checkpointer(settings or get_settings())
    return builder.compile(checkpointer=checkpointer)


def _state_from_result(
    app: object,
    config: dict[str, object],
    result: dict[str, object],
) -> MultiAgentGraphState:
    try:
        snapshot = app.get_state(config)  # type: ignore[attr-defined]
        state = dict(snapshot.values)
        if snapshot.interrupts:
            state["__interrupt__"] = result.get("__interrupt__", snapshot.interrupts)
            state["awaiting_human_review"] = True
        return state  # type: ignore[return-value]
    except Exception:
        return result  # type: ignore[return-value]


def run_multi_agent_workflow(
    initial_state: MultiAgentGraphState | WritingRequest | dict[str, object],
    *,
    settings: Settings | None = None,
    checkpointer: object | bool | None = None,
    thread_id: str | None = None,
    max_rounds: int = 2,
) -> MultiAgentGraphState:
    """Run multi-agent workflow and return final state."""

    if isinstance(initial_state, WritingRequest):
        state: MultiAgentGraphState = {"request": initial_state}
    else:
        state = dict(initial_state)  # type: ignore[arg-type]
    if "request" not in state:
        state = {"request": state}  # type: ignore[assignment]
    resolved_settings = settings or get_settings()
    resolved_thread_id = thread_id or generate_thread_id("multi-writing")
    state.setdefault("output_dir", str(resolved_settings.output_dir))
    state.setdefault("output_format", "markdown")
    state.setdefault("rag_enabled", True)
    state.setdefault("rag_mode", "hybrid")
    state.setdefault("rag_top_k", 5)
    state.setdefault("max_rounds", max_rounds)
    state["thread_id"] = resolved_thread_id
    app = build_multi_agent_workflow(settings=resolved_settings, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": resolved_thread_id}}
    result = app.invoke(state, config=config)
    result = _state_from_result(app, config, result)
    if "output_path" in result:
        result["output_path"] = str(Path(result["output_path"]))
        result.setdefault("current_step", "multi_agent_export")
    result["thread_id"] = resolved_thread_id
    update_thread_metadata(
        resolved_thread_id,
        result,
        interrupted=bool(result.get("__interrupt__")),
        settings=resolved_settings,
    )
    return result


def resume_multi_agent_workflow(
    thread_id: str,
    review_payload: object,
    *,
    settings: Settings | None = None,
    checkpointer: object | bool | None = None,
) -> MultiAgentGraphState:
    """Resume an interrupted multi-agent workflow with human review input."""

    try:
        from langgraph.types import Command
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Install langgraph to resume multi-agent workflows.") from exc

    resolved_settings = settings or get_settings()
    app = build_multi_agent_workflow(settings=resolved_settings, checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    result = app.invoke(Command(resume=review_payload), config=config)
    result = _state_from_result(app, config, result)
    if "output_path" in result:
        result["output_path"] = str(Path(result["output_path"]))
        result.setdefault("current_step", "multi_agent_export")
    result["thread_id"] = thread_id
    interrupted = bool(result.get("__interrupt__"))
    update_thread_metadata(thread_id, result, interrupted=interrupted, settings=resolved_settings)
    return result
