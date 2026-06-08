"""Automatic citation repair helpers."""

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from writing_agent.config import Settings, get_settings
from writing_agent.graph.nodes import _extract_json, _extract_text
from writing_agent.llm import get_chat_model
from writing_agent.verification.citations import ExtractedCitation, extract_citations
from writing_agent.verification.repair_prompts import build_repair_prompt
from writing_agent.verification.verifier import (
    CitationVerificationResult,
    load_index_manifest,
    verify_citations_in_file,
)

INSUFFICIENT_NOTE = "本节资料依据不足：原引用无法在索引中验证。"


class CitationRepairAction(BaseModel):
    """A single citation repair decision."""

    action: Literal["replace", "downgrade", "keep"]
    original_citation: str
    new_citation: str
    reason: str
    confidence: Literal["low", "medium", "high"] = "low"


class CitationRepairResult(BaseModel):
    """Citation repair result."""

    file_path: str
    mode: Literal["conservative", "llm_assisted"]
    repaired_text: str
    actions: list[CitationRepairAction] = Field(default_factory=list)
    replaced_count: int = 0
    downgraded_count: int = 0
    kept_count: int = 0
    output_path: str
    before: CitationVerificationResult | None = None
    after: CitationVerificationResult | None = None


def _chunk_lookup(manifest: dict[str, Any]) -> dict[str, str]:
    return {
        str(chunk.get("chunk_id")): str(chunk.get("source_path"))
        for chunk in manifest.get("chunks", [])
    }


def _valid_sources(manifest: dict[str, Any]) -> set[str]:
    return {str(source.get("source_path")) for source in manifest.get("sources", [])}


def _is_invalid(citation: ExtractedCitation, manifest: dict[str, Any]) -> bool:
    chunk_to_source = _chunk_lookup(manifest)
    if citation.chunk_id not in chunk_to_source:
        return True
    if citation.source_path not in _valid_sources(manifest):
        return True
    return chunk_to_source[citation.chunk_id] != citation.source_path


def _available_chunks_text(manifest: dict[str, Any], source_path: str, limit: int = 20) -> str:
    chunks = [
        chunk
        for chunk in manifest.get("chunks", [])
        if not source_path or str(chunk.get("source_path")) == source_path
    ]
    if not chunks:
        chunks = list(manifest.get("chunks", []))
    rows = [
        (
            f"- source_path={chunk.get('source_path')}; "
            f"chunk_id={chunk.get('chunk_id')}; title={chunk.get('title', '')}"
        )
        for chunk in chunks[:limit]
    ]
    return "\n".join(rows)


def _line_context(text: str, line_number: int, radius: int = 2) -> str:
    lines = text.splitlines()
    start = max(0, line_number - radius - 1)
    end = min(len(lines), line_number + radius)
    return "\n".join(lines[start:end])


def _conservative_action(citation: ExtractedCitation) -> CitationRepairAction:
    return CitationRepairAction(
        action="downgrade",
        original_citation=citation.raw_text,
        new_citation=INSUFFICIENT_NOTE,
        reason="The citation cannot be verified against the index manifest.",
        confidence="high",
    )


def _parse_repair_action(raw_output: str, citation: ExtractedCitation) -> CitationRepairAction:
    parsed = CitationRepairAction.model_validate_json(_extract_json(raw_output))
    if parsed.original_citation != citation.raw_text:
        parsed.original_citation = citation.raw_text
    return parsed


