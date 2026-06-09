"""Base classes and registry for writing agents."""

import time
from typing import Any

from pydantic import BaseModel

from writing_agent.agents.protocols import AgentRunResult


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

