# Predeploy Checker

A lightweight and reusable pre-deployment validation runner for Python applications. It validates environment variables, dependency availability, database connectivity, cache reachability, and test suite execution prior to service startup.

## Features

- **Environment Validation**: Verify required environment variables are present and populated.
- **Dependency Checks**: Ensure critical binaries and Python libraries are available on the system.
- **Database Readiness**: Check connectivity for synchronous and asynchronous SQLAlchemy database URLs.
- **Redis Connectivity**: Ping Redis instances before bootstrapping the service.
- **Custom Extensibility**: Run arbitrary custom validation hooks.
- **Test Gate**: Optionally execute `pytest` suites before proceeding.

## Installation

Install using pip:

```bash
pip install predeploy-checker
```

Or using uv:

```bash
uv add predeploy-checker
```

## CLI Usage

### Running the Command

- **If your virtual environment is activated** (`.venv\Scripts\activate` on Windows or `source .venv/bin/activate` on Linux/macOS):
  Typing `predeploy-check` directly works immediately:
  ```bash
  predeploy-check
  ```

- **If your virtual environment is NOT activated**:
  Windows won't find the command on your system `PATH`. In that case, use either:
  ```powershell
  .venv\Scripts\predeploy-check.exe
  # OR
  uv run --no-sync predeploy-check
  ```

### Default Execution

Run default checks using settings discovered in `pyproject.toml` (and auto-loading `.env` if present):

```bash
predeploy-check
```

Pass manual flags:

```bash
predeploy-check --require-env APP_SECRET --require-env DATABASE_URL --check-db --run-tests
```

### Options

- `-c, --config`: Path to `pyproject.toml` configuration (default: `pyproject.toml`).
- `--env-file`: Load environment variables from a `.env` file before executing checks.
- `--require-env`: Specify required environment variable names.
- `--check-db`: Validate database connectivity.
- `--skip-db`: Explicitly bypass database verification even if configured in `pyproject.toml`.
- `--db-url`: Explicit database connection URL.
- `--check-redis`: Validate Redis connectivity.
- `--skip-redis`: Explicitly bypass Redis verification even if configured in `pyproject.toml`.
- `--redis-url`: Explicit Redis connection URL.
- `--require-cmd`: Required CLI executable command.
- `--require-pkg`: Required Python package.
- `--run-tests`: Run the test suite gate.
- `--skip-tests`: Explicitly skip test suite execution even if configured in `pyproject.toml`.
- `--test-cmd`: Custom test execution command (default: `python -m pytest`).
- `--custom-check`: Target Python callable (`module:function`) to run.
- `-q, --quiet`: Suppress informational progress logs.
- `--version`: Show package version number.

## Configuration via `pyproject.toml`

Add a `[tool.predeploy_checker]` section to your project's `pyproject.toml`:

```toml
[tool.predeploy_checker]
required_env_vars = ["APP_ENV", "DATABASE_URL", "REDIS_URL"]
check_database = true
database_url_env = "DATABASE_URL"
check_redis = true
redis_url_env = "REDIS_URL"
run_tests = true
```

## Python API Usage

```python
from predeploy_checker import PreDeployRunner

runner = PreDeployRunner(
    required_env_vars=["DATABASE_URL"],
    check_database=True,
    run_tests=False,
)
runner.run()
```

## Development and Testing

Clone the repository and install dev dependencies:

```bash
cd predeploy-checker
uv sync
```

Run test suite:

```bash
uv run pytest
```

## Building the Package

Build both source distribution (`.tar.gz`) and wheel (`.whl`):

```bash
uv build
```

Or using the standard build module:

```bash
python -m build
```

## Publishing to PyPI

Verify package metadata with twine:

```bash
uvx twine check dist/*
```

Publish using `uv publish` (reads `UV_PUBLISH_TOKEN` from the environment):

```bash
uv publish
```

Or provide the token explicitly:

```bash
uv publish --token <YOUR_PYPI_TOKEN> dist/*
```

Or upload using `twine`:

```bash
uvx twine upload dist/*
```

## Versioning Policy

This project strictly adheres to [Semantic Versioning (SemVer 2.0.0)](https://semver.org/).
- `1.0.0` – Initial stable release with full pre-deployment validation suite.
- Minor bumps (`1.1.0`) introduce new backwards-compatible features.
- Patch releases (`1.0.1`) deliver bug fixes and optimizations.
