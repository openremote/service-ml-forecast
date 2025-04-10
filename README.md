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
`uv venv` automatically creates a virtual environment with the python version specified in the `pyproject.toml` file.

```bash
# Create a virtual environment
uv venv
source .venv/bin/activate # On Windows: .venv\Scripts\activate
```

### Install dependencies
```bash
uv sync
```

### Helper Scripts
*Make sure you have created a virtual environment via `uv venv`*
- Run linting - `uv run lint`
- Format code - `uv run format`
- Run tests - `uv run test`
- Run the application - `uv run start`


## License

The OpenRemote Machine Learning Forecast Service is distributed under [AGPL-3.0-or-later](LICENSE.txt).

```
Copyright 2025, OpenRemote Inc.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
```

