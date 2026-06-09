"""Structured retry helpers for LLM-backed agents."""

import time
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from writing_agent.agents.errors import AgentParseError
from writing_agent.agents.parser import parse_pydantic_output
from writing_agent.agents.protocols import AgentRunResult

ModelT = TypeVar("ModelT", bound=BaseModel)


def _call_llm(call_llm_fn: Callable[..., str], prompt: str | None) -> str:
    try:
        return call_llm_fn(prompt)
    except TypeError:
        return call_llm_fn()


def _default_repair_prompt(agent_name: str, raw_text: str, error: str) -> str:
    return (
        f"Agent {agent_name} returned invalid structured output.\n"
        f"Parse error: {error}\n"
        "Return only a valid JSON object matching the requested schema. "
        "Do not include markdown fences or explanations.\n"
        f"Original output:\n{raw_text}"
    )


def run_with_structured_retry(
    agent_name: str,
    call_llm_fn: Callable[..., str],
    output_model: type[ModelT],
    max_retries: int = 2,
    repair_prompt_fn: Callable[[str, str, str], str] | None = None,
) -> AgentRunResult:
    """Call an LLM function until its output validates or retry attempts are exhausted."""

    started = time.perf_counter()
    errors: list[str] = []
    warnings: list[str] = []
    prompt: str | None = None
    attempts = max(1, max_retries + 1)
    raw_text = ""
    for attempt in range(attempts):
        raw_text = _call_llm(call_llm_fn, prompt)
        try:
            parsed = parse_pydantic_output(raw_text, output_model)
            if attempt:
                warnings.append(f"structured retry succeeded after {attempt} repair attempt(s)")
            return AgentRunResult(
                agent_name=agent_name,
                status="success",
                output={"value": parsed.model_dump(mode="json"), "raw": raw_text},
                warnings=warnings,
                errors=errors,
                duration_seconds=time.perf_counter() - started,
            )
        except AgentParseError as exc:
            errors.append(str(exc))
            if attempt < attempts - 1:
                repair = repair_prompt_fn or _default_repair_prompt
                prompt = repair(agent_name, raw_text, str(exc))

    try:
        fallback = output_model.model_validate({})
    except Exception:
        return AgentRunResult(
            agent_name=agent_name,
            status="failed",
            output={"raw": raw_text},
            warnings=warnings,
            errors=errors + ["structured retry exhausted"],
            duration_seconds=time.perf_counter() - started,
        )
    warnings.append("fallback output used after structured retry exhaustion")
    return AgentRunResult(
        agent_name=agent_name,
        status="success",
        output={"value": fallback.model_dump(mode="json"), "raw": raw_text},
        warnings=warnings,
        errors=errors,
        duration_seconds=time.perf_counter() - started,
    )
