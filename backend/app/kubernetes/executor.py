"""
Secure kubectl execution engine.

All kubectl commands must pass through this class.
"""

from __future__ import annotations

import subprocess
import time

from app.core.logging import app_logger
from app.kubernetes.constants import (
    DEFAULT_TIMEOUT_SECONDS,
    KUBECTL_BINARY,
    SUCCESS_EXIT_CODE,
)
from app.kubernetes.exceptions import (
    CommandExecutionError,
    KubectlNotFoundError,
    KubectlTimeoutError,
)
from app.kubernetes.models import CommandResult


class KubectlExecutor:
    """Executes kubectl commands securely."""

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.timeout = timeout

    def execute(
        self,
        args: list[str],
        stdin: str | None = None,
        timeout: int | None = None,
    ) -> CommandResult:
        command = [KUBECTL_BINARY, *args]

        effective_timeout = timeout or self.timeout
        start = time.perf_counter()

        # Do not log stdin because it can contain Kubernetes Secrets.
        app_logger.info(
            "Executing command: {}",
            " ".join(command),
        )

        try:
            result = subprocess.run(
            command,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=effective_timeout,
            check=False,
            shell=False,
        )
        except FileNotFoundError as exc:
            raise KubectlNotFoundError(
                "kubectl executable was not found."
            ) from exc

        except subprocess.TimeoutExpired as exc:
            raise KubectlTimeoutError(
                f"Command timed out after {effective_timeout} seconds."
            ) from exc

        duration = round(
            (time.perf_counter() - start) * 1000,
            2,
        )

        response = CommandResult(
    command=" ".join(command),
    stdout=result.stdout or "",
    stderr=result.stderr or "",
    return_code=result.returncode,
    duration_ms=duration,
)

        app_logger.info(
            "Completed in {} ms (exit={})",
            duration,
            result.returncode,
        )

        if result.returncode != SUCCESS_EXIT_CODE:
            raise CommandExecutionError(


                
                message="kubectl command failed.",
                command=response.command,
                stderr=response.stderr,
                return_code=response.return_code,
            )

        return response