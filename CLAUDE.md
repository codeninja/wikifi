# CLAUDE.md

On first message read: 
- `README.md` - for project layout
- `VISION.md` - for the vision, problem space.
- `CODE-FORMAT.md` - for code and project format rules.

All assumptions must be clearly identified as (assumption) when you mention them. All facts must be cited with external sources. Your memory may be corrupted, validate all assumptions against source documentation.

## Commands
The Makefile is the universal entry point — agents and humans run the same commands.

```
make hooks       # one-time: enable .githooks/ pre-commit + pre-push
make test        # full test suite + coverage
make lint        # ruff check + format check
make format      # ruff auto-fix + format
make init        # `uv run wikifi init` against this repo
make walk        # `uv run wikifi walk` against this repo
make coverage    # pytest --cov term-missing
```

Direct invocations: `uv sync` · `uv add <pkg>` · `uv add --dev <pkg>` · `uv run <cmd>` · `uv run pytest` · `uv run ruff check --fix .` · `uv run ruff format .` · `uv run wikifi <subcommand>`.

## Tooling rules
Full source of truth: `CODE-FORMAT.md` in this repo (mirrors the user's PROJECT.md gist).

- **`uv`** is the exclusive Python package manager. Commit `uv.lock`.
- **`ruff`** is the single tool for lint and format — covers what flake8, isort, and black used to do.
- **Every feature ships with tests.** Coverage target **≥85%**.
- Pre-commit hook should run lint with auto fix.
- Pre-push hook should run the full test suite and block on failure.
- **Local LLM by default.** wikifi must run against a local LLM out of the box, with no cloud dependency required to wikify a codebase. Hosted backends are valid additional options, not the default. If a hosted-Anthropic backend is ever added, invoke the `claude-api` skill while writing it.
- **Provider abstraction is mandatory.** The LLM backend must be reached through an abstraction layer. Swapping the backend (local Ollama, hosted Anthropic, hosted OpenAI, custom) must not require changes outside the provider boundary.
- **Reasoning quality preferred over walk speed.** When the chosen model exposes a thinking / reasoning level, the agent runs at the highest available setting. Lower levels are opt-in only.
- For any Python UI surface, mount **NiceGUI on FastAPI**. Reserve React for genuine public-facing SPAs. (Not relevant in v1 — wikifi is a CLI library.)
- For any JS surface, use **`pnpm`** as the package manager.

## Code rules
Surface before deviating.

- **wikifi is a CLI library, not a FastAPI app.** The router auto-discovery rule from the project template doesn't apply here — there is no API surface. The CLI entry point is declared via `[project.scripts]` in `pyproject.toml`.
- **The walk has four responsibilities, in order.** (1) Introspect the repository before parsing — the agent reviews the root structure and decides scope. (2) Filter unstructured or near-empty input before extraction — empty files must never reach the agent or stall the walk. (3) Extract from each in-scope file deterministically against the primary capture sections in `VISION.md`. (4) Synthesize sections from the aggregate, with derivative sections (personas, user stories, diagrams) produced *after* primary content is complete, never inferred from a single file. Don't reintroduce LLM agency in the file walk itself.
- **Feature extraction only.** wikifi describes what the legacy system does. It does not transform the source into the shape of any target architecture, target language, or target framework — that work is for the migration team consuming the wiki.
- **Wiki layout is at the implementor's discretion.** The on-disk shape inside `.wikifi/` (one file per section, nested taxonomy, rolled-up parents, …) is not prescribed. The contract is the *content* the wiki conveys, defined in `VISION.md`.
- **Import from actual modules.** Keep `__init__.py` files free of re-exports.
- **Keep `.env.example` placeholder-only.** Real values stay in `.env` (gitignored) or the secrets manager.

## Git workflow
- Keep `main` always deployable. Land changes through PRs (docs-only changes may land directly on `main`).
- worktrees: Always use git worktrees based off main in the path of ./.claude/worktrees.
- Commit and push code often in the process as worktree progress could be lost. 
- **Conventional Commits**: `feat:` / `fix:` / `refactor:` / `test:` / `docs:` / `chore:`.
- Rebase and squash commits before merging. 
- **Use merge commits** to preserve branch history.
- The pre-commit hook auto-fixes lint and re-stages. The pre-push hook runs the full test suite and gates the push. CI is the safety net for any `--no-verify` bypasses.

## Parallel agent workflow
- Use git worktrees for parallel feature work: `git worktree add .claude/worktrees/wikifi-{N} -b feat/issue-{N}-{slug}`. Up to 3 in flight.

## Debug escalation
Once a single fix attempt has gone past — same test failing twice, repeated SDK errors, an environment issue that persists past a first fix, or a mid-task urge to change approach — **escalate to the Codex plugin** (`openai/codex-plugin-cc`) for debug direction. Describe the error you see, the situation, all info on the problem, but do not lead the model with your own theories or assumptions. 

This complements the `advisor` tool: `advisor` reviews approach; Codex debugs concrete failures.
