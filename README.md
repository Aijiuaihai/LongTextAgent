# LongTextAgent

LongTextAgent is a Python 3.11+ LangChain and LangGraph agent system for
long-form reports, project proposals, research plans, weekly reports, and
structured planning documents.

It is not a single-turn chatbot. The workflow parses the writing request, loads
local sources, plans an outline, writes section by section, reviews consistency,
revises, assembles, and exports the final document. LangGraph checkpoints allow
long tasks to pause and resume by `thread_id`.

## Architecture

```mermaid
flowchart LR
    request["request"] --> parse["parse"]
    parse --> source["source loading"]
    source --> rag["local RAG retrieval"]
    rag --> outline["outline"]
    outline --> writing["section writing"]
    writing --> review["review"]
    review --> revise["revise"]
    revise --> assemble["assemble"]
    assemble --> export["export"]
```

Core modules:

- `writing_agent.config`: environment-driven settings with secret-safe summaries.
- `writing_agent.llm`: Ollama, OpenAI-compatible, and OpenAI chat model adapters.
- `writing_agent.models`: Pydantic contracts for requests, plans, drafts, sources, and output.
- `writing_agent.graph`: LangGraph state, interrupt nodes, workflow assembly, and resume helpers.
- `writing_agent.checkpoints`: SQLite checkpointer creation and thread metadata.
- `writing_agent.rag`: minimal local chunking, in-memory indexing, and term-overlap retrieval.
- `writing_agent.evaluation`: deterministic quality metrics for generated markdown.
- `writing_agent.tools`: local document loading and markdown/docx export helpers.
- `writing_agent.cli`: Typer command line interface.

## Python 3.11 Environment

Use Python 3.11 or newer. The project intentionally declares
`requires-python = ">=3.11"`.

Linux or macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

Run checks:

```bash
ruff check .
pytest
```

## Environment

Copy `.env.example` to `.env` and edit values as needed. Do not commit `.env`.

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.6:35b

EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:8b

OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_MODEL=

DATA_DIR=./data
OUTPUT_DIR=./outputs
CHECKPOINT_DB_PATH=./outputs/checkpoints.sqlite
```

`LLM_PROVIDER` values:

- `ollama`: uses `langchain_ollama.ChatOllama`.
- `openai_compatible`: uses `langchain_openai.ChatOpenAI` with `OPENAI_BASE_URL`.
- `openai`: uses `langchain_openai.ChatOpenAI`.

API keys are never hardcoded, and `.gitignore` excludes `.env`, local data,
checkpoints, generated outputs, and cache directories.

## Doctor

```bash
writing-agent doctor
```

`doctor` prints the active Python version, whether Python 3.11+ is satisfied,
current working directory, `.env` status, data/output directory status,
checkpoint path, LLM provider, and model name. It does not print API keys.

## Ollama Model Check

Start Ollama and ensure the configured models exist:

```bash
ollama serve
ollama pull qwen3.6:35b
ollama pull qwen3-embedding:8b
```

Check the configured model:

```bash
writing-agent check-model
```

For Ollama, this checks `OLLAMA_BASE_URL`, calls `ChatOllama`, and prints model
name, base URL, elapsed time, and the first 200 response characters.

Windows and Docker notes:

- Local Windows Ollama normally uses `http://localhost:11434`.
- In a container calling a Windows host service, `host.docker.internal` may be required.
- If the check fails, run `ollama list` and confirm `OLLAMA_MODEL` exists.

## Run A Writing Workflow

```bash
writing-agent run \
  --topic "智慧林务系统建设计划书" \
  --type proposal \
  --audience "项目负责人和技术评审" \
  --length "5000字" \
  --style "正式、技术导向、少空话" \
  --source ./data/forestry_notes.md \
  --output-format markdown \
  --thread-id forestry-plan-demo \
  --rag \
  --top-k 5
```

If `--thread-id` is omitted, the CLI generates a readable id like
`writing-20260608-153000`. Checkpoints and metadata are bound to this id.

Supported source file types:

- `.md`
- `.txt`
- `.docx`
- `.pdf`

Generated markdown is written to `OUTPUT_DIR`, defaulting to `./outputs`.

## Human Review And Resume

Pause after outline:

```bash
writing-agent run \
  --topic "智慧林务系统建设计划书" \
  --thread-id forestry-plan-demo \
  --pause-after-outline
```

Pause before final export:

```bash
writing-agent run \
  --topic "智慧林务系统建设计划书" \
  --thread-id forestry-plan-demo \
  --pause-before-export
```

When the graph pauses, the CLI prints the `thread_id`, interrupt payload, and a
resume command. Create a review file:

```bash
echo "提纲整体可用，但请增加系统评估、部署风险、数据安全章节。" > review.md
```

Resume:

```bash
writing-agent resume \
  --thread-id forestry-plan-demo \
  --review-file review.md
```

Review files can be markdown text or JSON. Resume uses LangGraph
`Command(resume=...)` and continues from the checkpoint to export.

## Thread Metadata

List known threads:

```bash
writing-agent threads
```

Inspect one thread:

```bash
writing-agent inspect --thread-id forestry-plan-demo
```

Thread metadata is stored in `outputs/thread_metadata.json`. It summarizes
`thread_id`, update time, current step, interruption status, request topic,
section count, review finding count, final-document presence, and output path.

## Local RAG

The first RAG implementation is intentionally small and replaceable:

- `simple_chunk_text()` splits local source text by paragraph with overlap.
- `build_local_index()` builds an in-memory `list[DocumentChunk]`.
- `retrieve()` uses simple term-overlap scoring.

Before each section is written, the workflow retrieves top-k source chunks using
the section goal and key points. Only those chunks are injected into the writer
prompt. If no chunks match, the draft marks `本节资料依据不足`.

Disable local RAG:

```bash
writing-agent run --topic "..." --no-rag
```

## Evaluate Output

Evaluate generated markdown:

```bash
writing-agent evaluate --file outputs/<generated_file>.md
```

JSON output:

```bash
writing-agent evaluate --file outputs/<generated_file>.md --json
```

Rule metrics include character count, word count, heading counts, section count,
abstract/conclusion/reference detection, repeated paragraph ratio,
`依据不足` count, and generic phrase risk terms such as `赋能`, `高质量发展`,
`形成闭环`, `显著提升`, `多措并举`, `夯实基础`, and `智能化水平`.

## Roadmap

- Replace minimal RAG with embeddings and a persistent vector index.
- Web search tool integration for fresh external context.
- Interactive human editing and richer resume controls.
- Styled docx export with tables, references, and templates.
- Multi-agent collaboration for planner, writer, reviewer, and editor roles.
- LangSmith tracing for long workflow debugging.
- Evaluation datasets and optional LLM-as-judge scoring.

