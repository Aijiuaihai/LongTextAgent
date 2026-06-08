"""Core Pydantic models for long-form writing workflows."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Supported high-level document categories."""

    REPORT = "report"
    PROPOSAL = "proposal"
    PLAN = "plan"
    WEEKLY_REPORT = "weekly_report"
    RESEARCH_SUMMARY = "research_summary"
    CUSTOM = "custom"


class WritingRequest(BaseModel):
    """Normalized user writing request."""

    topic: str
    document_type: DocumentType = DocumentType.REPORT
    audience: str = "general readers"
    target_length: str = "3000 words"
    style: str = "formal and concise"
    constraints: list[str] = Field(default_factory=list)
    source_paths: list[str] = Field(default_factory=list)


class SectionPlan(BaseModel):
    """Executable plan for one document section."""

    title: str
    goal: str
    key_points: list[str] = Field(default_factory=list)
    evidence_needed: list[str] = Field(default_factory=list)
    estimated_words: int = Field(default=800, ge=0)


class WritingPlan(BaseModel):
    """Whole-document outline and planning risks."""

    title: str
    abstract_goal: str
    sections: list[SectionPlan] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class SourceNote(BaseModel):
    """Normalized local source content."""

    path: str
    title: str
    content_preview: str
    full_text: str


class DocumentChunk(BaseModel):
    """A retrievable source chunk."""

    source_path: str
    chunk_id: str
    title: str
    text: str


class SectionDraft(BaseModel):
    """Generated draft for a planned section."""

    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    revision_notes: list[str] = Field(default_factory=list)


class ReviewFinding(BaseModel):
    """A concrete review finding against the generated draft."""

    issue_type: str
    severity: str
    location: str
    comment: str
    suggestion: str


class FinalDocument(BaseModel):
    """Assembled final markdown document."""

    title: str
    markdown: str
    metadata: dict[str, Any] = Field(default_factory=dict)
