#!/usr/bin/env python
"""
Scripts for various tasks such as linting, formatting, testing, etc.

These are callable via `uv run <script_name>` from the root of the project.

They are listed in the `[project.scripts]` section of pyproject.toml.
"""

import shlex
import subprocess
import sys
from pathlib import Path


def find_project_root(start_path: Path = Path(__file__)) -> Path:
    """Find the project root by looking for marker files."""
    current = start_path.parent
    while current != current.parent:
        if any((current / marker).exists() for marker in ["pyproject.toml", ".env"]):
            return current
        current = current.parent
    raise RuntimeError("Could not find project root")


_PROJECT_ROOT = find_project_root()

# Source directory
SRC_DIR: Path = Path(f"{_PROJECT_ROOT}/src/service_ml_forecast")
TEST_DIR: Path = Path(f"{_PROJECT_ROOT}/tests")
FRONTEND_DIR: Path = Path(f"{_PROJECT_ROOT}/frontend")

# Deployment directory
DEPLOYMENT_DIR: Path = Path(f"{_PROJECT_ROOT}/deployment")
DEPLOYMENT_WEB_DIR: Path = Path(f"{DEPLOYMENT_DIR}/web")



def step(cmd: str, description: str = "", dir: Path | None = None) -> None:
    """Run a command with proper error handling."""

    if description:
        print(f"Running: {description}")
    try:
        if dir:
            subprocess.run(shlex.split(cmd), check=True, cwd=dir)
        else:
            subprocess.run(shlex.split(cmd), check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")
        sys.exit(1)


def help() -> None:
    """Print help."""

    print("Available commands:")
    print("  help                   - Print help")
    print("  start                  - Start the backend")
    print("  lint                   - Run linting")
    print("  format                 - Format the code")
    print("  test                   - Run tests")
    print("  test-coverage          - Run tests with coverage")
    print("  build                  - Build the backend")
    print("  build-frontend         - Build the frontend bundle")
    print("  build-all              - Build the backend and frontend bundle")


def start() -> None:
    """Start the backend."""
    step("uv run -m service_ml_forecast.main", "service-ml-forecast", _PROJECT_ROOT)


def lint() -> None:
    """Run linting on the backend src."""

    step(f"uv run ruff check {SRC_DIR} {TEST_DIR}", "ruff checks", _PROJECT_ROOT)
    step(f"uv run mypy --cache-fine-grained {SRC_DIR} {TEST_DIR}", "mypy checks", _PROJECT_ROOT)

def format() -> None:
    """Format the backend src."""

    step(f"uv run ruff format {SRC_DIR} {TEST_DIR}", "ruff formatting", _PROJECT_ROOT)
    step(f"uv run ruff check --fix {SRC_DIR} {TEST_DIR}", "ruff check and fix", _PROJECT_ROOT)


def test() -> None:
    """Run pytest."""

    step(f"uv run pytest {TEST_DIR} -vv --cache-clear", "pytest", _PROJECT_ROOT)


def test_coverage() -> None:
    """Run tests with coverage."""

    step(f"uv run pytest {TEST_DIR} -vv --cache-clear --cov {SRC_DIR}", "pytest with coverage", _PROJECT_ROOT)


def build() -> None:
    """Build backend."""

    # Build the backend
    step("uv build", "Building backend", _PROJECT_ROOT)


def build_frontend() -> None:
    """Build the frontend bundle."""

    step(f"npm run build", "Building frontend in frontend directory", FRONTEND_DIR)
    step(f"cp -r {FRONTEND_DIR}/dist {DEPLOYMENT_WEB_DIR}", "Copying dist to deployment", _PROJECT_ROOT)


def build_all() -> None:
    """Build the package and frontend."""

    build()
    build_frontend()
