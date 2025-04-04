#!/usr/bin/env python
"""
Scripts for various tasks such as linting, formatting, testing, etc.

These are callable via `uv run <script_name>` from the root of the project.

They are listed in the `[project.scripts]` section of pyproject.toml.
"""

import shlex
import subprocess
import sys

SRC_DIR = "src/service_ml_forecast"
TEST_DIR = "tests"


def step(cmd: str, description: str = "") -> None:
    """Run a command with proper error handling."""
    if description:
        print(f"Running: {description}")
    try:
        subprocess.run(shlex.split(cmd), check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        sys.exit(1)


def start() -> None:
    """Start the application."""
    step("uv run -m service_ml_forecast.main", "service-ml-forecast")


def lint() -> None:
    """Run linting."""
    step(f"uv run ruff check {SRC_DIR} {TEST_DIR}", "ruff checks")
    step(f"uv run mypy --cache-fine-grained {SRC_DIR} {TEST_DIR}", "mypy checks")


def format() -> None:
    """Format the code."""
    step(f"uv run ruff format {SRC_DIR} {TEST_DIR}", "ruff formatting")
    step(f"uv run ruff check --fix {SRC_DIR} {TEST_DIR}", "ruff check and fix")


def test() -> None:
    """Run tests."""
    step(f"uv run pytest {TEST_DIR} -vv --cache-clear", "tests")


def test_coverage() -> None:
    """Run tests with coverage."""
    step(f"uv run pytest {TEST_DIR} -vv --cache-clear --cov {SRC_DIR}", "tests with coverage")


def build() -> None:
    """Build package."""
    step("uv build", "Building package")
