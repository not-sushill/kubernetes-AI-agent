"""
Cluster service.

Business logic for Kubernetes cluster operations.
"""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.kubernetes.client import KubectlClient
from app.kubernetes.parser import parse_json_output


class ClusterService:
    """
    Service responsible for Kubernetes cluster operations.
    """

    def __init__(self, client: KubectlClient | None = None) -> None:
        self.client = client or KubectlClient()

    def health(self) -> dict[str, Any]:
        """
        Return Kubernetes cluster health information.
        """

        start = perf_counter()

        version_result = self.client.version()
        context_result = self.client.current_context()

        latency = round((perf_counter() - start) * 1000, 2)

        version: dict[str, Any] = parse_json_output(version_result)

        client_version = (version.get("clientVersion") or {}).get(
            "gitVersion", "Unknown"
        )

        server_version = (version.get("serverVersion") or {}).get(
            "gitVersion", "Unknown"
        )

        return {
            "connected": True,
            "current_context": context_result.stdout.strip(),
            "kubectl_version": client_version,
            "server_version": server_version,
            "latency_ms": latency,
        }
