.DEFAULT_GOAL := help
.PHONY: help install setup format check test precommit

POETRY_RUN := poetry run
TEST_ARGS := -m django test tests --settings=tests.settings -v 2

help: ## Show this help message.
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install project dependencies (Poetry)
	@poetry install

setup: ## Create .venv and install dependencies (no Poetry required)
	@python3 -m venv .venv
	@.venv/bin/pip install --upgrade pip
	@.venv/bin/pip install -e ".[full]"
	@.venv/bin/pip install pytest pytest-django pytest-cov ruff djangorestframework django-ratelimit
	@echo "Setup complete. Run 'make test' to verify."

format: ## Format code and fix linting
	@$(POETRY_RUN) ruff check . --fix

check: ## Check code formatting and linting
	@$(POETRY_RUN) ruff check .

test: ## Run the test suite
	@echo "Running tests..."
	@if command -v poetry >/dev/null 2>&1 && $(POETRY_RUN) python -c "import sys" >/dev/null 2>&1; then \
		echo "Using Poetry environment"; \
		$(POETRY_RUN) python $(TEST_ARGS); \
	elif [ -x .venv/bin/python ] && .venv/bin/python -c "import sys" >/dev/null 2>&1; then \
		echo "Using project .venv"; \
		.venv/bin/python $(TEST_ARGS); \
	elif command -v python3 >/dev/null 2>&1; then \
		echo "Using system python3"; \
		python3 $(TEST_ARGS); \
	else \
		echo "No working test runner found. Install dependencies with: poetry install"; \
		exit 1; \
	fi

precommit: ## Install pre-commit hooks
	@poetry add --group dev pre-commit || true
	@$(POETRY_RUN) pre-commit install
