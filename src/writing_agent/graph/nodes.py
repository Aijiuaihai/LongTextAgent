"""LangGraph node functions for the long-form writing workflow."""

import json
from typing import Any

from pydantic import ValidationError

from writing_agent.graph.state import WritingState
from writing_agent.llm import format_connection_help, get_chat_model
from writing_agent.models import (
    FinalDocument,
    ReviewFinding,
    SectionDraft,
    SectionPlan,
    SourceNote,
    WritingPlan,
    WritingRequest,
)
from writing_agent.prompts.editor import build_editor_prompt
from writing_agent.prompts.planner import build_planner_prompt
from writing_agent.prompts.reviewer import build_reviewer_prompt
from writing_agent.prompts.writer import build_writer_prompt
from writing_agent.tools.document_loader import load_sources
from writing_agent.tools.export import export_docx, export_markdown


def _errors(state: WritingState) -> list[str]:
    return list(state.get("errors", []))


def _use_llm(state: WritingState) -> bool:
    return bool(state.get("use_llm", True))


def _request_from_state(state: WritingState) -> WritingRequest:
    value = state.get("request") or state.get("raw_request")
    if isinstance(value, WritingRequest):
        return value
    if isinstance(value, dict):
        return WritingRequest.model_validate(value)
    if isinstance(value, str):
        return WritingRequest(topic=value)
    raise ValueError("Workflow state must include `request` or `raw_request`.")


def _plan_from_state(state: WritingState) -> WritingPlan:
    value = state["plan"]
    if isinstance(value, WritingPlan):
        return value
    return WritingPlan.model_validate(value)


def _source_notes_from_state(state: WritingState) -> list[SourceNote]:
    notes = state.get("source_notes", [])
    return [
        note if isinstance(note, SourceNote) else SourceNote.model_validate(note)
        for note in notes
    ]


def _drafts_from_state(state: WritingState) -> list[SectionDraft]:
    drafts = state.get("section_drafts", [])
    return [
        draft if isinstance(draft, SectionDraft) else SectionDraft.model_validate(draft)
        for draft in drafts
    ]


def _findings_from_state(state: WritingState) -> list[ReviewFinding]:
    findings = state.get("review_findings", [])
    return [
        finding if isinstance(finding, ReviewFinding) else ReviewFinding.model_validate(finding)
        for finding in findings
    ]


def _request_summary(request: WritingRequest) -> str:
    return json.dumps(request.model_dump(mode="json"), ensure_ascii=False, indent=2)


def _source_summary(notes: list[SourceNote], max_chars: int = 6000) -> str:
    if not notes:
        return "No local source notes were provided."
    parts = [
        f"[{index}] {note.title}\nPath: {note.path}\nPreview: {note.content_preview}"
        for index, note in enumerate(notes, start=1)
    ]
    return "\n\n".join(parts)[:max_chars]


def _extract_text(message: Any) -> str:
    content = getattr(message, "content", message)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content)


def _extract_json(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:]
    start = min((idx for idx in [stripped.find("{"), stripped.find("[")] if idx >= 0), default=0)
    end = max(stripped.rfind("}"), stripped.rfind("]"))
    if end >= start:
        return stripped[start : end + 1]
    return stripped


def _invoke_model(messages: list[tuple[str, str]]) -> str:
    model = get_chat_model()
    try:
        return _extract_text(model.invoke(messages))
    except Exception as exc:  # pragma: no cover - integration guard
        raise RuntimeError(format_connection_help()) from exc


def _invoke_json(messages: list[tuple[str, str]], model_class: type[Any]) -> Any:
    model = get_chat_model()
    try:
        if hasattr(model, "with_structured_output"):
            structured_model = model.with_structured_output(model_class)
            result = structured_model.invoke(messages)
            return result if isinstance(result, model_class) else model_class.model_validate(result)
        text = _extract_text(model.invoke(messages))
    except Exception as exc:  # pragma: no cover - integration guard
        raise RuntimeError(format_connection_help()) from exc
    return model_class.model_validate_json(_extract_json(text))


