from __future__ import annotations

from typing import Any

from app.kubernetes.client import KubectlClient
from app.kubernetes.parser import parse_json_output
from app.kubernetes.services.events import map_event_items


class KubernetesInventoryService:
    """
    Business logic for cluster inventory resources used by investigations.
    """

    def __init__(self, client: KubectlClient | None = None) -> None:
        self.client = client or KubectlClient()

    def list_replicasets(self, namespace: str) -> list[dict[str, Any]]:
        result = self.client.get_replicasets(namespace)
        data = parse_json_output(result)

        replicasets: list[dict[str, Any]] = []

        for item in data.get("items", []):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}

            replicasets.append(
                {
                    "namespace": metadata.get("namespace") or "",
                    "name": metadata.get("name") or "",
                    "desired_replicas": spec.get("replicas") or 0,
                    "ready_replicas": status.get("readyReplicas") or 0,
                    "available_replicas": status.get("availableReplicas") or 0,
                    "fully_labeled_replicas": (status.get("fullyLabeledReplicas") or 0),
                    "owner_references": metadata.get("ownerReferences") or [],
                    "age": metadata.get("creationTimestamp") or "",
                }
            )

        return replicasets

    def list_nodes(self) -> list[dict[str, Any]]:
        result = self.client.get_nodes()
        data = parse_json_output(result)

        nodes: list[dict[str, Any]] = []

        for item in data.get("items", []):
            metadata = item.get("metadata") or {}
            status = item.get("status") or {}
            node_info = status.get("nodeInfo") or {}
            conditions = status.get("conditions") or []
            ready_condition = next(
                (
                    condition
                    for condition in conditions
                    if condition.get("type") == "Ready"
                ),
                {},
            )

            nodes.append(
                {
                    "name": metadata.get("name") or "",
                    "ready": ready_condition.get("status") or "Unknown",
                    "roles": self._node_roles(metadata.get("labels") or {}),
                    "kubelet_version": node_info.get("kubeletVersion") or "",
                    "container_runtime": (
                        node_info.get("containerRuntimeVersion") or ""
                    ),
                    "conditions": conditions,
                    "age": metadata.get("creationTimestamp") or "",
                }
            )

        return nodes

    def list_services(self, namespace: str) -> list[dict[str, Any]]:
        result = self.client.get_services(namespace)
        data = parse_json_output(result)

        services: list[dict[str, Any]] = []

        for item in data.get("items", []):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}

            services.append(
                {
                    "namespace": metadata.get("namespace") or "",
                    "name": metadata.get("name") or "",
                    "type": spec.get("type") or "",
                    "cluster_ip": spec.get("clusterIP") or "",
                    "ports": spec.get("ports") or [],
                    "selector": spec.get("selector") or {},
                    "publish_not_ready_addresses": spec.get("publishNotReadyAddresses", False),
                    "external_name": spec.get("externalName"),
                    "age": metadata.get("creationTimestamp") or "",
                }
            )

        return services

    def list_persistent_volume_claims(
        self,
        namespace: str,
    ) -> list[dict[str, Any]]:
        result = self.client.get_persistent_volume_claims(namespace)
        data = parse_json_output(result)

        claims: list[dict[str, Any]] = []

        for item in data.get("items", []):
            metadata = item.get("metadata") or {}
            spec = item.get("spec") or {}
            status = item.get("status") or {}
            requests = (spec.get("resources") or {}).get("requests") or {}

            claims.append(
                {
                    "namespace": metadata.get("namespace") or "",
                    "name": metadata.get("name") or "",
                    "status": status.get("phase") or "",
                    "volume": spec.get("volumeName") or "",
                    "storage_class": spec.get("storageClassName") or "",
                    "capacity": (status.get("capacity") or {}).get(
                        "storage",
                        "",
                    ),
                    "requested_storage": requests.get("storage") or "",
                    "access_modes": spec.get("accessModes") or [],
                    "age": metadata.get("creationTimestamp") or "",
                }
            )

        return claims

    def list_namespace_events(self, namespace: str) -> list[dict[str, Any]]:
        result = self.client.get_namespace_events(namespace)
        data = parse_json_output(result)

        return map_event_items(data.get("items", []))

    def get_metrics(self, namespace: str) -> dict[str, Any]:
        return {
            "pods": self._parse_pod_metrics(self.client.top_pods(namespace).stdout),
            "nodes": self._parse_node_metrics(self.client.top_nodes().stdout),
        }

    @staticmethod
    def _node_roles(labels: dict[str, Any]) -> list[str]:
        roles = [
            key.removeprefix("node-role.kubernetes.io/")
            for key in labels
            if key.startswith("node-role.kubernetes.io/")
        ]

        return sorted(role or "control-plane" for role in roles)

    @staticmethod
    def _parse_pod_metrics(output: str) -> list[dict[str, str]]:
        metrics: list[dict[str, str]] = []

        for line in output.splitlines():
            columns = line.split()

            if len(columns) >= 3:
                metrics.append(
                    {
                        "name": columns[0],
                        "cpu": columns[1],
                        "memory": columns[2],
                    }
                )

        return metrics

    @staticmethod
    def _parse_node_metrics(output: str) -> list[dict[str, str]]:
        metrics: list[dict[str, str]] = []

        for line in output.splitlines():
            columns = line.split()

            if len(columns) >= 5:
                metrics.append(
                    {
                        "name": columns[0],
                        "cpu": columns[1],
                        "cpu_percent": columns[2],
                        "memory": columns[3],
                        "memory_percent": columns[4],
                    }
                )

        return metrics

    def list_endpoint_slices(self, namespace: str) -> list[dict[str, Any]]:
        return parse_json_output(self.client.get_endpoint_slices(namespace)).get("items", [])

    def list_network_policies(self, namespace: str) -> list[dict[str, Any]]:
        return parse_json_output(self.client.get_network_policies(namespace)).get("items", [])

    def list_resource_quotas(self, namespace: str) -> list[dict[str, Any]]:
        return parse_json_output(self.client.get_resource_quotas(namespace)).get("items", [])
