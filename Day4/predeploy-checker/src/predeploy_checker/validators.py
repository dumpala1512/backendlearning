"""Reusable pre-deployment validation logic."""

from __future__ import annotations

import asyncio
import importlib
import inspect
import os
import shutil
import subprocess
import sys
from typing import Any, Callable, Mapping

from predeploy_checker.exceptions import (
    CustomCheckError,
    DatabaseConnectionError,
    DependencyValidationError,
    EnvValidationError,
    RedisConnectionError,
    TestExecutionError,
)


def validate_env(
    required_vars: list[str],
    env: Mapping[str, str] | None = None,
) -> list[str]:
    """Validate that all required environment variables are present and non-empty.

    Args:
        required_vars: List of variable names that must exist.
        env: Mapping to check against. Defaults to os.environ.

    Returns:
        List of checked variable names.

    Raises:
        EnvValidationError: If one or more variables are missing or empty.
    """
    if env is None:
        env = os.environ

    missing = [var for var in required_vars if not env.get(var)]
    if missing:
        raise EnvValidationError(missing)
    return required_vars


def validate_dependencies(
    commands: list[str] | None = None,
    packages: list[str] | None = None,
) -> None:
    """Validate that required CLI tools and Python packages are available.

    Args:
        commands: Executables that must exist in system PATH.
        packages: Python importable module names that must be present.

    Raises:
        DependencyValidationError: If any executable or package cannot be found.
    """
    missing_commands = []
    if commands:
        for cmd in commands:
            if shutil.which(cmd) is None:
                missing_commands.append(cmd)

    missing_packages = []
    if packages:
        for pkg in packages:
            try:
                importlib.import_module(pkg)
            except ImportError:
                missing_packages.append(pkg)

    errors: list[str] = []
    if missing_commands:
        errors.append(f"Missing required CLI commands: {', '.join(missing_commands)}")
    if missing_packages:
        errors.append(f"Missing required Python packages: {', '.join(missing_packages)}")

    if errors:
        raise DependencyValidationError("; ".join(errors))


def check_database(
    url: str | None = None,
    timeout: float = 5.0,
) -> bool:
    """Verify database reachability and readiness.

    Supports synchronous and asynchronous SQLAlchemy URLs.

    Args:
        url: Database connection URL. Defaults to DATABASE_URL or DB_URL environment variable.
        timeout: Timeout in seconds for establishing connection.

    Returns:
        True if the database is reachable.

    Raises:
        DatabaseConnectionError: If connection cannot be established or query fails.
    """
    target_url = url or os.environ.get("DATABASE_URL")
    if not target_url:
        raise DatabaseConnectionError("DATABASE_URL is not set.")

    try:
        from sqlalchemy import text
    except ImportError as exc:
        raise DatabaseConnectionError(
            "SQLAlchemy is required for database verification. Install sqlalchemy to enable this check."
        ) from exc

    is_async = "+asyncpg" in target_url or "+aiosqlite" in target_url or "+asyncmy" in target_url

    try:
        if is_async:
            from sqlalchemy.ext.asyncio import create_async_engine

            async def _check_async() -> None:
                engine = create_async_engine(target_url, connect_args={"timeout": timeout} if "+asyncpg" in target_url else {})
                try:
                    async with engine.connect() as conn:
                        await conn.execute(text("SELECT 1"))
                finally:
                    await engine.dispose()

            asyncio.run(_check_async())
        else:
            from sqlalchemy import create_engine

            engine = create_engine(target_url)
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            finally:
                engine.dispose()
        return True
    except Exception as exc:
        raise DatabaseConnectionError(f"Database connection verification failed: {exc}") from exc


def check_redis(
    url: str | None = None,
    timeout: float = 5.0,
) -> bool:
    """Verify Redis reachability via PING.

    Args:
        url: Redis connection URL. Defaults to REDIS_URL environment variable or redis://localhost:6379.
        timeout: Socket timeout in seconds.

    Returns:
        True if Redis responds to PING.

    Raises:
        RedisConnectionError: If connection fails or PING does not respond.
    """
    target_url = url or os.environ.get("REDIS_URL") or "redis://localhost:6379"

    try:
        import redis
    except ImportError as exc:
        raise RedisConnectionError(
            "Redis library is required for redis verification. Install redis to enable this check."
        ) from exc

    try:
        # Check if async client is preferred or sync
        if hasattr(redis, "from_url"):
            client = redis.from_url(target_url, socket_timeout=timeout)
            # If client.ping is a coroutine (redis.asyncio)
            if inspect.iscoroutinefunction(client.ping):
                async def _ping():
                    await client.ping()
                    if hasattr(client, "aclose"):
                        await client.aclose()
                    elif hasattr(client, "close"):
                        client.close()
                asyncio.run(_ping())
            else:
                client.ping()
                client.close()
        return True
    except Exception as exc:
        raise RedisConnectionError(f"Redis connection verification failed: {exc}") from exc


def run_test_suite(
    test_command: list[str] | str | None = None,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
) -> bool:
    """Execute the project's test suite as a pre-deployment gate.

    Args:
        test_command: Command to execute. Defaults to [sys.executable, "-m", "pytest"].
        cwd: Directory where the command is executed.
        env: Optional environment variables.

    Returns:
        True if the test suite exited with code 0.

    Raises:
        TestExecutionError: If tests fail or the runner executable is not found.
    """
    if test_command is None:
        cmd = [sys.executable, "-m", "pytest"]
    elif isinstance(test_command, str):
        cmd = test_command.split()
    else:
        cmd = list(test_command)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env=dict(env) if env is not None else None,
            check=False,
        )
        if result.returncode != 0:
            raise TestExecutionError(f"Test suite failed with exit code {result.returncode}")
        return True
    except FileNotFoundError as exc:
        raise TestExecutionError(f"Test runner executable not found: {exc}") from exc
    except Exception as exc:
        if isinstance(exc, TestExecutionError):
            raise
        raise TestExecutionError(f"Test execution encountered an error: {exc}") from exc


def run_custom_check(target: str | Callable[..., Any]) -> Any:
    """Execute a custom validation check.

    Target can be a callable or an import string (e.g. 'pkg.module:func' or 'pkg.module.func').
    Supports both synchronous and asynchronous functions.

    Args:
        target: Callable or import string.

    Returns:
        Result of the custom check.

    Raises:
        CustomCheckError: If importing or executing the check fails.
    """
    func: Callable[..., Any]
    if isinstance(target, str):
        try:
            if ":" in target:
                mod_name, func_name = target.split(":", 1)
            else:
                mod_name, func_name = target.rsplit(".", 1)
            mod = importlib.import_module(mod_name)
            func = getattr(mod, func_name)
        except Exception as exc:
            raise CustomCheckError(f"Failed to load custom check '{target}': {exc}") from exc
    elif callable(target):
        func = target
    else:
        raise CustomCheckError(f"Custom check must be a callable or string reference, got {type(target)}")

    try:
        if inspect.iscoroutinefunction(func):
            return asyncio.run(func())
        return func()
    except Exception as exc:
        raise CustomCheckError(f"Custom check '{getattr(func, '__name__', str(target))}' failed: {exc}") from exc

