from writing_agent.verification.citations import extract_citations


def test_extract_citations_from_supported_formats() -> None:
    markdown = """# Demo

## Section A

Content [source: data/a.md#data/a.md#chunk-1]

### 参考依据

- data/b.md#chunk_001
- source_path=data/c.md; chunk_id=chunk_002
- [source_path: data/d.md, chunk_id: chunk_003]
"""

    citations = extract_citations(markdown)

    assert len(citations) == 4
    assert citations[0].source_path == "data/a.md"
    assert citations[0].chunk_id == "data/a.md#chunk-1"
    assert citations[-1].line_number > 0

