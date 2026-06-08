"""Citation verification reporting helpers."""

import json

from rich.console import Console
from rich.table import Table

from writing_agent.verification.verifier import CitationVerificationResult


def citation_result_to_json(result: CitationVerificationResult) -> str:
    """Serialize citation verification result as JSON."""

    return json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2)


def print_citation_report(
    result: CitationVerificationResult,
    console: Console | None = None,
) -> None:
    """Print a Rich table for citation verification."""

    resolved_console = console or Console()
    table = Table(title="Citation Verification")
    table.add_column("Metric")
    table.add_column("Value")
    for key, value in result.model_dump(mode="json").items():
        rendered = json.dumps(value, ensure_ascii=False) if isinstance(value, list) else str(value)
        table.add_row(key, rendered)
    resolved_console.print(table)
