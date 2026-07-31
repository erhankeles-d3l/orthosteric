# Single executable source of truth for command invocations (ENG §22).
# Task names are listed in CLAUDE.md §16; contracts in ENG §22.
.DEFAULT_GOAL := help
PKG := orthosteric
PY  := python3

.PHONY: help install test lint format typecheck docs ci-local clean

help: ## List targets
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-12s %s\n",$$1,$$2}'

install: ## Sync the pinned environment from the lockfile; resolve nothing new
	$(PY) -m pip install -e ".[dev]" --quiet

test: ## Run the full suite; deterministic, no network
	$(PY) -m pytest --cov --cov-report=term-missing

lint: ## Static checks requiring no type information; read-only
	$(PY) -m ruff check src tests scripts
	$(PY) -m ruff format --check src tests scripts

format: ## Apply formatting; the only target that modifies source
	$(PY) -m ruff format src tests scripts
	$(PY) -m ruff check --fix src tests scripts

typecheck: ## Strict type checking over src and tests
	$(PY) -m mypy

docs: ## Build documentation strictly; warnings are failures
	$(PY) -m mkdocs build --strict

ci-local: ## The complete Phase 1 CI sequence, offline, stopping at first failure
	$(PY) -m ruff check src tests scripts
	$(PY) -m ruff format --check src tests scripts
	$(PY) -m mypy
	$(PY) -m pytest --cov --cov-report=term-missing
	PYTHONPATH=src lint-imports --config .importlinter
	$(PY) scripts/checks/tests_mirror_src.py
	$(PY) scripts/checks/seal_timestamp.py
	$(PY) scripts/checks/no_fill_markers.py
	$(PY) scripts/checks/no_s8c_significance_test.py
	$(PY) scripts/checks/lockfile_requires_adr.py

clean: ## Remove build and cache artefacts
	rm -rf .mypy_cache .ruff_cache .pytest_cache htmlcov .coverage site dist build
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
