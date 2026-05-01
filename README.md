# wikifi

> A Python library that walks a codebase and produces a **technology-agnostic** feature and domain extraction from the source suitable for reflection into a new modern implementaiton which retains it's previous functionality and delivered value to users.

For the *why* behind wikifi and the design questions still to resolve, see [`VISION.md`](./VISION.md). For the development process, see [`CLAUDE.md`](./CLAUDE.md).

## Status
Pre-implementation. Architecture and CLI surface are sketched below; binding decisions live in `VISION.md`.

## Install & use
Add wikifi to a target project, then run `init` to bootstrap wikification of that project's source.

```bash
uv add wikifi
uv run wikifi init
```

## CLI

- `init` — one-time setup; scaffolds the `.wikifi/` directory and any local config the implementor chooses to expose.
- `walk` — main entry point. Walks the target codebase and produces the wiki content.
  - `--no-cache` — force a clean re-walk; drops the on-disk extraction + aggregation caches.
  - `--review` — run the critic + reviser loop on derivative sections (personas, user stories, diagrams).
  - `--provider {ollama|anthropic}` — override the configured provider for this walk.
- `report` — print a coverage + quality report (per-section file counts, findings, body sizes).
  - `--score` — additionally run the critic on every populated section for a 0-10 quality score.
- `ask` — natural language queries against the wiki content, with optional context injection from the target codebase.
- `chat` — interactive REPL for iterative exploration of the wiki content and the target codebase.

## Architecture
- **`wikifi/` package** — the library, with the CLI entry point exposed via `[project.scripts] wikifi = "wikifi.cli:main"` in `pyproject.toml`.
- **Repository introspection** — before walking, the agent reviews the target's root structure (manifests, top-level layout, gitignore signals) and decides which paths carry production source worth analyzing. The walk that follows is deterministic — the agent does not re-pick scope mid-walk.
- **Repo graph** (`wikifi/repograph.py`) — a regex-driven static analysis builds an import / reference graph across in-scope files, plus classifies each file's `FileKind` (application code, SQL, OpenAPI, Protobuf, GraphQL, migration, other). Each file's neighborhood is injected into the extraction prompt so per-file findings can describe cross-file flows.
- **Specialized extractors** (`wikifi/specialized/`) — schema files (SQL, OpenAPI, Protobuf, GraphQL, migrations) bypass the LLM entirely and run through deterministic parsers. The structured findings reach the same notes store as LLM output, so the rest of the pipeline is unchanged.
- **Per-file extraction** — for each in-scope file, the agent extracts contributions to each *primary* capture section (see `VISION.md`) into structured findings. Each finding carries a structured `SourceRef` (file + line range + content fingerprint) for downstream citation.
- **Content-addressed cache** (`wikifi/cache.py`) — extraction findings are keyed by `(rel_path, sha256(file_bytes))`; aggregation bodies are keyed by a hash of the section's notes payload. Re-walks skip every file whose fingerprint hasn't changed; resumability after a crash is a free property of the same cache. Use `walk --no-cache` to force a clean re-walk.
- **Input filtering** — the walker recognizes and skips unstructured or near-empty files (stub `__init__` files, empty fixtures, machine-generated artifacts) before they reach the agent. Empty input must never stall the walk.
- **Section synthesis** — primary capture sections are synthesized from the accumulated per-file findings; the aggregator emits a structured `EvidenceBundle` (body + claims + contradictions) and the renderer threads numbered citations + a "Conflicts in source" block into the section markdown. Derivative sections (personas, user stories, diagrams) are produced *after* primary content is complete, taking the synthesized primary content as their input.
- **Critic + reviser** (`wikifi/critic.py`) — opt-in (`walk --review`), runs a quality pass on derivative sections: scores the body against its brief and upstream evidence, identifies unsupported claims, and re-synthesizes when the score is below threshold. Only accepts a revision if it scores at least as well as the original.
- **Coverage + quality report** (`wikifi/report.py`) — `wikifi report` produces a per-section view of files contributing, finding count, body size, and (with `--score`) critic-derived quality scores.
- **Provider abstraction** — the LLM backend is reached through a provider interface. Default is a local Ollama server (`OllamaProvider`); two hosted backends are opt-in:
  - `AnthropicProvider` via `WIKIFI_PROVIDER=anthropic` — uses prompt caching with `cache_control: ephemeral` on the system prompt so the multi-KB extraction prompt is paid for once across hundreds of per-file calls.
  - `OpenAIProvider` via `WIKIFI_PROVIDER=openai` — relies on OpenAI's automatic prefix caching (no marker required) and routes the `think` knob to `reasoning_effort` on `o*`/`gpt-5` reasoning models.
- **Wiki adapter** — writes the rendered wiki into the target's `.wikifi/` directory. Layout, taxonomy, and structure within `.wikifi/` are at the implementor's discretion, provided the content contract from `VISION.md` is met.

## Tech stack
- **Python 3.12+**, packaged with **`uv`**
- **Local LLM via Ollama** as the default runtime; thinking-capable model (Qwen 3 27B) at the highest available reasoning level.
- **Provider abstraction layer** — Ollama is the default, additional backends slot in without touching the rest of the system.
- **`ruff`** as the single tool for lint and format
- **`pytest` + `pytest-cov`** for tests
- **NiceGUI** if and when wikifi gains a UI surface (mounted on FastAPI, no JS build step)
- **GitHub Actions** for CI

## Configuration
wikifi reads its configuration from environment variables (a `.env.example` lands once the surface is finalized). At minimum:

- the LLM provider id and the model identifier
- the local Ollama endpoint (when using the default provider)
- bounds on file size and stripped-content size, so unstructured or oversized files never reach the agent
- the agent's thinking / reasoning level — defaults to the highest the chosen model supports

## Setup (development)
```bash
make hooks       # one-time: enables .githooks/ pre-commit + pre-push
uv sync          # install dependencies
make test        # run the test suite
```

See [`CLAUDE.md`](./CLAUDE.md) for the full development process — commands, code rules, agent workflow, and debug escalation.

## Distribution
wikifi ships as a Python library (PyPI / private index); it operates as a CLI invoked from a target project rather than as a server.
