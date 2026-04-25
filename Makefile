.PHONY: test lint format coverage hooks init walk clean

# --- testing -----------------------------------------------------------------
test:
	uv run pytest

coverage:
	uv run pytest --cov=wikifi --cov-report=term-missing

init:
	uv run wikifi init .

walk:
	uv run wikifi walk .

# --- lint / format -----------------------------------------------------------
lint:
	uv run ruff check .
	uv run ruff format --check .

format:
	uv run ruff check --fix .
	uv run ruff format .

# --- repo plumbing -----------------------------------------------------------
hooks:
	git config core.hooksPath .githooks
	chmod +x .githooks/*

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov dist build
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
