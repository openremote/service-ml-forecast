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
import shutil


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
DEPLOYMENT_WEB_DIR: Path = Path(f"{_PROJECT_ROOT}/deployment/web/")

# Packages directory
PACKAGES_DIR: Path = Path(f"{_PROJECT_ROOT}/packages")


def get_package_dirs() -> list[Path]:
    """Get all package directories."""
    if not PACKAGES_DIR.exists():
        return []

    return [pkg_dir for pkg_dir in PACKAGES_DIR.iterdir() if pkg_dir.is_dir() and (pkg_dir / "pyproject.toml").exists()]


def step(cmd: str, description: str = "", dir: Path | None = _PROJECT_ROOT) -> None:
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
    print("  lint                   - Run linting (main + packages)")
    print("  format                 - Format the code (main + packages)")
    print("  test                   - Run tests (main + packages)")
    print("  test-coverage          - Run tests with coverage (main + packages)")
    print("  build                  - Build the backend and packages")
    print("  build-frontend         - Build the frontend bundle")
    print("  build-frontend-dev     - Build the frontend bundle in development mode")
    print("  lint-packages          - Run linting only on packages")
    print("  test-packages          - Run tests only on packages")
    print("  build-packages         - Build all packages")


def start() -> None:
    """Start the backend."""
    step("uv run -m service_ml_forecast.main", "service-ml-forecast")


def lint() -> None:
    """Run linting on the backend src and all packages."""

    # Lint main project
    step(f"uv run ruff check {SRC_DIR} {TEST_DIR}", "ruff checks (main)")
    step(f"uv run mypy --cache-fine-grained {SRC_DIR} {TEST_DIR}", "mypy checks (main)")

    # Lint packages
    lint_packages()


def lint_packages() -> None:
    """Run linting only on packages."""
    package_dirs = get_package_dirs()

    for pkg_dir in package_dirs:
        pkg_name = pkg_dir.name
        print(f"\n--- Linting package: {pkg_name} ---")

        # Check if package has src directory
        src_dir = pkg_dir / "src"
        test_dir = pkg_dir / "tests"

        if src_dir.exists():
            step(f"uv run ruff check {src_dir}", f"ruff checks ({pkg_name})", pkg_dir)
            step(f"uv run mypy --cache-fine-grained {src_dir}", f"mypy checks ({pkg_name})", pkg_dir)

        if test_dir.exists():
            step(f"uv run ruff check {test_dir}", f"ruff checks tests ({pkg_name})", pkg_dir)
            step(f"uv run mypy --cache-fine-grained {test_dir}", f"mypy checks tests ({pkg_name})", pkg_dir)


def format() -> None:
    """Format the backend src and all packages."""

    # Format main project
    step(f"uv run ruff format {SRC_DIR} {TEST_DIR}", "ruff formatting (main)")
    step(f"uv run ruff check --fix {SRC_DIR} {TEST_DIR}", "ruff check and fix (main)")

    # Format packages
    format_packages()


def format_packages() -> None:
    """Format only packages."""
    package_dirs = get_package_dirs()

    for pkg_dir in package_dirs:
        pkg_name = pkg_dir.name
        print(f"\n--- Formatting package: {pkg_name} ---")

        # Check if package has src directory
        src_dir = pkg_dir / "src"
        test_dir = pkg_dir / "tests"

        if src_dir.exists():
            step(f"uv run ruff format {src_dir}", f"ruff formatting ({pkg_name})", pkg_dir)
            step(f"uv run ruff check --fix {src_dir}", f"ruff check and fix ({pkg_name})", pkg_dir)

        if test_dir.exists():
            step(f"uv run ruff format {test_dir}", f"ruff formatting tests ({pkg_name})", pkg_dir)
            step(f"uv run ruff check --fix {test_dir}", f"ruff check and fix tests ({pkg_name})", pkg_dir)


def test() -> None:
    """Run pytest on main project and all packages."""

    # Test main project
    step(f"uv run pytest {TEST_DIR} -v --cache-clear -s", "pytest (main)")

    # Test packages
    test_packages()


def test_packages() -> None:
    """Run tests only on packages."""
    package_dirs = get_package_dirs()

    for pkg_dir in package_dirs:
        pkg_name = pkg_dir.name
        test_dir = pkg_dir / "tests"

        if test_dir.exists():
            print(f"\n--- Testing package: {pkg_name} ---")
            step(f"uv run pytest {test_dir} -v --cache-clear -s", f"pytest ({pkg_name})", pkg_dir)


def test_coverage() -> None:
    """Run tests with coverage on main project and all packages."""

    # Test main project with coverage
    step(f"uv run pytest {TEST_DIR} -v --cache-clear --cov {SRC_DIR} -s", "pytest with coverage (main)")

    # Test packages with coverage
    package_dirs = get_package_dirs()

    for pkg_dir in package_dirs:
        pkg_name = pkg_dir.name
        src_dir = pkg_dir / "src"
        test_dir = pkg_dir / "tests"

        if test_dir.exists() and src_dir.exists():
            print(f"\n--- Testing package with coverage: {pkg_name} ---")
            step(
                f"uv run pytest {test_dir} -vv --cache-clear --cov {src_dir} -s",
                f"pytest with coverage ({pkg_name})",
                pkg_dir,
            )


def build() -> None:
    """Build backend."""

    # Build the backend
    step("uv build", "Building backend")


def build_packages() -> None:
    """Build all packages."""
    package_dirs = get_package_dirs()

    for pkg_dir in package_dirs:
        pkg_name = pkg_dir.name
        print(f"\n--- Building package: {pkg_name} ---")
        step("uv build", f"Building {pkg_name}", pkg_dir)


def build_frontend() -> None:
    """Build the frontend bundle and copy to deployment/web."""

    step(f"npm run build:prod", "Building frontend in frontend directory", FRONTEND_DIR)

    _copy_frontend_dist()


def build_frontend_dev() -> None:
    """Build the frontend bundle and copy to deployment/web."""

    step(f"npm run build:dev", "Building frontend in frontend directory", FRONTEND_DIR)

    _copy_frontend_dist()


def _copy_frontend_dist() -> None:
    """Copy the frontend dist to the deployment/web directory."""
    DEPLOYMENT_WEB_DIR.mkdir(parents=True, exist_ok=True)

    if DEPLOYMENT_WEB_DIR.exists():
        shutil.rmtree(DEPLOYMENT_WEB_DIR)

    shutil.copytree(FRONTEND_DIR / "dist", DEPLOYMENT_WEB_DIR / "dist")

    print(f"Frontend dist copied to {DEPLOYMENT_WEB_DIR}")
