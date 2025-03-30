.PHONY: install test test-coverage lint format clean clean-install build run

# Python and pip
PYTHON = python
PIP = pip

# Testing
PYTEST = pytest

# Linting and type checking
MYPY = mypy
RUFF = ruff

# Directories
SRC_DIR = src
TEST_DIR = tests

# Setup development environment
install:
	$(PIP) install -e ".[dev]"

# Run tests
test:
	$(PYTEST) $(TEST_DIR) -v -o log_cli=true --cache-clear

# Run tests with coverage
test-coverage:
	$(PYTEST) $(TEST_DIR) -v -o log_cli=true --cache-clear --cov=src --cov-report=term:skip-covered

# Run linting and type checking
lint:
	$(RUFF) check $(SRC_DIR) $(TEST_DIR)	
	$(MYPY) $(SRC_DIR) --cache-fine-grained
	$(MYPY) $(TEST_DIR) --cache-fine-grained

# Format and fix ruff issues
format:
	$(RUFF) check --fix $(SRC_DIR) $(TEST_DIR)	
	$(RUFF) format $(SRC_DIR) $(TEST_DIR)

# Clean build artifacts, dependencies, caches and __pycache__ directories
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	$(PIP) freeze | grep -v "^-e" | xargs $(PIP) uninstall -y

# Clean and install dependencies
clean-install: clean install

# Build package
build:
	$(PYTHON) -m build

# Run the application
run:
	$(PYTHON) -m service_ml_forecast.main

# Help command
help:
	@echo "Available commands:"
	@echo "  install       - Install dependencies"
	@echo "  test          - Run tests"
	@echo "  test-coverage - Run tests with coverage"
	@echo "  lint          - Run linting and type checking"
	@echo "  format        - Run formatter"
	@echo "  clean         - Clean virtual environment"
	@echo "  clean-install - Clean and install dependencies"
	@echo "  build         - Build package for distribution"
	@echo "  run           - Run the application"
	@echo "  help          - Show this help message"

# Default target
.DEFAULT_GOAL := help
