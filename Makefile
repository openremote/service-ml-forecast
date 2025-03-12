.PHONY: install test lint format clean build run

# Python and pip
PYTHON = python
PIP = pip

# Testing
PYTEST = pytest

# Code formatting
BLACK = black
ISORT = isort

# Linting and type checking
MYPY = mypy
FLAKE8 = flake8

# Directories
SRC_DIR = src
TEST_DIR = tests

# Setup development environment
install:
	$(PIP) install -e ".[dev]"

# Run tests
test:
	$(PYTEST) $(TEST_DIR)

# Run linting
lint:
	$(FLAKE8) $(SRC_DIR) $(TEST_DIR)
	$(MYPY) $(SRC_DIR)

# Format code
format:
	$(BLACK) $(SRC_DIR) $(TEST_DIR)
	$(ISORT) $(SRC_DIR) $(TEST_DIR)

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
build: clean
	$(PYTHON) -m build

# Run the application
run:
	uvicorn service_ml_forecast.main:app --reload

# Help command
help:
	@echo "Available commands:"
	@echo "  install  - Install package in development mode with all dependencies"
	@echo "  test     - Run tests"
	@echo "  lint     - Run linting tools"
	@echo "  format   - Format code with black and isort"
	@echo "  clean    - Clean build artifacts"
	@echo "  build    - Build package for distribution"
	@echo "  run      - Run the application in development mode"
	@echo "  help     - Show this help message"

# Default target
.DEFAULT_GOAL := help
