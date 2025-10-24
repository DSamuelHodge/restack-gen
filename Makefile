.PHONY: help setup install install-dev fmt lint typecheck test test-fast test-cov clean

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup:  ## Install dependencies and pre-commit hooks
	python -m pip install --upgrade pip
	pip install -e ".[dev]"
	pre-commit install

install:  ## Install package only
	pip install -e .

install-dev:  ## Install package with dev dependencies
	pip install -e ".[dev]"

fmt:  ## Format code with black and ruff
	black restack_gen tests
	ruff check --fix restack_gen tests

lint:  ## Lint code with ruff
	ruff check restack_gen tests
	black --check restack_gen tests

typecheck:  ## Run mypy type checking
	mypy restack_gen

test:  ## Run all tests
	pytest

test-fast:  ## Run tests without slow ones
	pytest -m "not slow"

test-cov:  ## Run tests with coverage report
	pytest --cov=restack_gen --cov-report=term-missing --cov-report=html

test-integration:  ## Run integration tests only
	pytest -m integration

clean:  ## Clean up build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build:  ## Build distribution packages
	python -m build

release:  ## Build and upload to PyPI (requires credentials)
	python -m build
	python -m twine upload dist/*

.DEFAULT_GOAL := help
