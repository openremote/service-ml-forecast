# service-ml-forecast
[![Lint and Test](https://github.com/openremote/service-ml-forecast/actions/workflows/ci.yml/badge.svg)](https://github.com/openremote/service-ml-forecast/actions/workflows/ci.yml?query=branch%3Amain)
[![Open Source? Yes!](https://badgen.net/badge/Open%20Source%20%3F/Yes%21/blue?icon=github)](https://github.com/Naereen/badges/)

## Installation
GNU Make is used for project management purposes. It simplifies the process of running the commands like building, testing, linting, formatting, etc. and ensures consistency across different operating systems.

### Prerequisites
- Python 3.10+ [Download](https://www.python.org/downloads/)
    - Or use a package manager:
        - Ubuntu/Debian: `sudo apt install python3 python3-pip python3-venv`
        - Fedora: `sudo dnf install python3 python3-pip python3-virtualenv`
        - Arch Linux: `sudo pacman -S python python-pip python-virtualenv`
        - macOS: `brew install python`
    - [Pyenv](https://github.com/pyenv/pyenv) is also recommended for managing multiple versions of Python
- GNU Make
    - [Windows](https://gnuwin32.sourceforge.net/packages/make.htm)
    - macOS: `brew install make`
    - Linux:
        - Ubuntu/Debian: `sudo apt install make`
        - Fedora: `sudo dnf install make`
        - Arch Linux: `sudo pacman -S make`
        - Other: Depends on your package manager/distribution

### Setup python environment
```bash
python -m venv .venv # On Ubuntu/Debian: python3
source .venv/bin/activate # On Windows: .venv\Scripts\activate
```

### Make Commands

- List all available commands - `make help`

- Install dependencies - `make install`

- Run all tests - `make test`

- Run linting - `make lint`

- Format code - `make format`

- Clean virtual environment - `make clean`

- Clean virtual environment and install dependencies - `make clean-install`

- Run the application - `make run`

