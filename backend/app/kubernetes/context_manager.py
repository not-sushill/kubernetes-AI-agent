"""
Kubernetes context management.

This module reads the contexts available in the local kubeconfig
without changing the active kubectl context.

The application always uses explicit --context arguments when a
context is selected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.kubernetes.exceptions import InvalidKubectlArgumentError
from app.kubernetes.executor import KubectlExecutor


COMMAND_CONFIG_GET_CONTEXTS: Final[list[str]] = [
    "config",
    "get-contexts",
    "-o",
    "name",
]

COMMAND_CONFIG_CURRENT_CONTEXT: Final[list[str]] = [
    "config",
    "current-context",
]


@dataclass(frozen=True)
class KubernetesContext:
    """
    Represents an available Kubernetes kubeconfig context.
    """

    name: str
    current: bool


class KubernetesContextManager:
    """
    Provides safe access to Kubernetes contexts.

    This class never changes the active kubectl context.
    """

    def __init__(
        self,
        executor: KubectlExecutor | None = None,
    ) -> None:
        self.executor = executor or KubectlExecutor()

    def get_current_context(self) -> str:
        """
        Return the currently configured kubectl context.
        """

        result = self.executor.execute(
            COMMAND_CONFIG_CURRENT_CONTEXT,
        )

        context = result.stdout.strip()

        if not context:
            raise InvalidKubectlArgumentError(
                "No active Kubernetes context is configured."
            )

        return context

    def list_contexts(self) -> list[KubernetesContext]:
        """
        Return all contexts available in kubeconfig.
        """

        current_context = self.get_current_context()

        result = self.executor.execute(
            COMMAND_CONFIG_GET_CONTEXTS,
        )

        context_names = [
            line.strip()
            for line in result.stdout.splitlines()
            if line.strip()
        ]

        return [
            KubernetesContext(
                name=name,
                current=name == current_context,
            )
            for name in context_names
        ]

    def validate_context(
        self,
        context: str | None,
    ) -> str | None:
        """
        Validate a requested context.

        Returns None when no explicit context was supplied.
        """

        if context is None:
            return None

        context = context.strip()

        if not context:
            return None

        available_contexts = {
            item.name
            for item in self.list_contexts()
        }

        if context not in available_contexts:
            raise InvalidKubectlArgumentError(
                f"Unknown Kubernetes context: '{context}'"
            )

        return context