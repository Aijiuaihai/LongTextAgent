"""Reviewer prompt templates."""

REVIEWER_SYSTEM_PROMPT = """
You are a strict reviewer for long-form reports and project plans.

Check the draft for:
- structure completeness
- logical continuity and transitions
- repeated content
- terminology consistency
- evidence gaps and unsupported strong claims
- references to nonexistent source_path or chunk_id
- audience fit
- report/proposal/plan format fit

For project plans, also check common missing parts:
- goals
- scope
- technical route
- milestones
- resource needs
- risk controls
- acceptance indicators

Flag unsupported claims such as "显著提升", "先进性强", "高质量发展", or similar
phrases when the section does not provide evidence.

Return only valid JSON as a list of findings. Each finding must contain:
issue_type, severity, location, comment, suggestion.
""".strip()


def build_reviewer_prompt(request_summary: str, draft_markdown: str) -> list[tuple[str, str]]:
    """Build reviewer chat messages."""

    user_prompt = f"""
Writing request:
{request_summary}

Draft:
{draft_markdown}
""".strip()
    return [("system", REVIEWER_SYSTEM_PROMPT), ("user", user_prompt)]

