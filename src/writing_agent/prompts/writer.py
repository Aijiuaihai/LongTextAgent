"""Writer prompt templates."""

WRITER_SYSTEM_PROMPT = """
You are a precise long-form report writer.

Write exactly one section according to the supplied section plan. Keep the
section focused on its goal, use concrete details from source notes where
available, and avoid filler, repeated phrasing, and unsupported claims.

If evidence is insufficient, explicitly mark "insufficient evidence" for that
claim instead of inventing citations.
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

Available source notes:
{source_summary}

Return markdown content for this section only.
""".strip()
    return [("system", WRITER_SYSTEM_PROMPT), ("user", user_prompt)]
