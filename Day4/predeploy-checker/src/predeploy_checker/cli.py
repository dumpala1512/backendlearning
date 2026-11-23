"""Command-line interface for predeploy-checker."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from predeploy_checker.exceptions import PreDeployError
from predeploy_checker.runner import PreDeployRunner

__version__ = "1.0.0"


def build_parser() -> argparse.ArgumentParser:
    """Construct argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="predeploy-check",
        description="Generic pre-deployment validation runner for Python applications.",
    )
    parser.add_argument(
        "-c",
        "--config",
        default="pyproject.toml",
        help="Path to pyproject.toml containing [tool.predeploy_checker] configuration.",
    )
    parser.add_argument(
        "--env-file",
        help="Path to .env file to load before checks.",
    )
    parser.add_argument(
        "--require-env",
        action="append",
        dest="required_env_vars",
        help="Environment variable required to be present and non-empty (can be specified multiple times).",
    )
    parser.add_argument(
        "--check-db",
        action="store_true",
        default=None,
        help="Enable database connectivity verification.",
    )
    parser.add_argument(
        "--skip-db",
        action="store_true",
        help="Explicitly skip database verification even if configured in pyproject.toml.",
    )
    parser.add_argument(
        "--db-url",
        help="Database URL to verify (overrides DATABASE_URL env vars).",
    )
    parser.add_argument(
        "--check-redis",
        action="store_true",
        default=None,
        help="Enable Redis connectivity verification.",
    )
    parser.add_argument(
        "--skip-redis",
        action="store_true",
        help="Explicitly skip Redis verification even if configured in pyproject.toml.",
    )
    parser.add_argument(
        "--redis-url",
        help="Redis URL to verify (overrides REDIS_URL env var).",
    )
    parser.add_argument(
        "--require-cmd",
        action="append",
        dest="required_commands",
        help="Required CLI executable command (can be specified multiple times).",
    )
    parser.add_argument(
        "--require-pkg",
        action="append",
        dest="required_packages",
        help="Required Python package (can be specified multiple times).",
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        default=None,
        help="Execute test suite as part of the pre-deployment gate.",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Explicitly skip test suite execution even if configured in pyproject.toml.",
    )
    parser.add_argument(
        "--test-cmd",
        help="Custom command used to run tests (defaults to 'python -m pytest').",
    )
    parser.add_argument(
        "--custom-check",
        action="append",
        dest="custom_checks",
        help="Custom check import target ('module:func') to execute.",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress informational progress logs.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    # 1. Base configuration from pyproject.toml if present
    config_path = Path(args.config)
    if config_path.is_file():
        runner = PreDeployRunner.from_pyproject(config_path)
    else:
        runner = PreDeployRunner()

    # 2. Overlay CLI arguments
    if args.env_file is not None:
        runner.env_file = args.env_file
    if args.required_env_vars:
        runner.required_env_vars.extend(args.required_env_vars)
    if args.skip_db:
        runner.check_database_enabled = False
    elif args.check_db is not None:
        runner.check_database_enabled = args.check_db
    if args.db_url is not None:
        runner.database_url = args.db_url
        runner.check_database_enabled = True
    if args.skip_redis:
        runner.check_redis_enabled = False
    elif args.check_redis is not None:
        runner.check_redis_enabled = args.check_redis
    if args.redis_url is not None:
        runner.redis_url = args.redis_url
        runner.check_redis_enabled = True
    if args.required_commands:
        runner.required_commands.extend(args.required_commands)
    if args.required_packages:
        runner.required_packages.extend(args.required_packages)
    if args.skip_tests:
        runner.run_tests_enabled = False
    elif args.run_tests is not None:
        runner.run_tests_enabled = args.run_tests
    if args.test_cmd is not None:
        runner.test_command = args.test_cmd
    if args.custom_checks:
        runner.custom_checks.extend(args.custom_checks)
    if args.quiet:
        runner.verbose = False

    # 3. Execute runner
    try:
        runner.run()
        return 0
    except PreDeployError as exc:
        sys.stderr.write(f"\n[PreDeploy FAILED] {exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"\n[PreDeploy UNEXPECTED ERROR] {exc}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())

