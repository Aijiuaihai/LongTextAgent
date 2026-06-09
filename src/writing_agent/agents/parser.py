"""Utilities for parsing structured agent LLM output."""

import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from writing_agent.agents.errors import AgentParseError

ModelT = TypeVar("ModelT", bound=BaseModel)

FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(?P<body>.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json_from_markdown(raw_text: str) -> str:
    """Extract JSON from fenced markdown, or return the original text."""

    text = raw_text.strip()
    match = FENCED_JSON_RE.search(text)
    if match:
        return match.group("body").strip()
    return text


def normalize_llm_json(raw_text: str) -> str:
    """Normalize common LLM JSON wrappers into a raw JSON object string."""

    text = extract_json_from_markdown(raw_text).strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    raise AgentParseError("No JSON object found in agent output.")


def parse_json_object(raw_text: str) -> dict[str, Any]:
    """Parse a JSON object from direct JSON, fenced JSON, or explanatory text."""

    normalized = normalize_llm_json(raw_text)
    try:
        value = json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise AgentParseError(f"Invalid JSON object: {exc}") from exc
    if not isinstance(value, dict):
        raise AgentParseError(f"Expected JSON object, got {type(value).__name__}.")
    return value


def parse_pydantic_output(raw_text: str, model_cls: type[ModelT]) -> ModelT:
    """Parse and validate an agent response with a Pydantic model."""

    data = parse_json_object(raw_text)
    try:
        return model_cls.model_validate(data)
    except ValidationError as exc:
        raise AgentParseError(f"Output did not match {model_cls.__name__}: {exc}") from exc

