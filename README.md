# wikifi

> A Python library and CLI that walks a codebase and produces a technology-agnostic wiki describing the system in migration-ready terms.

`wikifi` reads source artefacts from a target repository, runs them through a
local-LLM pipeline, and writes a structured `.wikifi/` directory containing
domain-level documentation: intent, capabilities, domains, entities,
integrations, external dependencies, cross-cutting concerns, hard
specifications, plus derivative personas, Gherkin user stories, and Mermaid
diagrams. The output deliberately strips implementation language so a migration
team can re-implement the system on a fresh stack without referring back to the
original code.

## Quick start

```bash
# 1. Make sure Ollama is running locally and the default model is pulled.
ollama serve &
ollama pull qwen3.6:27b

# 2. Install wikifi (uv-based — it's the only Python package manager allowed).
uv sync

# 3. Provision the workspace and run the walk against the current repo.
make init    # one-time: create .wikifi/ + .wikifi/.notes/
make walk    # full four-stage walk
```

`wikifi walk --target /path/to/other/repo` runs the pipeline against any
target repository.

## Pipeline stages

The walk is a strict, sequential, four-stage pipeline:

1. **Introspection** — recursive scan with hard-excluded directories, gitignore
   awareness, binary sniffing, size truncation, and a min-content guard against
   thinking-runaway on stub files. Produces a directory summary and an LLM
   assessment classifying primary languages and inferred system purpose.
2. **Extraction** — every in-scope file goes through a schema-validated
   structured-output call. Each call yields one immutable JSON note tagging
   findings against allowed sections (`intent`, `capabilities`, `domains`,
   `entities`, `integrations`, `external_dependencies`, `cross_cutting`,
   `hard_specifications`).
3. **Aggregation** — notes are grouped by section and each primary section is
   synthesized into a markdown body via a free-form generation call. Empty
   sections receive an explicit gap stanza rather than being silently omitted.
4. **Derivation** — after the primary sections settle, the orchestrator
   synthesizes user personas, Gherkin user stories, and three Mermaid diagrams
   from the aggregate.

Every stage degrades gracefully — a single-file extraction failure or a
mid-section synthesis failure is logged and recorded in the run summary, but
never halts the pipeline.

## Configuration

All settings are read from `WIKIFI_*` environment variables, optionally
overridden by a `.env` co-located with the target repository. See
[`.env.example`](./.env.example) for the full list. Defaults are tuned for a
local Qwen3 27B running on Ollama at the highest reasoning level the model
exposes; reasoning quality is preferred over walk speed.

| Variable | Default | Purpose |
|---|---|---|
| `WIKIFI_PROVIDER` | `ollama` | LLM backend (only `ollama` in v1) |
| `WIKIFI_MODEL` | `qwen3.6:27b` | Model identifier |
| `WIKIFI_OLLAMA_HOST` | `http://localhost:11434` | Ollama HTTP endpoint |
| `WIKIFI_REQUEST_TIMEOUT` | `900` | Per-request timeout (seconds) |
| `WIKIFI_MAX_FILE_BYTES` | `200000` | Per-file truncation limit |
| `WIKIFI_MIN_CONTENT_BYTES` | `64` | Stub-skip guard |
| `WIKIFI_INTROSPECTION_DEPTH` | `3` | Tree depth fed to introspection |
| `WIKIFI_THINK` | `high` | Reasoning level (`high`/`medium`/`low`/`true`/`false`) |

## Output

The wiki is written to `<target>/.wikifi/`:

```
.wikifi/
├── intent.md
├── capabilities.md
├── domains.md
├── entities.md
├── integrations.md
├── external_dependencies.md
├── cross_cutting.md
├── hard_specifications.md
├── personas.md          (derivative)
├── user_stories.md      (derivative)
├── diagrams.md          (derivative)
├── execution_summary.md
└── .notes/              (gitignored — intermediate JSON extraction notes)
```

Every section file starts at H2 (no top-level H1). When upstream evidence is
missing or contradictory the body declares an explicit `### Documented Gaps`
block instead of fabricating content.

## Make targets

```
make init        # provision .wikifi/ in this repo
make walk        # run full pipeline against this repo
make test        # full test suite
make coverage    # pytest --cov term-missing
make lint        # ruff check + format check
make format      # ruff auto-fix + format
make hooks       # enable .githooks/ pre-commit + pre-push
```

See [`VISION.md`](./VISION.md) for the original vision and [`CLAUDE.md`](./CLAUDE.md)
for the conventions enforced inside this repo.
