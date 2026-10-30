.PHONY: audit test lint format-check
audit:
	uv run idxavm audit-data
test:
	uv run --extra dev pytest -q
lint:
	uv run --extra dev ruff check .
format-check:
	uv run --extra dev ruff format --check .

