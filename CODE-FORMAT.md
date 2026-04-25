How We Build Software — project conventions, tooling, and agent workflow for Claude

# PROJECT.md — How We Build Software

> **Purpose:** This document defines how projects are structured, built, tested, deployed, and maintained. It is the single source of truth for any new project or coding agent. Point Claude at this gist and it knows how we work.

---

## Table of Contents
1. [Philosophy](#philosophy)
2. [Repository Structure](#repository-structure)
3. [Tech Stack](#tech-stack)
4. [Package Management](#package-management)
5. [Project Initialization](#project-initialization)
6. [Backend Conventions (Python)](#backend-conventions-python)
7. [Frontend Conventions (JS/TS)](#frontend-conventions-jsts)
8. [Database & Migrations](#database--migrations)
9. [Testing](#testing)
10. [Linting & Formatting](#linting--formatting)
11. [Makefile](#makefile)
12. [Git Workflow](#git-workflow)
13. [CI/CD](#cicd)
14. [Pre-commit Hooks](#pre-commit-hooks)
15. [Docker & Local Dev](#docker--local-dev)
16. [Deployment](#deployment)
17. [Environment & Secrets](#environment--secrets)
18. [GitHub Project Management](#github-project-management)
19. [Agent Workflow (Agentic Development)](#agent-workflow-agentic-development)
20. [CLAUDE.md Template](#claudemd-template)
21. [PR Template](#pr-template)
22. [Anti-Patterns](#anti-patterns)

---

## Philosophy

- **Explicit > implicit** — no magic, no hidden state, no conventions only the author understands
- **Composition > inheritance** — small, composable pieces over deep hierarchies
- **Constraints > convention** — enforce correctness with types, schemas, and tooling, not documentation
- **Deterministic behavior** — same inputs produce same outputs; minimize runtime surprises
- **Tooling as force multipliers** — invest in DX so agents and humans move fast without breaking things
- **Tests are non-negotiable** — if it's not tested, it's broken; target ≥85% coverage

---

## Repository Structure

Every project follows this layout. Not every project needs every piece — skip what doesn't apply, but don't rename or reorganize what exists.

```
project-root/
├── .github/
│   ├── workflows/
│   │   └── ci.yml              # GitHub Actions CI pipeline
│   └── pull_request_template.md
├── .githooks/
│   ├── pre-commit              # Auto-fix lint on commit
│   └── pre-push                # Run full test suite before push
├── backend/                    # Python backend (FastAPI)
│   ├── api/                    # Route modules (auto-discovered)
│   ├── models/                 # SQLAlchemy models
│   ├── services/               # Business logic, external integrations
│   ├── auth/                   # Authentication (OAuth, JWT)
│   ├── agents/                 # AI agents (Google ADK, etc.)
│   ├── scripts/
│   │   └── seed_dev.py         # Dev data seeder + JWT token printer
│   ├── tests/
│   │   ├── conftest.py         # Shared fixtures
│   │   ├── e2e/                # End-to-end integration tests
│   │   └── test_*.py           # Unit/integration tests
│   ├── migrations/             # Alembic migration scripts
│   ├── main.py                 # App entry point
│   ├── config.py               # Pydantic BaseSettings
│   ├── database.py             # SQLAlchemy async engine + sessions
│   └── pyproject.toml          # Python project config (deps, pytest, ruff)
├── frontend/                   # React frontend (Vite)
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── context/
│   │   ├── lib/                # API client, hooks, utilities
│   │   └── __tests__/          # Vitest + RTL + MSW tests
│   ├── package.json
│   └── vite.config.js
├── mobile/                     # React Native + Expo (optional)
├── helm/                       # Kubernetes Helm charts (optional)
├── docs/
│   ├── screenshots/
│   └── implementation_plans/
├── .env.example                # Template — NEVER real secrets
├── .gitignore
├── CLAUDE.md                   # Agent instructions for this repo
├── README.md                   # Human-readable project overview
├── Makefile                    # Task runner
├── Dockerfile                  # Multi-stage production build
└── docker-compose.yml          # Local dev stack
```

---

## Tech Stack

### Backend
| Tool | Purpose | Why |
|------|---------|-----|
| **Python 3.12+** | Language | Type hints, async/await, performance |
| **FastAPI** | Web framework | Async-native, auto OpenAPI docs, Pydantic integration |
| **SQLAlchemy 2.x** | ORM | Async support, type-safe queries, mature ecosystem |
| **Alembic** | Migrations | SQLAlchemy-native, autogenerate support |
| **Pydantic** | Validation | Input/output schemas, settings management |
| **uv** | Package manager | Fast, deterministic, replaces pip/poetry/pipenv |
| **ruff** | Linter + formatter | Replaces flake8/isort/black — single tool, fast |
| **pytest** | Test framework | Fixtures, async support, coverage |
| **pytest-asyncio** | Async testing | Native async test functions |
| **pytest-cov** | Coverage | Coverage reporting in CI |

### GUI / Frontend

**Python projects prefer NiceGUI** for any UI needs — dashboards, admin panels, tools, internal apps. Only reach for React/Vite when building a standalone SPA or public-facing web app that truly needs a JS frontend.

#### Python GUI (preferred for Python projects)
| Tool | Purpose | Why |
|------|---------|-----|
| **NiceGUI** | Python web UI | Pure Python, auto-reload, Tailwind built-in, no JS build step |
| **Tailwind CSS** | Styling | Comes bundled with NiceGUI, utility-first |

> **When to use NiceGUI:** Internal tools, dashboards, config UIs, dev tools, admin panels, any Python project that needs a visual interface. It runs as part of your FastAPI app — no separate frontend build, no Node, no bundler.

> **When to use React/Vite:** Public-facing SPAs, complex client-side state, projects where the frontend team is JS-native, or when you need SSR/SSG.

#### JS Frontend (when needed)
| Tool | Purpose | Why |
|------|---------|-----|
| **React 18/19** | UI framework | Component model, hooks, ecosystem |
| **Vite** | Build tool | Fast HMR, ES modules, simple config |
| **Tailwind CSS 4** | Styling | Utility-first, no CSS files to manage |
| **pnpm** | Package manager | Fast, disk-efficient, strict |
| **Node 22** | Runtime | LTS, `.nvmrc` pinned |
| **Vitest** | Test framework | Vite-native, fast, Jest-compatible API |
| **React Testing Library** | Component tests | Tests behavior, not implementation |
| **MSW** | API mocking | Service worker intercepts, realistic mocks |
| **ESLint** | Linter | Standard JS/JSX rules |

### Infrastructure
| Tool | Purpose | Why |
|------|---------|-----|
| **Docker** | Containerization | Consistent environments |
| **Docker Compose** | Local dev stack | Multi-service orchestration |
| **PostgreSQL 16** | Database | JSONB, UUID, mature, async drivers |
| **GitHub Actions** | CI/CD | Native GitHub integration |
| **Helm** | K8s packaging | Templated deployments |
| **GKE** | Production hosting | Managed Kubernetes |

### AI / Agent
| Tool | Purpose |
|------|---------|
| **Google Gemini** | Vision, generation, structured output |
| **Google ADK** | Agent framework with tool calling |
| **MCP** | Tool declaration protocol |

---

## Package Management

### Python: `uv`

uv replaces pip, poetry, pipenv, and venv. It's fast, deterministic, and handles everything.

```bash
uv init                        # Initialize new project
uv add fastapi sqlalchemy      # Add dependencies
uv add --dev pytest ruff       # Add dev dependencies
uv sync                        # Install from lockfile
uv run pytest                  # Run within the project environment
uv run python script.py        # Run any Python script
```

**Key files:**
- `pyproject.toml` — project metadata, dependencies, tool config (pytest, ruff)
- `uv.lock` — deterministic lockfile (commit this)

**Never use pip directly.** Always `uv add` / `uv sync` / `uv run`.

### JavaScript: `pnpm`

```bash
pnpm install                   # Install from lockfile
pnpm add react                 # Add dependency
pnpm add -D vitest             # Add dev dependency
pnpm run dev                   # Run scripts
pnpm test                      # Run tests
```

**Key files:**
- `package.json` — deps and scripts
- `pnpm-lock.yaml` — lockfile (commit this)
- `.nvmrc` — pins Node version (use `22`)

**Never use npm or yarn.**

---

## Project Initialization

### Setup Checklist

Use this checklist when bootstrapping any new project. Not every item applies to every project — skip what doesn't fit, but don't skip what does.

#### Repository & Structure
- [ ] Create private GitHub repo: `gh repo create codeninja/<name> --private --description "..." --clone`
- [ ] Create directory structure per [Repository Structure](#repository-structure)
- [ ] Add `.gitignore` (Python, Node, IDE, `.env`, `.clawbert/`)
- [ ] Add `.env.example` with all required env vars (no real secrets)

#### Python Backend (if applicable)
- [ ] `uv init` in project root or `backend/`
- [ ] Add core deps: `fastapi`, `uvicorn`, `sqlalchemy`, `alembic`, `pydantic-settings`
- [ ] Add dev deps: `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `aiosqlite`
- [ ] Create `config.py` with Pydantic `BaseSettings`
- [ ] Create `main.py` with auto-router discovery
- [ ] Set up Alembic migrations (if using DB)

#### GUI (Python projects prefer NiceGUI)
- [ ] Add `nicegui` to deps: `uv add nicegui`
- [ ] Create `ui/` or `pages/` module for NiceGUI pages
- [ ] Mount NiceGUI on FastAPI app (shared server, single process)

#### Node/Frontend (only when a JS SPA is truly needed)
- [ ] Create `.nvmrc` → `22`
- [ ] Scaffold with `pnpm create vite frontend -- --template react`
- [ ] Add deps: `axios`, `react-router-dom`
- [ ] Add dev deps: `vitest`, `@testing-library/react`, `msw`, `jsdom`

#### Documentation
- [ ] `README.md` — purpose, tech stack, setup, usage, status
- [ ] `CLAUDE.md` — project instructions for Claude Code (see [template](#claudemd-template))
- [ ] `docs/PROJECT.md` — copy of this gist or link to it

#### CI/CD & Tooling
- [ ] `.github/workflows/ci.yml` — lint, test, build on PR/push
- [ ] `.github/pull_request_template.md`
- [ ] `Makefile` with standard targets (see [Makefile](#makefile))
- [ ] Git hooks: `make hooks` or `.githooks/pre-commit` + `pre-push`

#### Agent & Claude Code Setup
- [ ] Run `claude init` in project root (creates `.claude/` with settings)
- [ ] Verify `.claude/settings.json` has appropriate permissions
- [ ] `CLAUDE.md` includes: commands, architecture, conventions, known issues

#### Quality Gates
- [ ] Ruff configured in `pyproject.toml` (or `ruff.toml`)
- [ ] Test suite runs: `make test` or `pytest`
- [ ] Coverage target set (≥85%)
- [ ] Pre-commit hook runs lint + format

#### Deployment (if applicable)
- [ ] `Dockerfile` + `docker-compose.yml` for local dev
- [ ] Cloud Run / GKE / Helm config as needed
- [ ] Environment secrets documented in `.env.example`

#### First Commit
- [ ] `git add -A && git commit -m "feat: initial project scaffold"`
- [ ] `git push origin main`
- [ ] Verify CI passes on first push

---

### Setup Commands

```bash
# 1. Create repo
gh repo create codeninja/<name> --private --description "..." --clone
cd <name>

# 2. Backend setup
mkdir -p backend/api backend/models backend/services backend/auth backend/tests backend/scripts backend/migrations
cd backend
uv init
uv add fastapi uvicorn sqlalchemy alembic pydantic-settings
uv add --dev pytest pytest-asyncio pytest-cov ruff aiosqlite

# 3. Frontend setup (if needed)
cd ..
pnpm create vite frontend -- --template react
cd frontend
echo "22" > .nvmrc
pnpm add axios react-router-dom
pnpm add -D vitest @testing-library/react @testing-library/jest-dom msw jsdom

# 4. Root files
# Create: Makefile, .env.example, .gitignore, CLAUDE.md, README.md
# Create: Dockerfile, docker-compose.yml
# Create: .github/workflows/ci.yml, .github/pull_request_template.md

# 5. Agent setup
claude init

# 6. Git hooks
make hooks

# 7. Initial commit
git add -A && git commit -m "feat: initial project scaffold"
git push origin main
```

---

## Backend Conventions (Python)

### App Entry (`main.py`)

Auto-discover routers — never manually import and mount each one:

```python
import importlib
import pkgutil
from fastapi import FastAPI, APIRouter
from api import *  # ensures package is loaded

app = FastAPI(title="ProjectName")

# Auto-discover all router modules in api/
for module_info in pkgutil.iter_modules(["api"]):
    module = importlib.import_module(f"api.{module_info.name}")
    for attr in dir(module):
        obj = getattr(module, attr)
        if isinstance(obj, APIRouter):
            app.include_router(obj)
```

This eliminates the #1 merge conflict source when multiple agents add routes in parallel.

### Config (`config.py`)

```python
from functools import lru_cache
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    jwt_secret: str
    frontend_url: str = "http://localhost:5173"
    # ... all config from .env

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

### Database (`database.py`)

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

### Models

- UUID primary keys (not auto-increment integers)
- Use `mapped_column` with type annotations
- JSONB for flexible/nested data
- Timestamps: `created_at`, `updated_at` on every model

### API Routes

- One file per resource domain in `api/`
- Use Pydantic schemas for all request/response bodies
- Dependency injection for auth (`get_current_user_dep`) and DB (`get_db`)
- Return proper HTTP status codes (201 for creates, 204 for deletes)

### Services

- Business logic lives in `services/`, not in route handlers
- One service per external integration or domain concern
- Async all the way down
- Import from actual modules, not `services/__init__.py`

---

## Frontend Conventions (JS/TS)

### Structure
- **Pages** in `src/pages/` — one per route
- **Components** in `src/components/` — reusable UI pieces
- **Context** in `src/context/` — React context providers (auth, theme, etc.)
- **API client** in `src/lib/api.js` — centralized Axios instance with interceptors

### Auth Pattern
```jsx
// AuthContext provides: user, login(), logout(), loading
// ProtectedRoute wraps authenticated pages
// Axios interceptor catches 401 → redirect to login
```

### Testing
- Vitest + React Testing Library + MSW
- Test files in `src/__tests__/`
- Test behavior, not implementation details
- Mock API calls with MSW handlers

---

## Database & Migrations

### Alembic Setup
```bash
cd backend
uv run alembic init migrations        # First time only
uv run alembic revision --autogenerate -m "description"
uv run alembic upgrade head
uv run alembic downgrade -1            # Rollback one
```

### Conventions
- Migration messages are descriptive: `add_user_timezone_column`, `create_notifications_table`
- Always test migrations up AND down
- Never edit a migration that's been pushed to main

### Dev Seed Script
Every project gets `backend/scripts/seed_dev.py`:
- Creates dev user(s) with known credentials
- Populates sample data across all models
- Prints a valid JWT token for immediate API testing
- Uses SQLite for local dev, Postgres for production
- Run with `make seed`

---

## Testing

### Backend (pytest)

**Configuration in `pyproject.toml`:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"
filterwarnings = ["ignore::DeprecationWarning"]
```

**Test fixtures (`conftest.py`):**
```python
# Use async in-memory SQLite for tests
# StaticPool for connection sharing across async contexts
# Override get_db dependency to use test session
# Create/drop tables per module (not per test — too slow)
```

**Commands:**
```bash
uv run pytest                          # Run all tests
uv run pytest tests/test_foo.py        # Run one file
uv run pytest -k "test_name"           # Run by name
uv run pytest --cov=. --cov-report=term-missing  # With coverage
```

**Rules:**
- Every new feature gets tests — no exceptions
- All tests must pass before pushing (enforced by pre-push hook)
- Target ≥85% coverage, ideally ≥90%
- Test edge cases: empty inputs, missing auth, invalid data, error paths
- E2E tests in `tests/e2e/` for critical user flows

### Frontend (Vitest)

```bash
pnpm test                              # Run tests
pnpm test -- --run                     # Run once (no watch)
pnpm test -- --coverage                # With coverage
```

---

## Linting & Formatting

### Python: ruff

**Configuration in `pyproject.toml`:**
```toml
[tool.ruff]
target-version = "py312"
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I"]   # errors, pyflakes, isort
```

**Commands:**
```bash
uv run ruff check .                    # Check for issues
uv run ruff check --fix .             # Auto-fix
uv run ruff format .                   # Format code
```

### JavaScript: ESLint

```bash
pnpm run lint                          # Check
pnpm run lint -- --fix                 # Auto-fix
```

### Pre-commit Auto-fix

The pre-commit hook automatically runs `ruff check --fix` + `ruff format` on staged Python files and `eslint --fix` on staged JS files, then re-stages the fixes. You never have to think about formatting.

---

## Makefile

Every project gets a root Makefile. This is the universal entry point — agents and humans use the same commands.

```makefile
.PHONY: test test-backend test-frontend coverage dev dev-down lint lint-backend lint-frontend seed build hooks

# Testing
test: test-backend test-frontend
test-backend:
	cd backend && uv run pytest tests/
test-frontend:
	cd frontend && pnpm test -- --run
coverage:
	cd backend && uv run pytest tests/ --cov=. --cov-report=term-missing

# Development
dev:
	docker compose up -d
dev-down:
	docker compose down
seed:
	cd backend && uv run python scripts/seed_dev.py

# Linting
lint: lint-backend lint-frontend
lint-backend:
	cd backend && uv run ruff check .
lint-frontend:
	cd frontend && pnpm run lint

# Build
build:
	docker compose build
build-frontend:
	cd frontend && pnpm run build

# Setup
hooks:
	git config core.hooksPath .githooks
	chmod +x .githooks/*
```

---

## Git Workflow

### Branching
- `main` is the production branch — always deployable
- Feature branches: `feat/issue-{N}-{short-slug}`
- Fix branches: `fix/issue-{N}-{short-slug}`
- Never commit directly to main (except docs-only changes)

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/):
```
feat: add user profile endpoint
fix: handle null timezone in meetup scheduling
refactor: auto-discover API routers in main.py
test: add e2e test for full listing flow
docs: update CLAUDE.md with agent workflow
chore: update dependencies
```

### Pull Requests
- One PR per GitHub issue (or batch related small issues)
- PR title **must** include `closes #N` to auto-close the linked issue
- Fill out the PR template (What, Changes, Testing, Checklist)
- All CI checks must pass before merge
- Merge to main (not squash, not rebase — merge commits preserve history)

### Worktrees for Parallel Work
When working on multiple features simultaneously:
```bash
git worktree add /tmp/project-{issue#} -b feat/issue-{N}-{slug}
cd /tmp/project-{issue#}
# ... work ...
# Clean up after merge:
git worktree remove /tmp/project-{issue#}
```

---

## CI/CD

### GitHub Actions (`.github/workflows/ci.yml`)

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.run_id }}
  cancel-in-progress: true

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: astral-sh/setup-uv@v6
        with:
          enable-cache: true
          cache-dependency-glob: backend/uv.lock
      - run: uv sync
      - run: uv run pytest tests/ -v --tb=short --cov=. --cov-report=term-missing

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: pnpm
          cache-dependency-path: frontend/pnpm-lock.yaml
      - run: pnpm install
      - run: pnpm test -- --run
      - run: pnpm run build
```

**Key points:**
- Backend and frontend run in **parallel** jobs
- Concurrency group cancels in-progress runs for the same PR (saves CI minutes)
- uv cache via `astral-sh/setup-uv` action
- pnpm cache via `pnpm/action-setup` + `setup-node` cache

---

## Pre-commit Hooks

### Setup
```bash
make hooks   # Sets git config core.hooksPath and chmod +x
```

### Pre-commit (`.githooks/pre-commit`)
- Runs `ruff check --fix` + `ruff format` on staged `.py` files
- Runs `eslint --fix` on staged `.js`/`.jsx`/`.ts`/`.tsx` files
- Re-stages fixed files automatically
- Commit proceeds with clean code — zero manual intervention

### Pre-push (`.githooks/pre-push`)
- Runs full backend test suite (`make test-backend`)
- Runs full frontend test suite (`make test-frontend`)
- **Blocks push** if any test fails

### Bypass
Agents using `--no-verify` or `--dangerously-skip-permissions` can bypass hooks when needed. CI is the safety net.

---

## Docker & Local Dev

### docker-compose.yml
```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: projectname
      POSTGRES_USER: dev
      POSTGRES_PASSWORD: dev
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dev"]
      interval: 5s
      retries: 5

  backend:
    build:
      context: .
      target: backend-dev  # if multi-stage
    ports: ["8000:8000"]
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./backend:/app/backend

  frontend:
    build:
      context: ./frontend
    ports: ["5173:5173"]
    volumes:
      - ./frontend/src:/app/src

volumes:
  pgdata:
```

### Dockerfile (Multi-stage Production)
```dockerfile
# Stage 1: Build frontend
FROM node:22-slim AS frontend-build
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@latest --activate
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ .
RUN pnpm run build

# Stage 2: Python backend + static frontend
FROM python:3.12-slim
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ .
COPY --from=frontend-build /app/dist ./static
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Deployment

### Target: Google Cloud (GKE)
- Helm charts in `helm/` directory
- Google OAuth for auth
- Cloud SQL (PostgreSQL) or in-cluster Postgres
- Container Registry / Artifact Registry for images
- Managed certificates for HTTPS

### Helm Structure
```
helm/projectname/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── secrets.yaml
│   ├── hpa.yaml           # Horizontal Pod Autoscaler
│   └── backend-config.yaml # GKE-specific (health checks, timeouts)
```

### Health Check
Every backend exposes `GET /health` returning `{"status": "healthy"}`.

---

## Environment & Secrets

### `.env.example`
```bash
# Database
DATABASE_URL=postgresql+asyncpg://dev:dev@localhost:5432/projectname

# Auth (get from Google Cloud Console → APIs & Services → Credentials)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-your-client-secret

# AI (get from Google AI Studio → API Keys)
GEMINI_API_KEY=your-gemini-api-key

# App
JWT_SECRET=change-me-to-a-random-string
FRONTEND_URL=http://localhost:5173
```

**Rules:**
- `.env.example` has **placeholders only** — NEVER real keys
- `.env` is in `.gitignore` — NEVER committed
- Production secrets go in Kubernetes Secrets or Secret Manager
- Comments in `.env.example` explain where to get each value

---

## GitHub Project Management

### Issues
- Every feature, bug, or task gets a GitHub issue
- Issues are organized into milestones (M1, M2, M3...)
- Labels: `feat`, `fix`, `dx`, `security`, `infrastructure`, `frontend`, `backend`, `blocked`

### Milestones
Order by dependency and risk:
1. **Core API** — CRUD, basic endpoints
2. **Services & Hardening** — business logic, error handling, edge cases
3. **Infrastructure & Security** — auth, rate limiting, migrations, CSRF
4. **Frontend Integration** — wire UI to APIs, real-time features
5. **External Integrations** — third-party APIs, plugins (highest risk, last)
6. **DX & Tooling** — CI, linting, hooks, Makefile, dev ergonomics

### Workflow
1. Create issue with clear acceptance criteria
2. Create feature branch: `feat/issue-{N}-{slug}`
3. Implement, test, commit, push
4. Open PR with `closes #{N}` in title
5. CI passes → merge → issue auto-closes
6. Pull main, run tests, verify

---

## Agent Workflow (Agentic Development)

When Claude Code or other coding agents work on this project:

### Launch Pattern
```bash
# Create isolated worktree
git worktree add /tmp/project-{N} -b feat/issue-{N}-{slug}

# Launch agent
cd /tmp/project-{N} && claude --dangerously-skip-permissions "Task description..."
```

### Rules for Agents
1. **All tests must pass** before committing — run `make test`
2. **Never manually import routers** in `main.py` — auto-discovery handles it
3. **Don't modify `__init__.py` re-exports** — import from actual modules
4. **Commit message format**: `feat: description (closes #N)`
5. **Push the branch** and note the remote URL
6. After push, create PR or let the orchestrator handle it

### Parallel Execution
- Max 3 agents in parallel using separate worktrees
- Each agent works on a different issue/branch
- Merge conflicts are resolved manually on main after sequential merges
- Common conflict hotspots: `main.py` (router mounts), `__init__.py` (re-exports) — auto-discovery eliminates these

### Signal 9 = Normal Exit
When a Claude Code background process exits with signal 9, it means the task **finished normally** — NOT a crash. Always check `process action:log` before assuming failure. Restarting without checking wastes tokens and duplicates work.

### Timeout Recovery
If an agent times out before committing:
```bash
cd /tmp/project-{N}
git add -A
git commit -m "feat: description (closes #N)"
git push origin feat/issue-{N}-{slug}
gh pr create --title "feat: description (closes #N)" --body "..." --head feat/issue-{N}-{slug}
```

---

## CLAUDE.md Template

Every repo gets a `CLAUDE.md` at the root. Here's the template:

```markdown
# CLAUDE.md

## Project Overview
One paragraph: what this project does and why it exists.

## Commands
### Backend
cd backend && uv sync / uv run pytest / uv run uvicorn main:app --reload

### Frontend
cd frontend && pnpm install / pnpm test / pnpm run dev

### Docker
docker compose up -d

## Architecture
ASCII tree of key directories and files with one-line descriptions.

## Key Patterns
Bullet list of architectural decisions (async, auth flow, AI pipeline, etc.)

## Agent Workflow
- Branching: feat/issue-{N}-{slug}
- Commits: conventional commits with closes #{N}
- Testing: all tests must pass (make test)
- Key files: list files agents must not manually edit
- Makefile: make test / make lint / make seed / make hooks

## Environment
List of .env variables with descriptions.

## Deployment
How to build and deploy (Docker, Helm, GKE, etc.)
```

---

## PR Template

`.github/pull_request_template.md`:
```markdown
## What
Closes #

## Changes
-

## Testing
- [ ] All existing tests pass (`make test`)
- [ ] New tests added for new functionality
- [ ] Coverage maintained above 85%

## Checklist
- [ ] Branch based on latest `main`
- [ ] Conventional commit messages
- [ ] No new linting warnings (`make lint`)
```

---

## Anti-Patterns

Things we explicitly **do not do**:

| ❌ Anti-Pattern | ✅ What We Do Instead |
|---|---|
| pip install / poetry / pipenv | `uv` for all Python package management |
| npm / yarn | `pnpm` for all JS package management |
| Manual router imports in main.py | Auto-discovery with `pkgutil.iter_modules` |
| Fat `__init__.py` re-exports | Import from actual modules directly |
| Real secrets in `.env.example` | Placeholders with comments on where to get values |
| Tests optional / "I'll add them later" | Tests are required. No merge without tests. |
| Manual formatting | ruff + eslint auto-fix in pre-commit hooks |
| Manual CI validation | GitHub Actions on every push and PR |
| Squash merge | Merge commits (preserve branch history) |
| Magical abstractions | Explicit, readable, traceable code |
| Overloaded god-objects | Small, focused modules with clear ownership |
| Implicit global state | Dependency injection, explicit config |

---

## Quick Reference

```bash
# Start working
make hooks                   # First time setup
make dev                     # Start local stack
make seed                    # Populate dev data

# Daily workflow
make test                    # Run all tests
make lint                    # Check lint
make coverage                # Coverage report

# Feature work
git worktree add /tmp/proj-{N} -b feat/issue-{N}-{slug}
# ... implement ...
make test                    # Verify
git add -A && git commit -m "feat: thing (closes #N)"
git push origin feat/issue-{N}-{slug}
gh pr create --title "feat: thing (closes #N)"
```

---

*Last updated: 2026-02-18. This is a living document — update it when conventions evolve.*
