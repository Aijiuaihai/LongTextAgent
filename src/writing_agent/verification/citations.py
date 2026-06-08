"""Citation extraction from generated markdown."""

import re

from pydantic import BaseModel


class ExtractedCitation(BaseModel):
    """Citation extracted from a markdown document."""

    raw_text: str
    source_path: str
    chunk_id: str
    section_title: str
    line_number: int


SOURCE_BRACKET_RE = re.compile(r"\[source:\s*(?P<path>[^\]#]+)#(?P<chunk>[^\]]+)\]")
SOURCE_PAIR_RE = re.compile(
    r"\[source_path:\s*(?P<path>[^,\]]+),\s*chunk_id:\s*(?P<chunk>[^\]]+)\]"
)
SOURCE_ASSIGN_RE = re.compile(
    r"source_path\s*=\s*(?P<path>[^;]+);\s*chunk_id\s*=\s*(?P<chunk>[^\s\]]+)"
)
HASH_RE = re.compile(r"(?P<path>[^\s\[\](),;]+)#(?P<chunk>chunk[-_][\w.-]+|\w+#chunk-\d+)")


def _clean(value: str) -> str:
    return value.strip().strip("`.,;()[]")


def extract_citations(markdown: str) -> list[ExtractedCitation]:
    """Extract supported citation formats from markdown text."""

    citations: list[ExtractedCitation] = []
    current_section = ""
    in_references = False
    for line_number, line in enumerate(markdown.splitlines(), start=1):
        stripped = line.strip()
        is_reference_heading = (
            "参考依据" in stripped
            or "鍙傝€冧緷鎹" in stripped
            or stripped.lower().startswith("references")
        )
        if stripped.startswith("#") and not is_reference_heading:
            current_section = stripped.lstrip("#").strip()
            in_references = False
        if is_reference_heading:
            in_references = True

        patterns = [SOURCE_BRACKET_RE, SOURCE_PAIR_RE, SOURCE_ASSIGN_RE]
        structured_match_found = False
        for pattern in patterns:
            for match in pattern.finditer(line):
                structured_match_found = True
                citations.append(
                    ExtractedCitation(
                        raw_text=match.group(0),
                        source_path=_clean(match.group("path")),
                        chunk_id=_clean(match.group("chunk")),
                        section_title=current_section,
                        line_number=line_number,
                    )
                )

        if in_references and not structured_match_found:
            for match in HASH_RE.finditer(line):
                raw = match.group(0)
                if raw.startswith("http"):
                    continue
                citations.append(
                    ExtractedCitation(
                        raw_text=raw,
                        source_path=_clean(match.group("path")),
                        chunk_id=_clean(match.group("chunk")),
                        section_title=current_section,
                        line_number=line_number,
                    )
                )
    return citations
