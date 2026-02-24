# Developer Setup

This guide explains how to run `terragenai` locally for development.

## Prerequisites

- Python 3.11+ (3.14 also works)
- Git

## 1) Clone and enter the repo

```bash
git clone https://github.com/eshika289/terragenAI.git
cd terragenAI
```

## 2) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 3) Install project + dev dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## 4) Run tests

```bash
python -m pytest -q
python -m pytest -q --cov=src --cov-report=term-missing --cov-fail-under=80
```

## 5) Run the CLI locally

```bash
python -m src.main --version
python -m src.main --configure
python -m src.main
```

## 6) Run linter and autoformater
```bash
python -m black .
python -m ruff check . --fix   
```

Optional environment variables:

- `TERRAGENAI_CONFIG_FILE` (override config file location)
- `TERRAGENAI_HISTORY_FILE` (override chat history file location)
- `TERRAGENAI_HOME` (override app config/state base directory)

## Branch and PR flow

- Create work from `feature/*`
- Open PR into `develop`
- After approval and passing checks, merge to `develop`
- Merge `develop` into `main`
- On `main`, release tagging is automated and PyPI publish runs from version tags
