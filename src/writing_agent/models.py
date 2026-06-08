"""Core Pydantic models for long-form writing workflows."""

from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentType(StrEnum):
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

