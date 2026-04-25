# wikify

> A Python library that walks a codebase and produces a **technology-agnostic** markdown wiki describing the system in migration-ready terms.

For the *why* behind wikify and the design questions still to resolve, see [`VISION.md`](./VISION.md). For the development process, see [`CLAUDE.md`](./CLAUDE.md).

> **Naming:** the repo directory is `wikifi`; the library and CLI are `wikify`. Use the names deliberately.

## Status
Pre-implementation. Architecture and CLI surface are sketched below; binding decisions live in `VISION.md` under "Open design questions."

## Install & use
Add wikify to a target project, then run `init` to bootstrap wikification of that project's source.

```bash
uv add wikify
uv run wikify init
```

## CLI

- `init` — one-time setup and configuration, including boundary-walker heuristics and wiki target
- `walk` — the main entry point for walking a codebase and producing the wiki content
- `ask` — natural language queries against the wiki content, with optional context injection from the target codebase
- `chat` — an interactive REPL for iterative exploration of the wiki content and the target codebase


## Code Structure
Modularity is the key to successful parallel agent work. The codebase must follow our 


## Architecture (sketch)
- **`wikify/` package** — the library, with the CLI entry point exposed via `[project.scripts] wikify = "wikify.cli:main"` in `pyproject.toml`.
- **Boundary walker** — detects logical units in the target tree using manifest files (`pyproject.toml`, `package.json`, `Cargo.toml`, …) and yields them in dependency-aware order.
- **Agent-SDK orchestrator** — invokes the Anthropic Agent SDK per unit to produce the eight capture-scope sections defined in `VISION.md`.
- **Wiki adapter** — writes the rendered output to the wiki target. Selection of target system follows the open design questions.

## Tech stack
- **Python 3.12+**, packaged with **`uv`**
- **Anthropic Agent SDK** (`claude-agent-sdk`) — the engine for per-unit knowledge hydration
- **`ruff`** as the single tool for lint and format
- **`pytest` + `pytest-asyncio` + `pytest-cov`** for tests
- **NiceGUI** if and when wikify gains a UI surface (mounted on FastAPI, no JS build step)
- **Docker** + **Docker Compose** for the local stack
- **GitHub Actions** for CI

## Configuration
wikify reads its configuration from environment variables (a `.env.example` lands once the surface is finalized):

- `ANTHROPIC_API_KEY` — credentials for the Agent SDK

## Setup (development)
```bash
make hooks       # one-time: enables .githooks/ pre-commit + pre-push
uv sync          # install dependencies
make test        # run the test suite
make dev         # start the local stack
```

See [`CLAUDE.md`](./CLAUDE.md) for the full development process — commands, code rules, agent workflow, and debug escalation.

## Distribution
wikify ships as a Python library (PyPI / private index); it operates as a CLI invoked from a target project rather than as a server. 

