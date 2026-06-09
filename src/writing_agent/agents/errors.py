"""Agent structured-output errors."""


class AgentParseError(ValueError):
    """Raised when an agent LLM response cannot be parsed as the expected schema."""


class AgentRetryExceededError(RuntimeError):
    """Raised when structured retry attempts are exhausted."""


class AgentFallbackUsedWarning(Warning):
    """Warning marker used when an agent falls back to deterministic behavior."""

