# CLAUDE.md
## Project Overview
Wikifi — initialized scaffold. Clarify primary language, UI needs (NiceGUI vs React), DB (Postgres), and deploy target.

## Commands
- make hooks
- make dev
- make test

## Architecture
Backend (FastAPI) + optional Frontend (React/Vite). Dockerized local stack. CI runs tests.

## Key Patterns
- Explicit schemas with Pydantic
- Auto router discovery in backend/api

## Agent Workflow
Use /develop skill for implementation once spec is ready.

## Environment
See .env.example.

## Deployment
Docker/Helm; target GKE by default (to be configured).
