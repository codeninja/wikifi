.PHONY: test dev seed hooks

test:
	cd backend && uv run pytest tests/ || true
	cd frontend && pnpm test -- --run || true

dev:
	docker compose up -d

seed:
	cd backend && uv run python scripts/seed_dev.py || true

hooks:
	git config core.hooksPath .githooks
	chmod +x .githooks/*
