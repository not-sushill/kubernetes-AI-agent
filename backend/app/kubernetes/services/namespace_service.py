from __future__ import annotations

from typing import Any

from app.kubernetes.client import KubectlClient
from app.kubernetes.parser import parse_json_output


class NamespaceService:
    """
    Business logic for namespace operations.
    """

    def __init__(self, client: KubectlClient | None = None) -> None:
        self.client = client or KubectlClient()

    def list_namespaces(self) -> list[dict[str, Any]]:
        result = self.client.get_namespaces()

        data = parse_json_output(result)

        namespaces: list[dict[str, Any]] = []

        for item in data.get("items", []):
            metadata = item.get("metadata", {})
            status = item.get("status", {})

            namespaces.append(
                {
                    "name": metadata.get("name") or "",
                    "status": status.get("phase") or "",
                    "age": metadata.get("creationTimestamp") or "",
                }
            )

        return namespaces
