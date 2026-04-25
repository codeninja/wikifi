# Wikifi

One-line description: TBD.

## Overview
Initialized with OpenClaw project-init skill. Standard scaffold with backend (Python/FastAPI), optional frontend (React/Vite), CI, and Docker.

## Tech Stack
- Python 3.12 + FastAPI, SQLAlchemy, Alembic, Pydantic, uv
- Optional React + Vite + Tailwind (pnpm)
- Docker + Docker Compose
- GitHub Actions CI

## Setup
```bash
make hooks
# Backend setup
cd backend && uv init && uv add fastapi "sqlalchemy>=2" alembic pydantic pydantic-settings pytest pytest-asyncio pytest-cov ruff && cd ..
# Frontend setup (optional)
cd frontend && pnpm init -y && pnpm add react react-dom && pnpm add -D vite typescript @types/react @types/react-dom vitest @testing-library/react jsdom eslint && cd ..
```

## Usage
- make dev — start local stack
- make test — run tests for backend and frontend

## Status
Fresh scaffold. Fill in SPEC and implementation plan next.
