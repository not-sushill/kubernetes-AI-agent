from __future__ import annotations

import subprocess
from types import SimpleNamespace
from typing import Any

import pytest

from app.kubernetes.client import KubectlClient
from app.kubernetes.exceptions import (
    CommandExecutionError,
    InvalidKubectlArgumentError,
    KubectlTimeoutError,
)
from app.kubernetes.executor import KubectlExecutor
from app.kubernetes.models import CommandResult


def test_executor_returns_command_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_run(
        command: list[str],
        *,
        input: str | None = None,
        capture_output: bool,
        text: bool,
        encoding: str | None = None,
        errors: str | None = None,
        timeout: int,
        check: bool,
        shell: bool = False,
    ) -> SimpleNamespace:
        calls.append(
            {
                "command": command,
                "input": input,
                "capture_output": capture_output,
                "text": text,
                "encoding": encoding,
                "errors": errors,
                "timeout": timeout,
                "check": check,
                "shell": shell,
            }
        )

        return SimpleNamespace(
            stdout="ok",
            stderr="",
            returncode=0,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = KubectlExecutor(timeout=5).execute(["get", "pods", "-A"])

    assert calls == [
        {
            "command": ["kubectl", "get", "pods", "-A"],
            "input": None,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": 5,
            "check": False,
            "shell": False,
        }
    ]
    assert result.stdout == "ok"
    assert result.return_code == 0
    assert result.command == "kubectl get pods -A"


def test_executor_raises_for_failed_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(*args: Any, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(
            stdout="",
            stderr="forbidden",
            returncode=1,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(CommandExecutionError) as exc_info:
        KubectlExecutor().execute(["get", "pods"])

    assert exc_info.value.stderr == "forbidden"
    assert exc_info.value.return_code == 1


def test_executor_raises_for_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(
        command: list[str],
        **kwargs: Any,
    ) -> SimpleNamespace:
        raise subprocess.TimeoutExpired(
            cmd=command,
            timeout=kwargs["timeout"],
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(KubectlTimeoutError):
        KubectlExecutor(timeout=1).execute(["get", "pods"])


class FakeExecutor:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def execute(self, args: list[str]) -> CommandResult:
        self.commands.append(args)
        return CommandResult(
            command="kubectl " + " ".join(args),
            stdout="{}",
            stderr="",
            return_code=0,
            duration_ms=1.0,
        )


def test_client_builds_pod_logs_command() -> None:
    executor = FakeExecutor()
    client = KubectlClient(executor=executor)  # type: ignore[arg-type]

    client.logs(
        namespace="default",
        pod="api-7d8b4c5c9f-x9x9x",
        container="api",
        previous=True,
        tail=50,
        since="10m",
        timestamps=True,
    )

    assert executor.commands == [
        [
            "logs",
            "api-7d8b4c5c9f-x9x9x",
            "-n",
            "default",
            "-c",
            "api",
            "--previous",
            "--tail",
            "50",
            "--since",
            "10m",
            "--timestamps",
        ]
    ]


def test_client_rejects_invalid_kubectl_argument() -> None:
    client = KubectlClient(executor=FakeExecutor())  # type: ignore[arg-type]

    with pytest.raises(InvalidKubectlArgumentError):
        client.get_pods("default;rm")


def test_client_builds_deployment_commands() -> None:
    executor = FakeExecutor()
    client = KubectlClient(executor=executor)  # type: ignore[arg-type]

    client.get_deployment("default", "api")
    client.get_deployment_events("default", "api")
    client.get_deployment_yaml("default", "api")

    assert executor.commands == [
        [
            "get",
            "deployment",
            "api",
            "-n",
            "default",
            "-o",
            "json",
        ],
        [
            "get",
            "events",
            "-n",
            "default",
            "--field-selector",
            "involvedObject.kind=Deployment,involvedObject.name=api",
            "-o",
            "json",
        ],
        [
            "get",
            "deployment",
            "api",
            "-n",
            "default",
            "-o",
            "yaml",
        ],
    ]