def _llm_repair_action(
    *,
    citation: ExtractedCitation,
    text: str,
    manifest: dict[str, Any],
    settings: Settings,
) -> CitationRepairAction:
    model = get_chat_model(settings)
    messages = build_repair_prompt(
        invalid_citation=citation.raw_text,
        section_title=citation.section_title,
        paragraph_context=_line_context(text, citation.line_number),
        available_chunks=_available_chunks_text(manifest, citation.source_path),
    )
    raw = _extract_text(model.invoke(messages))
    action = _parse_repair_action(raw, citation)
    if action.action == "replace":
        normalized = action.new_citation.strip()
        if normalized.startswith("[source:") and normalized.endswith("]"):
            extracted = extract_citations(normalized)
        elif "#" in normalized:
            extracted = extract_citations(f"[source: {normalized}]")
        else:
            extracted = []
        candidate = extracted[0] if extracted else None
        if candidate is None or _is_invalid(candidate, manifest):
            return _conservative_action(citation)
        action.new_citation = f"[source: {candidate.source_path}#{candidate.chunk_id}]"
    elif action.action == "downgrade":
        action.new_citation = INSUFFICIENT_NOTE
    return action


def _apply_actions(text: str, actions: list[CitationRepairAction]) -> str:
    repaired = text
    for action in actions:
        if action.action == "keep":
            continue
        replacement = action.new_citation or INSUFFICIENT_NOTE
        repaired = repaired.replace(action.original_citation, replacement, 1)
    return repaired


def _write_repair_output(
    *,
    original_path: Path,
    repaired_text: str,
    output: Path | None,
    in_place: bool,
) -> Path:
    if in_place:
        backup = original_path.with_suffix(original_path.suffix + ".bak")
        backup.write_text(original_path.read_text(encoding="utf-8"), encoding="utf-8")
        original_path.write_text(repaired_text, encoding="utf-8")
        return original_path
    resolved = output or original_path.with_suffix(".repaired.md")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(repaired_text, encoding="utf-8")
    return resolved


def repair_citations_in_file(
    file_path: Path | str,
    *,
    collection: str | None = None,
    index_manifest: Path | str | dict[str, Any] | None = None,
    mode: Literal["conservative", "llm_assisted"] = "conservative",
    output: Path | str | None = None,
    in_place: bool = False,
    settings: Settings | None = None,
) -> CitationRepairResult:
    """Repair invalid citations in a markdown file."""

    resolved_settings = settings or get_settings()
    path = Path(file_path)
    text = path.read_text(encoding="utf-8")
    manifest = load_index_manifest(
        collection,
        index_manifest=index_manifest,
        settings=resolved_settings,
    )
    if not manifest.get("chunks"):
        raise FileNotFoundError(
            "No index manifest chunks found. Run `writing-agent collections rebuild` first."
        )
    before = verify_citations_in_file(path, collection=collection, index_manifest=manifest)
    citations = extract_citations(text)
    actions: list[CitationRepairAction] = []
    for citation in citations:
        if not _is_invalid(citation, manifest):
            actions.append(
                CitationRepairAction(
                    action="keep",
                    original_citation=citation.raw_text,
                    new_citation=citation.raw_text,
                    reason="Citation is valid.",
                    confidence="high",
                )
            )
            continue
        if mode == "llm_assisted":
            try:
                action = _llm_repair_action(
                    citation=citation,
                    text=text,
                    manifest=manifest,
                    settings=resolved_settings,
                )
            except (ValidationError, json.JSONDecodeError, ValueError, RuntimeError):
                action = _conservative_action(citation)
        else:
            action = _conservative_action(citation)
        actions.append(action)

    repaired_text = _apply_actions(text, actions)
    output_path = _write_repair_output(
        original_path=path,
        repaired_text=repaired_text,
        output=Path(output) if output else None,
        in_place=in_place,
    )
    after = verify_citations_in_file(output_path, collection=collection, index_manifest=manifest)
    return CitationRepairResult(
        file_path=str(path),
        mode=mode,
        repaired_text=repaired_text,
        actions=actions,
        replaced_count=sum(1 for action in actions if action.action == "replace"),
        downgraded_count=sum(1 for action in actions if action.action == "downgrade"),
        kept_count=sum(1 for action in actions if action.action == "keep"),
        output_path=str(output_path),
        before=before,
        after=after,
    )
