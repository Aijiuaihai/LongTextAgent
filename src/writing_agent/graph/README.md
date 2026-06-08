# Graph Module

The graph module owns workflow state and LangGraph execution.

- `state.py` defines `WritingState`, the shared state object passed between nodes.
- `nodes.py` contains pure node functions for parsing, loading, planning, writing, reviewing, revising, assembling, and exporting.
- `workflow.py` compiles the `StateGraph`, wires the linear workflow, and enables SQLite checkpoints by default.

The current route is:

`START -> parse_request -> load_sources -> plan_outline -> write_sections -> review_document -> revise_document -> assemble_document -> export_document -> END`

Tests can disable checkpoint persistence with `checkpointer=False` and disable
model calls with `use_llm=False`.

