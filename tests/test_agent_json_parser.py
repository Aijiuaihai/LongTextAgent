from pydantic import BaseModel

from writing_agent.agents.parser import (
    extract_json_from_markdown,
    normalize_llm_json,
    parse_json_object,
    parse_pydantic_output,
)


class DemoOutput(BaseModel):
    name: str
    count: int


def test_agent_json_parser_handles_common_llm_wrappers() -> None:
    assert parse_json_object('{"name": "ok", "count": 1}')["name"] == "ok"
    assert extract_json_from_markdown('```json\n{"name": "ok", "count": 2}\n```').startswith("{")
    assert normalize_llm_json('Sure:\n{"name": "ok", "count": 3}\nDone.') == (
        '{"name": "ok", "count": 3}'
    )

    parsed = parse_pydantic_output(
        '```json\n{"name": "typed", "count": 4}\n```',
        DemoOutput,
    )

    assert parsed.name == "typed"
    assert parsed.count == 4
