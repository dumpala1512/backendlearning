"""Predeploy-checker: A reusable pre-deployment validation gate for Python projects."""

from predeploy_checker.cli import main
from predeploy_checker.exceptions import (
    CustomCheckError,
    DatabaseConnectionError,
    DependencyValidationError,
    EnvValidationError,
    PreDeployError,
    RedisConnectionError,
    TestExecutionError,
)
from predeploy_checker.runner import PreDeployRunner, load_env_file
from predeploy_checker.validators import (
    check_database,
    check_redis,
    run_custom_check,
    run_test_suite,
    validate_dependencies,
    validate_env,
)

__version__ = "1.0.0"

__all__ = [
    "CustomCheckError",
    "DatabaseConnectionError",
    "DependencyValidationError",
    "EnvValidationError",
    "PreDeployError",
    "PreDeployRunner",
    "RedisConnectionError",
    "TestExecutionError",
    "check_database",
    "check_redis",
    "load_env_file",
    "main",
    "run_custom_check",
    "run_test_suite",
    "validate_dependencies",
    "validate_env",
]

