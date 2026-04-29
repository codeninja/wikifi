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
- `ask` — natural language queries against the wiki content, with optional context injection from the target codebase.
- `chat` — interactive REPL for iterative exploration of the wiki content and the target codebase.

## Architecture (sketch)
- **`wikifi/` package** — the library, with the CLI entry point exposed via `[project.scripts] wikifi = "wikifi.cli:main"` in `pyproject.toml`.
- **Repository introspection** — before walking, the agent reviews the target's root structure (manifests, top-level layout, gitignore signals) and decides which paths carry production source worth analyzing. The walk that follows is deterministic — the agent does not re-pick scope mid-walk.
- **Per-file extraction** — for each in-scope file, the agent extracts contributions to each *primary* capture section (see `VISION.md`) into structured findings.
- **Input filtering** — the walker recognizes and skips unstructured or near-empty files (stub `__init__` files, empty fixtures, machine-generated artifacts) before they reach the agent. Empty input must never stall the walk.
- **Section synthesis** — primary capture sections are synthesized from the accumulated per-file findings; derivative sections (personas, user stories, diagrams) are produced *after* primary content is complete, taking the synthesized primary content as their input.
- **Provider abstraction** — the LLM backend is reached through a provider interface. Default is a local Ollama server; alternative providers (hosted Anthropic, hosted OpenAI, custom) plug in by implementing the same interface.
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
