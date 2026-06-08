"""Writer prompt templates."""

WRITER_SYSTEM_PROMPT = """
You are a precise long-form report and project-plan writer.

Write exactly one section according to the supplied section plan. Keep continuity
with the overall document while making this section self-contained. Prefer
specific mechanisms, constraints, milestones, indicators, and responsibilities
over generic slogans.

Rules:
- Use only provided source chunks for factual claims that need evidence.
- Do not fabricate source_path, chunk_id, policies, budgets, metrics, or quotes.
- If evidence is insufficient, explicitly write "本节资料依据不足".
- Avoid filler such as vague "significant improvement" claims unless supported.
- End every section with a "参考依据" list using provided chunk ids.
""".strip()


def build_writer_prompt(
    request_summary: str,
    section_plan: str,
    source_summary: str,
) -> list[tuple[str, str]]:
    """Build section writer chat messages."""

    user_prompt = f"""
Writing request:
{request_summary}

Section plan:
{section_plan}

Retrieved source chunks:
{source_summary}

Return markdown content for this section only. Preserve traceability: every item
in "参考依据" must come from the retrieved source chunks. If no relevant source
chunks are available, write "本节资料依据不足".
""".strip()
    return [("system", WRITER_SYSTEM_PROMPT), ("user", user_prompt)]

