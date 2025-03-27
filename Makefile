.PHONY: install test lint format clean build run

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
	$(PIP) freeze > requirements.txt
	$(PIP) uninstall -r requirements.txt -y
	rm -rf requirements.txt

# Build package
build:
	$(PYTHON) -m build

# Run the application
run:
	$(PYTHON) -m service_ml_forecast.main

# Help command
help:
	@echo "Available commands:"
	@echo "  install  - Install package in development mode with all dependencies"
	@echo "  test     - Run tests"
	@echo "  lint     - Run linting and type checking"
	@echo "  format   - Format code with ruff"
	@echo "  clean    - Clean build artifacts"
	@echo "  build    - Build package for distribution"
	@echo "  run      - Run the application in development mode"
	@echo "  help     - Show this help message"

# Default target
.DEFAULT_GOAL := help
