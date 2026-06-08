"""Editor prompt templates."""

EDITOR_SYSTEM_PROMPT = """
You are a careful long-form document editor.

Revise according to review findings without changing core facts. Remove repeated
content, strengthen transitions, keep terminology consistent, and preserve
explicit evidence-gap notes where sources are insufficient.
""".strip()


def build_editor_prompt(draft_markdown: str, findings: str) -> list[tuple[str, str]]:
    """Build editor chat messages."""

    user_prompt = f"""
Draft:
{draft_markdown}

Review findings:
{findings}

Return revised markdown only.
""".strip()
    return [("system", EDITOR_SYSTEM_PROMPT), ("user", user_prompt)]
