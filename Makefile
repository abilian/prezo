.PHONY: all test build format check lint clean

all:
	uv run pytest
	uv run ruff format . --check
	uv run ruff check .
	uv run pyrefly check src

check: lint

lint:
	uv run ruff check .
	uv run ruff format . --check
	uv run pyrefly check src

format:
	uv run ruff format .
	uv run ruff check . --fix
	uv run ruff format .

test:
	uv run pytest

test-cov:
	uv run pytest --cov=prezo --cov-report=html --cov-report=term tests

clean:
	rm -rf .pytest_cache .ruff_cache dist build __pycache__ .mypy_cache \
		.coverage htmlcov .coverage.* *.egg-info
	adt clean

build: clean
	uv build

publish: build
	uv publish
