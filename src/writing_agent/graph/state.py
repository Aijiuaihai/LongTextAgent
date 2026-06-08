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
    human_review_notes: Any
    rag_enabled: bool
    rag_mode: str
    rag_top_k: int
    rag_collection: str
    rag_rebuild_index: bool
    output_path: str
    output_paths: dict[str, str]
    output_format: str
    output_dir: str
    thread_id: str
    use_llm: bool
    pause_after_outline: bool
    pause_before_export: bool
    awaiting_human_review: bool
    current_step: str
    errors: list[str]
