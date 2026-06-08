"""Optional LLM-based document judge."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from writing_agent.config import Settings, get_settings
from writing_agent.evaluation.rubrics import DEFAULT_RUBRIC, LongFormJudgeResult
from writing_agent.graph.nodes import _extract_json, _extract_text
from writing_agent.llm import get_chat_model


def parse_judge_output(raw_output: str) -> dict[str, Any]:
    """Parse LLM judge output into a structured result payload."""

    try:
        result = LongFormJudgeResult.model_validate_json(_extract_json(raw_output))
        return {"parsed": result.model_dump(mode="json"), "raw_output": raw_output, "error": ""}
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        return {"parsed": None, "raw_output": raw_output, "error": str(exc)}


def judge_document_with_llm(
    file_path: Path | str,
    rubric: str = DEFAULT_RUBRIC,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Judge a markdown document with the configured chat model."""

    resolved_settings = settings or get_settings()
    markdown = Path(file_path).read_text(encoding="utf-8")
    model = get_chat_model(resolved_settings)
    messages = [
        ("system", rubric),
        (
            "user",
            "Evaluate this document. Return JSON only.\n\n"
            f"Document path: {file_path}\n\n{markdown[:24000]}",
        ),
    ]
    raw_output = _extract_text(model.invoke(messages))
    return parse_judge_output(raw_output)
