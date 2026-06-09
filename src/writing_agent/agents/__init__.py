"""Structured multi-agent roles for long-form writing."""

from writing_agent.agents.base import AgentSpec, get_agent_spec, list_agent_specs
from writing_agent.agents.citation_auditor import CitationAuditorAgent
from writing_agent.agents.editor import EditorAgent
from writing_agent.agents.evaluator import EvaluatorAgent
from writing_agent.agents.formatter import FormatterAgent
from writing_agent.agents.planner import PlannerAgent
from writing_agent.agents.researcher import ResearcherAgent
from writing_agent.agents.reviewer import ReviewerAgent
from writing_agent.agents.supervisor import SupervisorAgent
from writing_agent.agents.writer import WriterAgent

__all__ = [
    "AgentSpec",
    "CitationAuditorAgent",
    "EditorAgent",
    "EvaluatorAgent",
    "FormatterAgent",
    "PlannerAgent",
    "ResearcherAgent",
    "ReviewerAgent",
    "SupervisorAgent",
    "WriterAgent",
    "get_agent_spec",
    "list_agent_specs",
]
