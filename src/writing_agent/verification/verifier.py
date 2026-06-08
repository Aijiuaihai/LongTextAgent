"""Citation verification against an index manifest."""

import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from writing_agent.config import Settings, get_settings
from writing_agent.verification.citations import ExtractedCitation, extract_citations


class CitationVerificationResult(BaseModel):
    """Citation verification summary."""

    total_citations: int
    valid_citations: int
    invalid_citations: int
    missing_sections: list[str] = Field(default_factory=list)
    insufficient_evidence_count: int = 0
    fabricated_reference_count: int = 0
    findings: list[str] = Field(default_factory=list)
    overall_status: Literal["pass", "warning", "fail"]


def _manifest_path(collection: str, settings: Settings | None = None) -> Path:
    resolved = settings or get_settings()
    return resolved.output_dir / "index_manifests" / f"{collection}.json"


def load_index_manifest(
    collection: str | None = None,
    *,
    index_manifest: Path | str | dict[str, Any] | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Load an index manifest from explicit data/path or collection name."""

    if isinstance(index_manifest, dict):
        return index_manifest
    if index_manifest is not None:
        return json.loads(Path(index_manifest).read_text(encoding="utf-8"))
    if not collection:
        return {"sources": [], "chunks": []}
    path = _manifest_path(collection, settings)
    if not path.exists():
        return {"sources": [], "chunks": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _section_titles(markdown: str) -> list[str]:
    return [line.lstrip("#").strip() for line in markdown.splitlines() if line.startswith("## ")]


def _has_citation(section: str, citations: list[ExtractedCitation]) -> bool:
    return any(citation.section_title == section for citation in citations)


def _is_suspicious_chunk_id(chunk_id: str) -> bool:
    return not bool(re.search(r"(#chunk-\d+|chunk[-_]\w+|\w+#chunk-\d+)", chunk_id))


def verify_citations_in_text(
    text: str,
    collection: str | None = None,
    index_manifest: Path | str | dict[str, Any] | None = None,
) -> CitationVerificationResult:
    """Verify citations in markdown text."""

    manifest = load_index_manifest(collection, index_manifest=index_manifest)
    citations = extract_citations(text)
    chunk_to_source = {
        str(chunk.get("chunk_id")): str(chunk.get("source_path"))
        for chunk in manifest.get("chunks", [])
    }
    manifest_sources = {str(source.get("source_path")) for source in manifest.get("sources", [])}
    valid = 0
    findings: list[str] = []
    fabricated = 0
    for citation in citations:
        expected_source = chunk_to_source.get(citation.chunk_id)
        if _is_suspicious_chunk_id(citation.chunk_id):
            fabricated += 1
            findings.append(
                f"Suspicious chunk id at line {citation.line_number}: {citation.raw_text}"
            )
            continue
        if citation.chunk_id not in chunk_to_source:
            findings.append(f"Unknown chunk id at line {citation.line_number}: {citation.chunk_id}")
            continue
        if citation.source_path not in manifest_sources:
            findings.append(
                f"Unknown source path at line {citation.line_number}: {citation.source_path}"
            )
            continue
        if expected_source != citation.source_path:
            findings.append(
                f"Chunk/source mismatch at line {citation.line_number}: "
                f"{citation.chunk_id} belongs to {expected_source}"
            )
            continue
        valid += 1

    missing_sections = []
    for section in _section_titles(text):
        if section and not _has_citation(section, citations):
            missing_sections.append(section)
    insufficient = text.count("依据不足") + text.lower().count("insufficient evidence")
    invalid = len(citations) - valid
    if invalid or fabricated:
        status: Literal["pass", "warning", "fail"] = "fail"
    elif missing_sections or insufficient:
        status = "warning"
    else:
        status = "pass"
    return CitationVerificationResult(
        total_citations=len(citations),
        valid_citations=valid,
        invalid_citations=invalid,
        missing_sections=missing_sections,
        insufficient_evidence_count=insufficient,
        fabricated_reference_count=fabricated,
        findings=findings,
        overall_status=status,
    )


def verify_citations_in_file(
    file_path: Path | str,
    collection: str | None = None,
    index_manifest: Path | str | dict[str, Any] | None = None,
) -> CitationVerificationResult:
    """Verify citations in a markdown file."""

    return verify_citations_in_text(
        Path(file_path).read_text(encoding="utf-8"),
        collection=collection,
        index_manifest=index_manifest,
    )
