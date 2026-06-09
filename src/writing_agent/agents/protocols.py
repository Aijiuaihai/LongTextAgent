"""Structured protocols for multi-agent writing workflows."""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from writing_agent.models import (
    FinalDocument,
    ReviewFinding,
    SectionPlan,
    WritingPlan,
    WritingRequest,
)
from writing_agent.rag.models import RetrievalResult


def utc_now() -> str:
    """Return an ISO UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


class AgentMessage(BaseModel):
    """Auditable message emitted by an agent."""

    role: str
    agent_name: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now)


class AgentRunResult(BaseModel):
    """Standard wrapper for an agent run."""

    agent_name: str
    status: Literal["success", "failed", "skipped"]
    output: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    duration_seconds: float = 0.0


class EvidencePack(BaseModel):
    """Retrieved evidence for one section."""

    section_title: str
    query: str
    results: list[RetrievalResult] = Field(default_factory=list)
    insufficient_evidence: bool = False
    notes: list[str] = Field(default_factory=list)


class SectionWritingTask(BaseModel):
    """Input contract for section writing."""

    section_plan: SectionPlan
    evidence_pack: EvidencePack
    style_constraints: list[str] = Field(default_factory=list)
    citation_policy: str = "[source: <source_path>#<chunk_id>]"


class SectionAgentDraft(BaseModel):
    """Section draft created by WriterAgent or EditorAgent."""

    title: str
    content: str
    citations: list[str] = Field(default_factory=list)
    evidence_used: list[str] = Field(default_factory=list)
    insufficient_evidence: bool = False


class CitationAuditReport(BaseModel):
    """Citation audit summary for one section."""

    section_title: str
    total_citations: int = 0
    valid_citations: int = 0
    invalid_citations: int = 0
    repaired_citations: int = 0
    downgraded_citations: int = 0
    findings: list[str] = Field(default_factory=list)


class SupervisorDecision(BaseModel):
    """Supervisor routing decision."""

    decision: Literal["edit", "format", "continue"]
    reason: str
    current_round: int
    high_severity_findings: int = 0
    invalid_citations: int = 0


class MultiAgentState(BaseModel):
    """Serializable state for a multi-agent workflow."""

    request: WritingRequest | dict[str, Any]
    plan: WritingPlan | dict[str, Any] | None = None
    evidence_packs: list[EvidencePack] = Field(default_factory=list)
    section_tasks: list[SectionWritingTask] = Field(default_factory=list)
    section_drafts: list[SectionAgentDraft] = Field(default_factory=list)
    citation_audits: list[CitationAuditReport] = Field(default_factory=list)
    review_findings: list[ReviewFinding] = Field(default_factory=list)
    edited_drafts: list[SectionAgentDraft] = Field(default_factory=list)
    final_document: FinalDocument | dict[str, Any] | None = None
    evaluation_result: dict[str, Any] = Field(default_factory=dict)
    supervisor_decisions: list[SupervisorDecision] = Field(default_factory=list)
    agent_messages: list[AgentMessage] = Field(default_factory=list)
    agent_results: list[AgentRunResult] = Field(default_factory=list)
    current_agent: str = ""
    current_round: int = 0
    max_rounds: int = 2
    errors: list[str] = Field(default_factory=list)

