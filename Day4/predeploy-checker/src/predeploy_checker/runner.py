"""Pre-deployment validation runner and orchestrator."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import tomllib
from typing import Any, Callable

from predeploy_checker.exceptions import PreDeployError
from predeploy_checker.validators import (
    check_database,
    check_redis,
    run_custom_check,
    run_test_suite,
    validate_dependencies,
    validate_env,
)


def load_env_file(filepath: str | Path) -> dict[str, str]:
    """Parse a .env file and export variables to os.environ.

    Args:
        filepath: Path to the .env file.

    Returns:
        Dict of parsed environment variables.
    """
    path = Path(filepath)
    loaded: dict[str, str] = {}
    if not path.is_file():
        return loaded

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("export "):
                stripped = stripped[7:].strip()
            if "=" in stripped:
                key, val = stripped.split("=", 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                loaded[key] = val
                os.environ[key] = val
    return loaded


class PreDeployRunner:
    """Orchestrates configurable pre-deployment validation checks."""

    def __init__(
        self,
        required_env_vars: list[str] | None = None,
        env_file: str | None = None,
        check_database: bool = False,
        database_url: str | None = None,
        database_url_env: str | None = "DATABASE_URL",
        check_redis: bool = False,
        redis_url: str | None = None,
        redis_url_env: str | None = "REDIS_URL",
        required_commands: list[str] | None = None,
        required_packages: list[str] | None = None,
        run_tests: bool = False,
        test_command: list[str] | str | None = None,
        custom_checks: list[str | Callable[..., Any]] | None = None,
        verbose: bool = True,
    ) -> None:
        self.required_env_vars = list(required_env_vars or [])
        self.env_file = env_file
        self.check_database_enabled = check_database
        self.database_url = database_url
        self.database_url_env = database_url_env
        self.check_redis_enabled = check_redis
        self.redis_url = redis_url
        self.redis_url_env = redis_url_env
        self.required_commands = list(required_commands or [])
        self.required_packages = list(required_packages or [])
        self.run_tests_enabled = run_tests
        self.test_command = test_command
        self.custom_checks = list(custom_checks or [])
        self.verbose = verbose

    def log(self, message: str) -> None:
        """Print log message if verbose mode is enabled."""
        if self.verbose:
            print(message)

    @classmethod
    def from_pyproject(cls, pyproject_path: str | Path = "pyproject.toml") -> PreDeployRunner:
        """Load runner configuration from pyproject.toml."""
        path = Path(pyproject_path)
        if not path.is_file():
            return cls()

        with open(path, "rb") as f:
            data = tomllib.load(f)

        tool_config = (
            data.get("tool", {}).get("predeploy_checker")
            or data.get("tool", {}).get("predeploy-checker")
            or {}
        )

        return cls(
            required_env_vars=tool_config.get("required_env_vars"),
            env_file=tool_config.get("env_file"),
            check_database=tool_config.get("check_database", False),
            database_url=tool_config.get("database_url"),
            database_url_env=tool_config.get("database_url_env", "DATABASE_URL"),
            check_redis=tool_config.get("check_redis", False),
            redis_url=tool_config.get("redis_url"),
            redis_url_env=tool_config.get("redis_url_env", "REDIS_URL"),
            required_commands=tool_config.get("required_commands"),
            required_packages=tool_config.get("required_packages"),
            run_tests=tool_config.get("run_tests", False),
            test_command=tool_config.get("test_command"),
            custom_checks=tool_config.get("custom_checks"),
        )

    def run(self) -> bool:
        """Execute all configured pre-deployment validations.

        Returns:
            True if all checks succeed.

        Raises:
            PreDeployError: If any check fails.
        """
        self.log("================ Pre-Deployment Checks ================")

        # 1. Load .env if specified or automatically found in working directory
        env_to_load = self.env_file
        if env_to_load is None and Path(".env").is_file():
            env_to_load = ".env"

        if env_to_load and Path(env_to_load).is_file():
            load_env_file(env_to_load)
            self.log(f"[OK] Loaded environment file: {env_to_load}")

        # 2. Validate environment variables
        if self.required_env_vars:
            validate_env(self.required_env_vars)

        # 3. Validate dependencies / binaries
        if self.required_commands or self.required_packages:
            validate_dependencies(
                commands=self.required_commands,
                packages=self.required_packages,
            )
            self.log("[OK] Dependencies and required binaries verified")

        # 4. Check database connectivity
        if self.check_database_enabled:
            db_url = self.database_url
            if not db_url and self.database_url_env:
                db_url = os.environ.get(self.database_url_env)
            check_database(url=db_url)
            self.log("[OK] Database connectivity verified")

        # 5. Check Redis connectivity
        if self.check_redis_enabled:
            redis_url = self.redis_url
            if not redis_url and self.redis_url_env:
                redis_url = os.environ.get(self.redis_url_env)
            check_redis(url=redis_url)
            self.log("[OK] Redis connectivity verified")

        # 6. Execute custom checks
        if self.custom_checks:
            for check in self.custom_checks:
                check_name = check if isinstance(check, str) else getattr(check, "__name__", str(check))
                run_custom_check(check)
                self.log(f"[OK] Custom check passed: {check_name}")

        # 7. Execute test suite
        if self.run_tests_enabled:
            self.log("Running pre-deployment test suite...")
            run_test_suite(test_command=self.test_command)
            self.log("[OK] Test suite passed")

        self.log("=======================================================")
        self.log("Pre-deployment checks passed! Application ready to start.")
        self.log("=======================================================")
        return True

