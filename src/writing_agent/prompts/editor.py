"""Editor prompt templates."""

EDITOR_SYSTEM_PROMPT = """
You are a careful long-form document editor.

Revise only where review findings require changes. Do not rewrite the whole
document, do not change core facts, and do not drift from the existing structure.
Remove repeated content, strengthen transitions, keep terminology consistent,
and preserve traceable evidence lists. Keep evidence-gap notes visible where
sources are insufficient.
""".strip()


def build_editor_prompt(draft_markdown: str, findings: str) -> list[tuple[str, str]]:
    """Build editor chat messages."""

    user_prompt = f"""
Draft:
{draft_markdown}

Review findings:
{findings}

Return revised markdown only. Keep section headings stable unless a finding
explicitly asks for a structural change.
""".strip()
    return [("system", EDITOR_SYSTEM_PROMPT), ("user", user_prompt)]

