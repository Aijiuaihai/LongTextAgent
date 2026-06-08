"""Reviewer prompt templates."""

REVIEWER_SYSTEM_PROMPT = """
You are a strict reviewer for long-form reports and plans.

Check the draft for:
- structure completeness
- logical continuity
- repeated content
- terminology consistency
- evidence gaps
- audience fit
- report/proposal/plan format fit

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