def _fallback_plan(request: WritingRequest, notes: list[SourceNote]) -> WritingPlan:
    evidence_hint = (
        "Use provided local sources"
        if notes
        else "Mark unsupported claims as insufficient evidence"
    )
    return WritingPlan(
        title=request.topic,
        abstract_goal=(
            f"Create a {request.document_type.value} for {request.audience}, "
            f"target length {request.target_length}, style: {request.style}."
        ),
        sections=[
            SectionPlan(
                title="Background and Objectives",
                goal=(
                    "Clarify the writing context, objectives, audience needs, "
                    "and success criteria."
                ),
                key_points=["current context", "document objectives", "audience concerns"],
                evidence_needed=[evidence_hint],
                estimated_words=700,
            ),
            SectionPlan(
                title="Current Analysis and Requirements",
                goal="Analyze known facts, constraints, assumptions, and information gaps.",
                key_points=["known facts", "constraints", "open questions"],
                evidence_needed=[evidence_hint],
                estimated_words=900,
            ),
            SectionPlan(
                title="Proposed Approach",
                goal=(
                    "Describe the recommended structure, actions, milestones, "
                    "and responsibilities."
                ),
                key_points=["approach", "implementation steps", "dependencies"],
                evidence_needed=[evidence_hint],
                estimated_words=1100,
            ),
            SectionPlan(
                title="Risks, Controls, and Next Steps",
                goal="Summarize delivery risks, mitigation measures, and immediate next actions.",
                key_points=["risks", "controls", "next steps"],
                evidence_needed=[evidence_hint],
                estimated_words=700,
            ),
        ],
        risks=["Source coverage may be insufficient for evidence-heavy claims."],
    )


def parse_request_node(state: WritingState) -> WritingState:
    """Normalize the incoming request."""

    try:
        request = _request_from_state(state)
        return {"request": request, "current_step": "parse_request", "errors": _errors(state)}
    except (ValidationError, ValueError) as exc:
        return {"current_step": "parse_request", "errors": [*_errors(state), str(exc)]}


def load_sources_node(state: WritingState) -> WritingState:
    """Load local source notes from request paths."""

    request = _request_from_state(state)
    try:
        notes = load_sources(request.source_paths)
        return {"source_notes": notes, "current_step": "load_sources", "errors": _errors(state)}
    except Exception as exc:
        return {
            "source_notes": [],
            "current_step": "load_sources",
            "errors": [*_errors(state), str(exc)],
        }


def plan_outline_node(state: WritingState) -> WritingState:
    """Generate a structured writing plan."""

    request = _request_from_state(state)
    notes = _source_notes_from_state(state)
    awaiting_review = bool(state.get("pause_after_outline", False))
    if not _use_llm(state):
        return {
            "plan": _fallback_plan(request, notes),
            "current_step": "plan_outline",
            "awaiting_human_review": awaiting_review,
        }

    messages = build_planner_prompt(_request_summary(request), _source_summary(notes))
    try:
        plan = _invoke_json(messages, WritingPlan)
        return {
            "plan": plan,
            "current_step": "plan_outline",
            "errors": _errors(state),
            "awaiting_human_review": awaiting_review,
        }
    except Exception as exc:
        return {
            "plan": _fallback_plan(request, notes),
            "current_step": "plan_outline",
            "errors": [*_errors(state), str(exc)],
            "awaiting_human_review": awaiting_review,
        }


def write_sections_node(state: WritingState) -> WritingState:
    """Write each planned section independently."""

    request = _request_from_state(state)
    plan = _plan_from_state(state)
    notes = _source_notes_from_state(state)
    source_summary = _source_summary(notes)
    drafts: list[SectionDraft] = []
    errors = _errors(state)

    for section in plan.sections:
        if not _use_llm(state):
            source_line = (
                "Available source previews were considered."
                if notes
                else "Evidence note: insufficient evidence from local sources."
            )
            content = (
                f"## {section.title}\n\n"
                f"{section.goal}\n\n"
                f"Key points: {', '.join(section.key_points) or 'to be refined'}.\n\n"
                f"{source_line}\n"
            )
        else:
            try:
                messages = build_writer_prompt(
                    _request_summary(request),
                    section.model_dump_json(indent=2),
                    source_summary,
                )
                content = _invoke_model(messages)
            except Exception as exc:
                errors.append(str(exc))
                content = (
                    f"## {section.title}\n\n"
                    f"{section.goal}\n\n"
                    "Evidence note: insufficient evidence.\n"
                )
        drafts.append(
            SectionDraft(
                title=section.title,
                content=content,
                citations=[note.path for note in notes if note.content_preview],
                revision_notes=[],
            )
        )

    return {"section_drafts": drafts, "current_step": "write_sections", "errors": errors}


