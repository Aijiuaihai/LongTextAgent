# Tools Module

The tools module contains local, deterministic helpers used by graph nodes.

- `document_loader.py` reads `.md`, `.txt`, `.docx`, and `.pdf` files and normalizes them into `SourceNote` records.
- `export.py` writes timestamped markdown files and provides a simple docx export function.

Generated outputs, checkpoint databases, local data, and environment files are
excluded from Git by default.

