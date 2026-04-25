# CLAUDE.md

Process and procedures for working in this repo. For *what* wikify is, see [`README.md`](./README.md). For *why* it exists, see [`VISION.md`](./VISION.md).

## Commands
The Makefile is the universal entry point — agents and humans run the same commands.

```
make hooks       # one-time: enables .githooks/ pre-commit + pre-push
make dev         # docker compose up the local stack
make seed        # backend/scripts/seed_dev.py — dev data + prints JWT
make test        # full test suite (blocks pre-push on failure)
make lint        # ruff (+ eslint if a JS surface exists)
make coverage    # pytest --cov term-missing
```

Direct invocations: `uv sync` · `uv add <pkg>` · `uv add --dev <pkg>` · `uv run <cmd>` · `uv run pytest` · `uv run ruff check --fix .` · `uv run ruff format .`

## Tooling rules
Full source of truth: the user's PROJECT.md gist. Fetch it with `gh api gists/75f94d35911df96b3c931a8f76242332 --jq '.files."PROJECT.md".content'`.

- **`uv`** is the exclusive Python package manager. Commit `uv.lock`.
- **`ruff`** is the single tool for lint and format — covers what flake8, isort, and black used to do.
- **Every feature ships with tests.** Coverage target **≥85%**.
- Pre-commit hook should run lint with auto fix.
- Pre-push hook should run the full test suite and block on failure.
- When touching the **Anthropic Agent SDK** or the Anthropic API, invoke the `claude-api` skill so we use current model IDs and caching patterns.
- For any Python UI surface, mount **NiceGUI on FastAPI**. Reserve React for genuine public-facing SPAs.
- For any JS surface, use **`pnpm`** as the package manager.

## Code rules
Surface before deviating.

- **Auto-discover routers in `main.py`** via `pkgutil.iter_modules(...)`. The discovery loop is the single mount point — keeping it that way eliminates the top merge-conflict hotspot for parallel agents.
- **Import from actual modules.** Keep `__init__.py` files free of re-exports.
- **UUID primary keys**, with `created_at` + `updated_at` on every model and JSONB for flexible data.
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
- Use git worktrees for parallel feature work: `git worktree add /tmp/wikifi-{N} -b feat/issue-{N}-{slug}`. Up to 3 in flight.
- **Treat signal 9 from a backgrounded Claude process as a normal exit.** Check the log before restarting; restarts cost tokens and duplicate work.

## Debug escalation
Once a single fix attempt has gone past — same test failing twice, repeated SDK errors, an environment issue that persists past a first fix, or a mid-task urge to change approach — **escalate to the Codex plugin** (`openai/codex-plugin-cc`) for debug direction.

This complements the `advisor` tool: `advisor` reviews approach; Codex debugs concrete failures.
