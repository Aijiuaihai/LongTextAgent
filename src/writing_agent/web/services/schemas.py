"""Pydantic schemas used by the web console API."""

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from writing_agent.models import DocumentType, WritingRequest

JobStatus = Literal[
    "pending",
    "running",
    "interrupted",
    "completed",
    "failed",
    "cancel_requested",
    "cancelled",
]


def utc_now() -> str:
    """Return a UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


class JobCreateRequest(BaseModel):
    """JSON API payload for creating a writing job."""

    topic: str
    document_type: DocumentType = DocumentType.REPORT
    audience: str = "general readers"
    target_length: str = "3000 words"
    style: str = "formal and concise"
    source_paths: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    collection: str = ""
    rag: bool = True
    rag_mode: str = "hybrid"
    top_k: int = 5
    output_format: str = "markdown"
    docx_template: str = ""
    thread_id: str | None = None
    use_llm: bool = True
    mode: Literal["single", "multi"] = "single"
    max_agent_rounds: int = 2
    agent_debug: bool = False
    review_outline: bool = False
    review_final: bool = False

    def to_writing_request(self) -> WritingRequest:
        """Convert API payload to core WritingRequest."""

        return WritingRequest(
            topic=self.topic,
            document_type=self.document_type,
            audience=self.audience,
            target_length=self.target_length,
            style=self.style,
            constraints=self.constraints,
            source_paths=self.source_paths,
        )


class JobEvent(BaseModel):
    """One visible job event."""

    event: str
    message: str = ""
    step: str = ""
    created_at: str = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)


class JobRecord(BaseModel):
    """Persisted web job metadata."""

    job_id: str
    thread_id: str
    topic: str
    request: dict[str, Any]
    status: JobStatus = "pending"
    current_step: str = ""
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)
    output_files: dict[str, str] = Field(default_factory=dict)
    error_message: str = ""
    interrupt_payload: dict[str, Any] | list[Any] | str | None = None
    events: list[JobEvent] = Field(default_factory=list)
    agent_results: list[dict[str, Any]] = Field(default_factory=list)
    supervisor_decisions: list[dict[str, Any]] = Field(default_factory=list)
    evaluation_result: dict[str, Any] = Field(default_factory=dict)


class JobCreateResponse(BaseModel):
    """Response after creating a job."""

    job_id: str
    thread_id: str
    status: JobStatus
    created_at: str


class ResumeRequest(BaseModel):
    """Human review resume payload."""

    review: str | dict[str, Any]


class CollectionBuildRequest(BaseModel):
    """Create or rebuild a collection from paths."""

    collection: str
    source_paths: list[str]
    reset: bool = True


class RetrievalRequest(BaseModel):
    """Collection retrieval payload."""

    query: str
    top_k: int = 5


class CitationActionRequest(BaseModel):
    """Citation repair/verification payload."""

    collection: str | None = None
    mode: Literal["conservative", "llm_assisted"] = "conservative"


class EvaluateRequest(BaseModel):
    """Document evaluation payload."""

    llm_judge: bool = False
    verify_citations: bool = False
    collection: str | None = None
