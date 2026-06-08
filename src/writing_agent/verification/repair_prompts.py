"""Prompts for citation repair."""


LLM_CITATION_REPAIR_SYSTEM_PROMPT = """You repair invalid citations in a generated report.

Rules:
- You may only choose one action: replace, downgrade, or keep.
- replace means replacing the invalid citation with a real source_path and chunk_id
  from the manifest.
- downgrade means replacing the invalid citation with an insufficient-evidence note.
- keep is only allowed when the citation is already valid.
- Never invent source_path or chunk_id values.
- Return JSON only, matching this schema:
{
  "action": "replace | downgrade | keep",
  "original_citation": "...",
  "new_citation": "...",
  "reason": "...",
  "confidence": "low | medium | high"
}
"""


def build_repair_prompt(
    *,
    invalid_citation: str,
    section_title: str,
    paragraph_context: str,
    available_chunks: str,
) -> list[tuple[str, str]]:
    """Build a constrained citation repair prompt."""

    return [
        ("system", LLM_CITATION_REPAIR_SYSTEM_PROMPT),
        (
            "user",
            "Repair this invalid citation.\n\n"
            f"Section: {section_title}\n"
            f"Invalid citation: {invalid_citation}\n\n"
            f"Paragraph context:\n{paragraph_context}\n\n"
            f"Available manifest chunks:\n{available_chunks}\n\n"
            "If no chunk is clearly relevant, downgrade to: "
            "本节资料依据不足：原引用无法在索引中验证。",
        ),
    ]
