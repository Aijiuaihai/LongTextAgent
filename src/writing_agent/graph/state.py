"""Workflow state definitions."""

from typing import Any, TypedDict

from writing_agent.models import (
    FinalDocument,
    ReviewFinding,
    SectionDraft,
    SourceNote,
    WritingPlan,
    WritingRequest,
)


class WritingState(TypedDict, total=False):
    """Mutable state passed between LangGraph nodes."""

    raw_request: str | dict[str, Any]
    request: WritingRequest | dict[str, Any]
    plan: WritingPlan | dict[str, Any]
    source_notes: list[SourceNote] | list[dict[str, str]]
    section_drafts: list[SectionDraft] | list[dict[str, Any]]
    review_findings: list[ReviewFinding] | list[dict[str, str]]
    final_document: FinalDocument | dict[str, Any]
    output_path: str
    use_llm: bool
    awaiting_human_review: bool
    current_step: str
    errors: list[str]
