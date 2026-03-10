# Run from ai_plotter directory. Activate .venv first.
.PHONY: test lint fmt

test:
	cd "$(CURDIR)" && python -m pytest

lint:
	ruff check . tests
	ruff format --check .

fmt:
	ruff format .
	ruff check --fix .
