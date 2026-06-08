# writing_agent Package

This package contains the long-form writing agent runtime.

- `config.py` loads environment variables and returns secret-safe summaries.
- `llm.py` creates chat model instances for Ollama, OpenAI-compatible endpoints, and OpenAI.
- `models.py` defines Pydantic contracts shared by graph nodes, tools, and CLI commands.
- `cli.py` exposes the Typer command line interface.
- `graph/` contains LangGraph state, node implementations, and workflow assembly.
- `tools/` contains local source loading and export helpers.
- `prompts/` contains role-specific prompt builders.

The package is intentionally organized around stable contracts so retrieval,
human review, tracing, and richer exporters can be added without rewriting the
workflow.

