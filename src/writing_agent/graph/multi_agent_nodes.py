"""LangGraph nodes for the bounded multi-agent writing workflow."""

from typing import Any

from writing_agent.agents import (
    CitationAuditorAgent,
    EditorAgent,
    EvaluatorAgent,
    FormatterAgent,
    PlannerAgent,
    ResearcherAgent,
    ReviewerAgent,
    SupervisorAgent,
    WriterAgent,
)
from writing_agent.agents.protocols import (
    AgentMessage,
    AgentRunResult,
    CitationAuditReport,
    EvidencePack,
    SectionAgentDraft,
    SectionWritingTask,
    SupervisorDecision,
)
from writing_agent.config import get_settings
from writing_agent.models import (
    FinalDocument,
    ReviewFinding,
    SourceNote,
    WritingPlan,
    WritingRequest,
)
from writing_agent.tools.document_loader import load_sources
from writing_agent.tools.export import export_docx, export_docx_from_template, export_markdown


def _request(state: dict[str, Any]) -> WritingRequest:
    value = state["request"]
    return value if isinstance(value, WritingRequest) else WritingRequest.model_validate(value)


def _plan(state: dict[str, Any]) -> WritingPlan:
    value = state["plan"]
    return value if isinstance(value, WritingPlan) else WritingPlan.model_validate(value)


def _source_notes(state: dict[str, Any]) -> list[SourceNote]:
    return [
        item if isinstance(item, SourceNote) else SourceNote.model_validate(item)
        for item in state.get("source_notes", [])
    ]


def _drafts(state: dict[str, Any], key: str = "section_drafts") -> list[SectionAgentDraft]:
    return [
        item if isinstance(item, SectionAgentDraft) else SectionAgentDraft.model_validate(item)
        for item in state.get(key, [])
    ]


def _audits(state: dict[str, Any]) -> list[CitationAuditReport]:
    return [
        item if isinstance(item, CitationAuditReport) else CitationAuditReport.model_validate(item)
        for item in state.get("citation_audits", [])
    ]


def _findings(state: dict[str, Any]) -> list[ReviewFinding]:
    return [
        item if isinstance(item, ReviewFinding) else ReviewFinding.model_validate(item)
        for item in state.get("review_findings", [])
    ]


def _messages(state: dict[str, Any]) -> list[AgentMessage]:
    return [
        item if isinstance(item, AgentMessage) else AgentMessage.model_validate(item)
        for item in state.get("agent_messages", [])
    ]


def _results(state: dict[str, Any]) -> list[AgentRunResult]:
    return [
        item if isinstance(item, AgentRunResult) else AgentRunResult.model_validate(item)
        for item in state.get("agent_results", [])
    ]


