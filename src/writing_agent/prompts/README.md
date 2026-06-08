# Prompts Module

The prompts module keeps role-specific instructions separate from node logic.

- `planner.py` asks the model for a structured JSON outline parseable as `WritingPlan`.
- `writer.py` writes one section at a time from a `SectionPlan`.
- `reviewer.py` returns structured review findings for logic, repetition, terminology, evidence, audience fit, and format fit.
- `editor.py` revises the draft from review findings without changing core facts.

Prompt builders return LangChain-compatible chat message tuples.

