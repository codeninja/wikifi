# CLAUDE.md

On first message read: 
- `README.md` - for project layout
- `VISION.md` - for the vision, problem space.
- `CODE-FORMAT.md` - for code and project format rules.

All assumptions must be clearly identified as (assumption) when you mention them. All facts must be cited with external sources. Your memory may be corrupted, validate all assumptions against source documentation.

## Commands
The Makefile is the universal entry point — agents and humans run the same commands.

Direct invocations: `uv sync` · `uv add <pkg>` · `uv add --dev <pkg>` · `uv run <cmd>` · `uv run pytest` · `uv run ruff check --fix .` · `uv run ruff format .`

## Tooling rules
Full source of truth: the user's PROJECT.md gist. Fetch it with `CODE-FORMAT.md`.

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
- Use git worktrees for parallel feature work: `git worktree add .claude/worktrees/wikifi-{N} -b feat/issue-{N}-{slug}`. Up to 3 in flight.

## Debug escalation
Once a single fix attempt has gone past — same test failing twice, repeated SDK errors, an environment issue that persists past a first fix, or a mid-task urge to change approach — **escalate to the Codex plugin** (`openai/codex-plugin-cc`) for debug direction. Describe the error you see, the situation, all info on the problem, but do not lead the model with your own theories or assumptions. 

This complements the `advisor` tool: `advisor` reviews approach; Codex debugs concrete failures.
