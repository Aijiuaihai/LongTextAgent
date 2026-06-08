"""Rule-based metrics for generated markdown documents."""

import re
from collections import Counter
from typing import Any

RISK_TERMS = [
    "赋能",
    "高质量发展",
    "形成闭环",
    "显著提升",
    "多措并举",
    "夯实基础",
    "智能化水平",
]


def count_characters(text: str) -> int:
    """Count non-whitespace characters."""

    return len(re.sub(r"\s+", "", text))


def count_words(text: str) -> int:
    """Count English-like words and CJK character groups."""

    return len(re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]", text))


def heading_counts(markdown: str) -> dict[str, int]:
    """Count markdown headings by level."""

    counts: Counter[str] = Counter()
    for line in markdown.splitlines():
        match = re.match(r"^(#{1,6})\s+", line)
        if match:
            counts[f"h{len(match.group(1))}"] += 1
    return dict(counts)


def section_count(markdown: str) -> int:
    """Count top-level content sections."""

    counts = heading_counts(markdown)
    return sum(count for level, count in counts.items() if level in {"h2", "h3"})


def has_heading(markdown: str, keywords: list[str]) -> bool:
    """Return whether a heading contains any keyword."""

    for line in markdown.splitlines():
        if not line.lstrip().startswith("#"):
            continue
        if any(keyword.lower() in line.lower() for keyword in keywords):
            return True
    return False


def repeated_paragraph_ratio(markdown: str) -> float:
    """Calculate repeated paragraph ratio, ignoring very short paragraphs."""

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", markdown)
        if len(paragraph.strip()) >= 30
    ]
    if not paragraphs:
        return 0.0
    counts = Counter(paragraphs)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    return repeated / len(paragraphs)


def risk_term_counts(markdown: str) -> dict[str, int]:
    """Count generic or slogan-like risk terms."""

    return {term: markdown.count(term) for term in RISK_TERMS if markdown.count(term)}


def evaluate_text(markdown: str) -> dict[str, Any]:
    """Evaluate markdown with deterministic rule-based metrics."""

    headings = heading_counts(markdown)
    return {
        "characters": count_characters(markdown),
        "words": count_words(markdown),
        "heading_counts": headings,
        "section_count": section_count(markdown),
        "has_abstract": has_heading(markdown, ["abstract", "摘要"]),
        "has_conclusion": has_heading(markdown, ["conclusion", "结论", "总结"]),
        "has_references": "参考依据" in markdown or "references" in markdown.lower(),
        "repeated_paragraph_ratio": repeated_paragraph_ratio(markdown),
        "insufficient_evidence_count": markdown.count("依据不足")
        + markdown.lower().count("insufficient evidence"),
        "risk_terms": risk_term_counts(markdown),
    }

