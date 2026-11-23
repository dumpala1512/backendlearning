import os
import sys
import pytest
from unittest.mock import MagicMock, patch

from predeploy_checker.exceptions import (
    CustomCheckError,
    DatabaseConnectionError,
    DependencyValidationError,
    EnvValidationError,
    PreDeployError,
    RedisConnectionError,
    TestExecutionError,
)
from predeploy_checker.validators import (
    check_database,
    check_redis,
    run_custom_check,
    run_test_suite,
    validate_dependencies,
    validate_env,
)
from predeploy_checker.runner import PreDeployRunner, load_env_file
from predeploy_checker.cli import main


def test_validate_env_success():
    env = {"KEY_A": "val_a", "KEY_B": "val_b"}
    res = validate_env(["KEY_A", "KEY_B"], env=env)
    assert res == ["KEY_A", "KEY_B"]


def test_validate_env_failure():
    env = {"KEY_A": "val_a"}
    with pytest.raises(EnvValidationError) as exc_info:
        validate_env(["KEY_A", "MISSING_VAR"], env=env)
    assert "MISSING_VAR" in str(exc_info.value)


def test_validate_dependencies_success():
    validate_dependencies(commands=[sys.executable], packages=["sys", "os"])


def test_validate_dependencies_failure():
    with pytest.raises(DependencyValidationError):
        validate_dependencies(commands=["non_existent_binary_xyz_123"])

    with pytest.raises(DependencyValidationError):
        validate_dependencies(packages=["non_existent_python_package_xyz_123"])


def test_check_database_missing_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DB_URL", raising=False)
    with pytest.raises(DatabaseConnectionError):
        check_database(url=None)


def test_check_database_sqlite_memory():
    # SQLite memory connection
    result = check_database("sqlite:///:memory:")
    assert result is True


def test_check_redis_failure():
    with pytest.raises(RedisConnectionError):
        # Using an invalid port that won't respond
        check_redis("redis://127.0.0.1:1/0", timeout=0.1)


def test_run_test_suite_success():
    # python -c "exit(0)" should pass
    result = run_test_suite(test_command=[sys.executable, "-c", "exit(0)"])
    assert result is True


def test_run_test_suite_failure():
    with pytest.raises(TestExecutionError):
        run_test_suite(test_command=[sys.executable, "-c", "exit(1)"])


def test_run_custom_check_callable():
    def custom_ok():
        return 42

    def custom_fail():
        raise RuntimeError("Something broke")

    assert run_custom_check(custom_ok) == 42
    with pytest.raises(CustomCheckError):
        run_custom_check(custom_fail)


def test_runner_full_run_success(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_PORT", "8000")
    runner = PreDeployRunner(
        required_env_vars=["APP_PORT"],
        check_database=True,
        database_url="sqlite:///:memory:",
        run_tests=True,
        test_command=[sys.executable, "-c", "exit(0)"],
        verbose=False,
    )
    assert runner.run() is True


def test_runner_from_pyproject(tmp_path):
    pyproject_file = tmp_path / "pyproject.toml"
    pyproject_file.write_text(
        """
[tool.predeploy_checker]
required_env_vars = ["SAMPLE_FLAG"]
check_database = false
run_tests = false
""",
        encoding="utf-8",
    )
    runner = PreDeployRunner.from_pyproject(pyproject_file)
    assert runner.required_env_vars == ["SAMPLE_FLAG"]
    assert runner.check_database_enabled is False


def test_cli_execution_success(monkeypatch, tmp_path):
    monkeypatch.setenv("CLI_VAR", "present")
    empty_conf = tmp_path / "empty.toml"
    empty_conf.write_text("", encoding="utf-8")
    exit_code = main(["-c", str(empty_conf), "--require-env", "CLI_VAR", "--quiet"])
    assert exit_code == 0


def test_cli_execution_failure(tmp_path):
    empty_conf = tmp_path / "empty.toml"
    empty_conf.write_text("", encoding="utf-8")
    exit_code = main(["-c", str(empty_conf), "--require-env", "DEFINITELY_NOT_SET_VAR_999", "--quiet"])
    assert exit_code == 1

