"""Workflow state definitions."""

from typing import TypedDict


class WritingState(TypedDict, total=False):
    """Mutable state passed between LangGraph nodes."""

    current_step: str
    errors: list[str]