def _record(
    state: dict[str, Any],
    *,
    agent: str,
    content: str,
    output: Any,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    messages = _messages(state)
    results = _results(state)
    messages.append(AgentMessage(role="agent", agent_name=agent, content=content))
    rendered = (
        output.model_dump(mode="json")
        if hasattr(output, "model_dump")
        else [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in output
        ]
        if isinstance(output, list)
        else output
    )
    results.append(
        AgentRunResult(
            agent_name=agent,
            status="success",
            output={"value": rendered},
            warnings=warnings or [],
        )
    )
    return {"agent_messages": messages, "agent_results": results, "current_agent": agent}


def supervisor_start_node(state: dict[str, Any]) -> dict[str, Any]:
    """Initialize multi-agent state."""

    return {
        "current_agent": "supervisor",
        "current_round": int(state.get("current_round", 0)),
        "max_rounds": int(state.get("max_rounds", 2)),
        "errors": list(state.get("errors", [])),
        "agent_messages": _messages(state),
        "agent_results": _results(state),
    }


def load_sources_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Load sources for multi-agent mode."""

    request = _request(state)
    try:
        notes = load_sources(request.source_paths)
        return {"source_notes": notes, "current_agent": "researcher"}
    except Exception as exc:
        return {"source_notes": [], "errors": [*state.get("errors", []), str(exc)]}


def planner_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run PlannerAgent."""

    plan = PlannerAgent()._run(_request(state), _source_notes(state))
    record = _record(state, agent="planner", content="Generated writing plan.", output=plan)
    return {**record, "plan": plan}


def researcher_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run ResearcherAgent for every section."""

    notes = _source_notes(state)
    top_k = int(state.get("rag_top_k", 5))
    packs: list[EvidencePack] = []
    tasks: list[SectionWritingTask] = []
    for section in _plan(state).sections:
        pack = ResearcherAgent()._run(section, notes, top_k=top_k)
        packs.append(pack)
        tasks.append(
            SectionWritingTask(
                section_plan=section,
                evidence_pack=pack,
                style_constraints=[_request(state).style],
            )
        )
    record = _record(
        state,
        agent="researcher",
        content=f"Retrieved evidence for {len(packs)} sections.",
        output=packs,
    )
    return {**record, "evidence_packs": packs, "section_tasks": tasks}


def writer_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run WriterAgent for every section task."""

    drafts = [
        WriterAgent()._run(
            task
            if isinstance(task, SectionWritingTask)
            else SectionWritingTask.model_validate(task)
        )
        for task in state.get("section_tasks", [])
    ]
    record = _record(
        state,
        agent="writer",
        content=f"Wrote {len(drafts)} section drafts.",
        output=drafts,
    )
    return {**record, "section_drafts": drafts}


def citation_auditor_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run CitationAuditorAgent."""

    collection = str(state.get("rag_collection", "") or "") or None
    drafts = _drafts(state, "edited_drafts") or _drafts(state)
    audits = [CitationAuditorAgent()._run(draft, collection=collection) for draft in drafts]
    record = _record(
        state,
        agent="citation_auditor",
        content="Completed citation audit.",
        output=audits,
    )
    return {**record, "citation_audits": audits}


def reviewer_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run ReviewerAgent."""

    drafts = _drafts(state, "edited_drafts") or _drafts(state)
    findings = ReviewerAgent()._run(_request(state), drafts, _audits(state))
    record = _record(
        state,
        agent="reviewer",
        content=f"Produced {len(findings)} findings.",
        output=findings,
    )
    return {**record, "review_findings": findings}


def supervisor_review_decision_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run bounded SupervisorAgent routing."""

    decision = SupervisorAgent()._run(
        current_round=int(state.get("current_round", 0)),
        max_rounds=int(state.get("max_rounds", 2)),
        audits=_audits(state),
        findings=_findings(state),
    )
    decisions = [
        item if isinstance(item, SupervisorDecision) else SupervisorDecision.model_validate(item)
        for item in state.get("supervisor_decisions", [])
    ]
    decisions.append(decision)
    record = _record(
        state,
        agent="supervisor",
        content=decision.reason,
        output=decision,
    )
    return {**record, "supervisor_decisions": decisions}


def route_after_supervisor(state: dict[str, Any]) -> str:
    """Route after supervisor decision."""

    decisions = state.get("supervisor_decisions", [])
    latest = decisions[-1] if decisions else None
    decision = (
        latest
        if isinstance(latest, SupervisorDecision)
        else SupervisorDecision.model_validate(latest)
        if latest
        else None
    )
    if decision and decision.decision == "edit":
        return "editor_agent"
    return "formatter_agent"


def editor_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run EditorAgent for one bounded revision pass."""

    edited = EditorAgent()._run(_drafts(state), _findings(state))
    record = _record(
        state,
        agent="editor",
        content="Applied bounded edits.",
        output=edited,
    )
    return {
        **record,
        "edited_drafts": edited,
        "current_round": int(state.get("current_round", 0)) + 1,
    }


def formatter_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run FormatterAgent."""

    drafts = _drafts(state, "edited_drafts") or _drafts(state)
    metadata = {
        "mode": "multi",
        "agent_results": [result.model_dump(mode="json") for result in _results(state)],
        "supervisor_decisions": [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in state.get("supervisor_decisions", [])
        ],
        "unresolved_findings": [finding.model_dump(mode="json") for finding in _findings(state)],
        "rag_mode": state.get("rag_mode", "hybrid"),
        "collection": state.get("rag_collection", ""),
        "thread_id": state.get("thread_id", ""),
    }
    document = FormatterAgent()._run(_request(state), _plan(state), drafts, metadata=metadata)
    record = _record(
        state,
        agent="formatter",
        content="Assembled final document.",
        output=document,
    )
    return {**record, "final_document": document}


def evaluator_agent_node(state: dict[str, Any]) -> dict[str, Any]:
    """Run EvaluatorAgent."""

    value = state["final_document"]
    document = value if isinstance(value, FinalDocument) else FinalDocument.model_validate(value)
    collection = str(state.get("rag_collection", "") or "") or None
    evaluation = EvaluatorAgent()._run(document, collection=collection)
    record = _record(
        state,
        agent="evaluator",
        content="Completed final evaluation.",
        output=evaluation,
    )
    return {**record, "evaluation_result": evaluation}


def export_multi_agent_document_node(state: dict[str, Any]) -> dict[str, Any]:
    """Export multi-agent final document."""

    value = state["final_document"]
    final = value if isinstance(value, FinalDocument) else FinalDocument.model_validate(value)
    output_dir = state.get("output_dir", "./outputs")
    output_format = state.get("output_format", "markdown")
    docx_template = str(state.get("docx_template", "") or "")
    settings = get_settings()
    metadata = {
        **final.metadata,
        "model_name": settings.ollama_model
        if settings.llm_provider == "ollama"
        else settings.openai_model,
    }
    if output_format == "markdown":
        path = export_markdown(final.markdown, output_dir=output_dir, title=final.title)
        output_paths = {"markdown": str(path)}
    elif output_format == "docx":
        if docx_template:
            path, _warnings = export_docx_from_template(
                final.markdown,
                template_path=docx_template,
                output_dir=output_dir,
                title=final.title,
                metadata=metadata,
            )
        else:
            path = export_docx(
                final.markdown,
                output_dir=output_dir,
                title=final.title,
                metadata=metadata,
            )
        output_paths = {"docx": str(path)}
    elif output_format == "both":
        markdown_path = export_markdown(final.markdown, output_dir=output_dir, title=final.title)
        if docx_template:
            docx_path, _warnings = export_docx_from_template(
                final.markdown,
                template_path=docx_template,
                output_dir=output_dir,
                title=final.title,
                metadata=metadata,
            )
        else:
            docx_path = export_docx(
                final.markdown,
                output_dir=output_dir,
                title=final.title,
                metadata=metadata,
            )
        path = markdown_path
        output_paths = {"markdown": str(markdown_path), "docx": str(docx_path)}
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    return {
        "output_path": str(path),
        "output_paths": output_paths,
        "current_step": "multi_agent_export",
        "current_agent": "formatter",
    }
