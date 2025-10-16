.PHONY: help setup init lint format test clean run_pipeline

# Default target - show help
help:
	@echo "LOAC QA Pipeline - Available targets:"
	@echo ""
	@echo "  make setup (or init)  - Install dependencies (run after git clone)"
	@echo "  make lint             - Run ruff linter and format checker"
	@echo "  make format           - Auto-fix code style with ruff"
	@echo "  make test             - Run linter + test suite"
	@echo "  make clean            - Remove generated data and cache (prompts first)"
	@echo "  make run_pipeline ... - Run pipeline with args (e.g., make run_pipeline eval --model gpt-4o)"
	@echo ""

# Setup/init - install all dependencies
setup init:
	@echo "Installing dependencies..."
	uv sync
	@echo "✓ Setup complete! Run 'make test' to verify."

# Lint - check code quality and formatting
lint:
	@echo "Running ruff linter..."
	uv run ruff check src/ tests/
	@echo "Checking code formatting..."
	uv run ruff format --check src/ tests/
	@echo "✓ Lint checks passed!"

# Format - auto-fix code style
format:
	@echo "Formatting code with ruff..."
	uv run ruff check --fix src/ tests/
	uv run ruff format src/ tests/
	@echo "✓ Code formatted!"

# Test - run lint then test suite
test: lint
	@echo "Running test suite..."
	uv run pytest
	@echo "✓ All tests passed!"

# Clean - remove generated artifacts (with confirmation)
clean:
	@echo "WARNING: This will delete all generated data and cache."
	@echo -n "Continue? [y/N] " && read ans && [ $${ans:-N} = y ]
	@echo "Cleaning data and cache directories..."
	rm -rf data/* cache/* .pytest_cache
	@echo "✓ Cleaned!"

