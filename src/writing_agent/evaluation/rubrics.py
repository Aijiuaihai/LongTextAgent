"""LLM Judge rubrics."""

from pydantic import BaseModel, Field


class LongFormJudgeResult(BaseModel):
    """Structured long-form document judge result."""

    structure_score: int = Field(ge=1, le=5)
    logic_score: int = Field(ge=1, le=5)
    evidence_score: int = Field(ge=1, le=5)
    specificity_score: int = Field(ge=1, le=5)
    audience_fit_score: int = Field(ge=1, le=5)
    actionability_score: int = Field(ge=1, le=5)
    risk_awareness_score: int = Field(ge=1, le=5)
    overall_score: int = Field(ge=1, le=5)
    comments: str
    revision_suggestions: list[str] = Field(default_factory=list)


DEFAULT_RUBRIC = """
Evaluate the document as a long-form report or project plan. Score each item
from 1 to 5:
- structure_score: structure completeness
- logic_score: logical continuity
- evidence_score: evidence sufficiency and traceability
- specificity_score: specificity and low filler
- audience_fit_score: target audience fit
- actionability_score: operational usefulness
- risk_awareness_score: risk identification and mitigation
- overall_score: overall quality

Return only valid JSON matching the schema. Do not rewrite the document.
""".strip()

