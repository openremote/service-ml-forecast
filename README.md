# service-ml-forecast
Machine Learning Forecast Service

## Installation
GNU Make is used for project management purposes. It simplifies the process of running the commands like building, testing, linting, formatting, etc. and ensures consistency across different operating systems.

### Prerequisites
- Python 3.10+ [Download](https://www.python.org/downloads/)
    - Or use a package manager like `brew` or `apt`
    - [Pyenv](https://github.com/pyenv/pyenv) is also recommended for managing multiple versions of Python
- GNU Make
    - [Windows](https://gnuwin32.sourceforge.net/packages/make.htm)
    - [MacOS](https://formulae.brew.sh/formula/make)
    - Linux:
        - Ubuntu/Debian: `sudo apt install make`
        - Fedora: `sudo dnf install make`
        - Arch Linux: `sudo pacman -S make`
        - Other: Depends on your package manager/distribution

### Setup python environment
```bash
python -m venv .venv
source .venv/bin/activate # On Windows: .venv\Scripts\activate
```

### Make Commands

- List all available commands - `make help`

- Install all dependencies - `make install`

- Run all tests - `make test`

- Run linting - `make lint`

- Format code - `make format`

- Clean dependencies and build artifacts - `make clean`

- Run the application - `make run`

