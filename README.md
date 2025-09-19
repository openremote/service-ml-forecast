# service-ml-forecast
[![Lint and Test](https://github.com/openremote/service-ml-forecast/actions/workflows/ci.yml/badge.svg)](https://github.com/openremote/service-ml-forecast/actions/workflows/ci.yml?query=branch%3Amain)
[![Open Source? Yes!](https://badgen.net/badge/Open%20Source%20%3F/Yes%21/blue?icon=github)](https://github.com/Naereen/badges/)

## Installation
Follow the steps below to run the project.

### Prerequisites
[uv](https://docs.astral.sh/uv/) - Python package and project manager
- Install with curl (macOS/Linux): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Install with PowerShell (Windows): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Or install with pip: `pip install uv`
- Or with Homebrew (macOS): `brew install uv`

[node](https://nodejs.org/en/download/) - JavaScript runtime + npm (node package manager)
- Install with Homebrew (macOS): `brew install node`
- Install directly (Windows): https://nodejs.org/en/download/
- Install via apt (Linux): `sudo apt install nodejs npm`
- Install via dnf (Linux): `sudo dnf install nodejs npm`
- Install via pacman (Linux): `sudo pacman -S nodejs npm`

***

### Run the back-end (Python)

Create a virtual environment
```bash
# In project root
uv venv
source .venv/bin/activate # On Windows: .venv\Scripts\activate

uv sync
```

Set the required environment variables -- See [config.py](https://github.com/openremote/service-ml-forecast/blob/main/src/service_ml_forecast/config.py) for all configuration options.
```bash
ML_OR_SERVICE_USER=serviceuser
ML_OR_SERVICE_SECRET=secret
```

Start the back-end application
```bash
uv run start

# Exposes the back-end on http://localhost:8000
```

***

### Run the front-end (JavaScript)
Serve the front-end
```bash
cd frontend
npm run serve  # Automatically installs dependencies

# Exposes the front-end on http://localhost:8001
```

***

### UV Helper Scripts
In project root
- Run linting - `uv run lint`
- Format code - `uv run format`
- Run tests - `uv run test`
- Run the application - `uv run start`

### NPM Helper Scripts
in `/frontend`
- Run linting - `npm run lint`
- Format code - `npm run format`
- Run the application - `npm run serve`

## License

The OpenRemote ML Forecast Service is distributed under [AGPL-3.0-or-later](LICENSE.txt).

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

