"""
Custom exceptions for Kubernetes operations.
"""


class KubernetesError(Exception):
    """Base exception for Kubernetes operations."""


class KubectlNotFoundError(KubernetesError):
    """Raised when kubectl is not installed or not available."""


class KubectlTimeoutError(KubernetesError):
    """Raised when a kubectl command exceeds the configured timeout."""


class CommandExecutionError(KubernetesError):
    """Raised when kubectl returns a non-zero exit code."""

    def __init__(
        self,
        message: str,
        command: str,
        stderr: str,
        return_code: int,
    ) -> None:
        super().__init__(message)
        self.command = command
        self.stderr = stderr
        self.return_code = return_code


class KubectlOutputParseError(KubernetesError):
    """Raised when kubectl returns output that cannot be parsed."""

    def __init__(
        self,
        message: str,
        command: str,
    ) -> None:
        super().__init__(message)
        self.command = command


class InvalidKubectlArgumentError(KubernetesError):
    """Raised when an invalid kubectl argument is detected."""


class ClusterConnectionError(KubernetesError):
    """Raised when the cluster cannot be reached."""
