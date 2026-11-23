"""Shared exceptions for predeploy-checker."""

class PreDeployError(Exception):
    """Base exception for all pre-deployment validation errors."""
    pass


class EnvValidationError(PreDeployError):
    """Raised when one or more required environment variables are missing or invalid."""
    def __init__(self, missing_vars: list[str], message: str | None = None):
        self.missing_vars = missing_vars
        msg = message or f"Missing required environment variables: {', '.join(missing_vars)}"
        super().__init__(msg)


class DatabaseConnectionError(PreDeployError):
    """Raised when database connectivity validation fails."""
    pass


class RedisConnectionError(PreDeployError):
    """Raised when Redis connectivity validation fails."""
    pass


class DependencyValidationError(PreDeployError):
    """Raised when required executables, tools, or dependencies are missing."""
    pass


class TestExecutionError(PreDeployError):
    """Raised when the pre-deployment test suite fails."""
    __test__ = False



class CustomCheckError(PreDeployError):
    """Raised when a user-defined custom validation check fails."""
    pass
