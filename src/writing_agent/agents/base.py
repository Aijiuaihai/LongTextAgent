"""Base classes and registry for writing agents."""

import time
from typing import Any

from pydantic import BaseModel

from writing_agent.agents.parser import parse_pydantic_output
from writing_agent.agents.protocols import AgentRunResult
from writing_agent.agents.retry import run_with_structured_retry


class AgentSpec(BaseModel):
    """Static agent metadata shown by CLI and Web."""

    name: str
    responsibility: str
    input_schema: str
    output_schema: str
    prompt_policy: str
    allowed_actions: list[str]
    forbidden_actions: list[str]


class BaseWritingAgent:
    """Base class for deterministic, schema-first agents."""

    spec: AgentSpec

    def run(self, *args: Any, **kwargs: Any) -> AgentRunResult:
        """Run the agent and wrap errors in a standard result."""

        started = time.perf_counter()
        try:
            output = self._run(*args, **kwargs)
            if isinstance(output, BaseModel):
                rendered = output.model_dump(mode="json")
            elif isinstance(output, list):
                rendered = [
                    item.model_dump(mode="json") if isinstance(item, BaseModel) else item
                    for item in output
                ]
            else:
                rendered = dict(output or {})
            return AgentRunResult(
                agent_name=self.spec.name,
                status="success",
                output={"value": rendered},
                duration_seconds=time.perf_counter() - started,
            )
        except Exception as exc:
            return AgentRunResult(
                agent_name=self.spec.name,
                status="failed",
                errors=[str(exc)],
                duration_seconds=time.perf_counter() - started,
            )

    def parse_structured_output(self, raw_text: str, model_cls: type[BaseModel]) -> BaseModel:
        """Parse one structured LLM response with the shared parser."""

        return parse_pydantic_output(raw_text, model_cls)

    def run_structured_retry(
        self,
        call_llm_fn: Any,
        output_model: type[BaseModel],
        *,
        max_retries: int = 2,
    ) -> AgentRunResult:
        """Run an LLM-backed agent step through the shared retry handler."""

        return run_with_structured_retry(
            self.spec.name,
            call_llm_fn,
            output_model,
            max_retries=max_retries,
        )

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


AGENT_SPECS: dict[str, AgentSpec] = {}


def register_agent(spec: AgentSpec) -> AgentSpec:
    """Register agent metadata."""

    AGENT_SPECS[spec.name] = spec
    return spec


def list_agent_specs() -> list[AgentSpec]:
    """List registered agents."""

    return list(AGENT_SPECS.values())


def get_agent_spec(name: str) -> AgentSpec | None:
    """Get one registered agent spec."""

    return AGENT_SPECS.get(name)
