# service-ml-forecast
[![Lint and Test](https://github.com/openremote/service-ml-forecast/actions/workflows/ci.yml/badge.svg)](https://github.com/openremote/service-ml-forecast/actions/workflows/ci.yml?query=branch%3Amain)
[![Open Source? Yes!](https://badgen.net/badge/Open%20Source%20%3F/Yes%21/blue?icon=github)](https://github.com/Naereen/badges/)

## Installation
This project uses [uv](https://docs.astral.sh/uv/) for project management. `uv` is a Python package and project manager that simplifies dependency management, environment creation, and running commands.

For more information about uv, visit the [official documentation](https://docs.astral.sh/uv/).

### Prerequisites
[uv](https://docs.astral.sh/uv/) - Python package and project manager
- Install with curl (macOS/Linux): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Install with PowerShell (Windows): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Or install with pip: `pip install uv`
- Or with Homebrew (macOS): `brew install uv`

### Setup python environment
`uv` automatically creates and manages virtual environments:

```bash
# Create a virtual environment
uv venv --python 3.12
source .venv/bin/activate # On Windows: .venv\Scripts\activate
```

### Install dependencies
```bash
uv sync
```

### Helper Scripts
*Make sure you have created a virtual environment via `uv venv --python 3.12`*
- Run linting - `uv run lint`
- Format code - `uv run format`
- Run tests - `uv run test`
- Run the application - `uv run serve`