def review_document_node(state: WritingState) -> WritingState:
    """Review the generated section drafts."""

    request = _request_from_state(state)
    drafts = _drafts_from_state(state)
    draft_markdown = "\n\n".join(draft.content for draft in drafts)
    errors = _errors(state)

    if not _use_llm(state):
        findings = [
            ReviewFinding(
                issue_type="evidence_gap",
                severity="medium",
                location="document",
                comment="Offline smoke path cannot verify evidence coverage.",
                suggestion="Review source coverage before production use.",
            )
        ]
        return {"review_findings": findings, "current_step": "review_document", "errors": errors}

    try:
        text = _invoke_model(build_reviewer_prompt(_request_summary(request), draft_markdown))
        raw_findings = json.loads(_extract_json(text))
        findings = [ReviewFinding.model_validate(item) for item in raw_findings]
    except Exception as exc:
        errors.append(str(exc))
        findings = [
            ReviewFinding(
                issue_type="review_unavailable",
                severity="medium",
                location="document",
                comment="Automated review failed.",
                suggestion=(
                    "Manually review structure, terminology, repetitions, "
                    "and evidence gaps."
                ),
            )
        ]
    return {"review_findings": findings, "current_step": "review_document", "errors": errors}


def revise_document_node(state: WritingState) -> WritingState:
    """Revise section drafts according to review findings."""

    drafts = _drafts_from_state(state)
    findings = _findings_from_state(state)
    errors = _errors(state)
    if not findings:
        return {"section_drafts": drafts, "current_step": "revise_document", "errors": errors}

    if not _use_llm(state):
        revised = [
            draft.model_copy(
                update={"revision_notes": [finding.suggestion for finding in findings]}
            )
            for draft in drafts
        ]
        return {"section_drafts": revised, "current_step": "revise_document", "errors": errors}

    draft_markdown = "\n\n".join(draft.content for draft in drafts)
    findings_text = json.dumps(
        [finding.model_dump(mode="json") for finding in findings],
        ensure_ascii=False,
        indent=2,
    )
    try:
        revised_markdown = _invoke_model(build_editor_prompt(draft_markdown, findings_text))
        revised = [
            SectionDraft(
                title="Revised Draft",
                content=revised_markdown,
                citations=[],
                revision_notes=[finding.suggestion for finding in findings],
            )
        ]
    except Exception as exc:
        errors.append(str(exc))
        revised = drafts
    return {"section_drafts": revised, "current_step": "revise_document", "errors": errors}


def assemble_document_node(state: WritingState) -> WritingState:
    """Assemble revised drafts into a final markdown document."""

    request = _request_from_state(state)
    plan = _plan_from_state(state)
    drafts = _drafts_from_state(state)
    findings = _findings_from_state(state)
    body = "\n\n".join(draft.content.strip() for draft in drafts)
    markdown = (
        f"# {plan.title}\n\n"
        f"> Document type: {request.document_type.value}; audience: {request.audience}; "
        f"target length: {request.target_length}.\n\n"
        f"{body}\n"
    )
    final = FinalDocument(
        title=plan.title,
        markdown=markdown,
        metadata={
            "document_type": request.document_type.value,
            "audience": request.audience,
            "target_length": request.target_length,
            "review_findings": [finding.model_dump(mode="json") for finding in findings],
        },
    )
    return {
        "final_document": final,
        "current_step": "assemble_document",
        "errors": _errors(state),
        "awaiting_human_review": bool(state.get("pause_before_export", False)),
    }


def export_document_node(state: WritingState) -> WritingState:
    """Export the final markdown document."""

    value = state["final_document"]
    final = value if isinstance(value, FinalDocument) else FinalDocument.model_validate(value)
    output_dir = state.get("output_dir", "./outputs")
    output_format = state.get("output_format", "markdown")
    try:
        if output_format == "markdown":
            path = export_markdown(final.markdown, output_dir=output_dir, title=final.title)
        elif output_format == "docx":
            path = export_docx(final.markdown, output_dir=output_dir, title=final.title)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
        return {
            "output_path": str(path),
            "current_step": "export_document",
            "errors": _errors(state),
        }
    except Exception as exc:
        return {"current_step": "export_document", "errors": [*_errors(state), str(exc)]}
