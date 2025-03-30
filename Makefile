.PHONY: install test lint format clean clean-install build run

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
test-cov:
	$(PYTEST) $(TEST_DIR) -v -o log_cli=true --cache-clear --cov=src --cov-report=term:skip-covered

# Run formatting, linting and type checking
lint:
	$(RUFF) check $(SRC_DIR) $(TEST_DIR)
	$(MYPY) $(SRC_DIR) --cache-fine-grained

# Format code
format:
	$(RUFF) format $(SRC_DIR) $(TEST_DIR)
	$(RUFF) check --fix $(SRC_DIR) $(TEST_DIR)

# Clean build artifacts and dependencies
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
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
	@echo "  install  - Install dependencies"
	@echo "  test     - Run tests"
	@echo "  test-cov - Run tests with coverage"
	@echo "  lint     - Run linting and type checking"
	@echo "  format   - Format code with ruff"
	@echo "  clean    - Clean virtual environment"
	@echo "  clean-install - Clean and install dependencies"
	@echo "  build    - Build package for distribution"
	@echo "  run      - Run the application in development mode"
	@echo "  help     - Show this help message"

# Default target
.DEFAULT_GOAL := help
