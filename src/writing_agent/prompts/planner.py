"""Planner prompt templates."""

PLANNER_SYSTEM_PROMPT = """
You are a senior long-form document planner.

Generate an executable outline for a long report, proposal, plan, weekly report,
or research summary. The outline must be specific enough that another writer can
write each section independently without losing context.

Return only valid JSON matching this schema:
{
  "title": "string",
  "abstract_goal": "string",
  "sections": [
    {
      "title": "string",
      "goal": "string",
      "key_points": ["string"],
      "evidence_needed": ["string"],
      "estimated_words": 800
    }
  ],
  "risks": ["string"]
}
""".strip()


def build_planner_prompt(request_summary: str, source_summary: str) -> list[tuple[str, str]]:
    """Build planner chat messages."""

    user_prompt = f"""
Writing request:
{request_summary}

Available source notes:
{source_summary}

Planning requirements:
- Prefer concrete section goals over generic headings.
- Include evidence needs for claims that require support.
- Keep the section count practical for long-form staged writing.
- Do not invent source titles or citations.
""".strip()
    return [("system", PLANNER_SYSTEM_PROMPT), ("user", user_prompt)]
