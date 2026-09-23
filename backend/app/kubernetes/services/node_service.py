from __future__ import annotations

import json

from app.kubernetes.client import KubectlClient


class NodeService:

    def __init__(
        self,
        client: KubectlClient | None = None,
    ) -> None:

        self.client = client or KubectlClient()

    @staticmethod
    def _get_internal_ip(addresses: list[dict]) -> str:

        for address in addresses:

            if address.get("type") == "InternalIP":
                return address.get("address", "")

        return ""

    @staticmethod
    def _get_role(labels: dict) -> str:

        if "node-role.kubernetes.io/control-plane" in labels:
            return "control-plane"

        if "node-role.kubernetes.io/master" in labels:
            return "master"

        return "worker"

    @staticmethod
    def _get_ready_status(conditions: list[dict]) -> str:

        for condition in conditions:

            if condition.get("type") == "Ready":

                return (
                    "Ready"
                    if condition.get("status") == "True"
                    else "NotReady"
                )

        return "Unknown"

    def list_nodes(self) -> list[dict]:

        result = self.client.get_nodes()

        data = json.loads(result.stdout)

        response = []

        for item in data.get("items", []):

            metadata = item.get("metadata", {})
            status = item.get("status", {})
            node_info = status.get("nodeInfo", {})
            labels = metadata.get("labels", {})

            response.append(
                {
                    "name": metadata.get("name", ""),
                    "status": self._get_ready_status(
                        status.get("conditions", [])
                    ),
                    "roles": self._get_role(labels),
                    "version": node_info.get(
                        "kubeletVersion",
                        "",
                    ),
                    "internal_ip": self._get_internal_ip(
                        status.get("addresses", [])
                    ),
                    "os_image": node_info.get(
                        "osImage",
                        "",
                    ),
                    "kernel_version": node_info.get(
                        "kernelVersion",
                        "",
                    ),
                    "container_runtime": node_info.get(
                        "containerRuntimeVersion",
                        "",
                    ),
                    "age": metadata.get(
                        "creationTimestamp",
                        "",
                    ),
                }
            )

        return response

    def get_node(
        self,
        node_name: str,
    ) -> dict:

        result = self.client.get_node(node_name)

        data = json.loads(result.stdout)

        metadata = data.get("metadata", {})
        status = data.get("status", {})
        spec = data.get("spec", {})
        node_info = status.get("nodeInfo", {})

        return {
            "name": metadata.get("name", ""),
            "status": self._get_ready_status(
                status.get("conditions", [])
            ),
            "roles": self._get_role(
                metadata.get("labels", {})
            ),
            "version": node_info.get(
                "kubeletVersion",
                "",
            ),
            "internal_ip": self._get_internal_ip(
                status.get("addresses", [])
            ),
            "os_image": node_info.get(
                "osImage",
                "",
            ),
            "kernel_version": node_info.get(
                "kernelVersion",
                "",
            ),
            "container_runtime": node_info.get(
                "containerRuntimeVersion",
                "",
            ),
            "age": metadata.get(
                "creationTimestamp",
                "",
            ),
            "labels": metadata.get(
                "labels",
                {},
            ),
            "annotations": metadata.get(
                "annotations",
                {},
            ),
            "capacity": status.get(
                "capacity",
                {},
            ),
            "allocatable": status.get(
                "allocatable",
                {},
            ),
            "conditions": status.get(
                "conditions",
                [],
            ),
            "provider_id": spec.get(
                "providerID",
                "",
            ),
            "pod_cidr": spec.get(
                "podCIDR",
                "",
            ),
            "unschedulable": spec.get(
                "unschedulable",
                False,
            ),
        }

    def describe_node(
        self,
        node_name: str,
    ) -> str:
        """
        Return kubectl describe node output.
        """

        result = self.client.describe_node(node_name)

        return result.stdout

    def get_yaml(
        self,
        node_name: str,
    ) -> str:
        """
        Return node YAML.
        """

        result = self.client.get_node_yaml(node_name)

        return result.stdout

    def get_events(
        self,
        node_name: str,
    ) -> list[dict]:
        """
        Node events.

        Currently Kubernetes doesn't expose a direct
        node events API like pods.

        For now we return namespace-independent events
        filtered by involved object.
        """

        result = self.client.executor.execute(
            [
                "get",
                "events",
                "--field-selector",
                f"involvedObject.kind=Node,involvedObject.name={node_name}",
                "-A",
                "-o",
                "json",
            ]
        )

        data = json.loads(result.stdout)

        events = []

        for item in data.get("items", []):

            events.append(
                {
                    "type": item.get("type"),
                    "reason": item.get("reason"),
                    "message": item.get("message"),
                    "count": item.get("count"),
                    "last_timestamp": item.get(
                        "lastTimestamp"
                    ),
                }
            )

        return events

    def get_metrics(
        self,
        node_name: str,
    ) -> dict:
        """
        Return metrics for a node.

        Gracefully handles clusters
        without Metrics Server.
        """

        try:

            result = self.client.top_nodes()

        except Exception:

            return {
                "available": False,
                "cpu": None,
                "memory": None,
            }

        for line in result.stdout.splitlines():

            cols = line.split()

            if not cols:
                continue

            if cols[0] != node_name:
                continue

            return {
                "available": True,
                "cpu": cols[1],
                "memory": cols[3],
            }

        return {
            "available": False,
            "cpu": None,
            "memory": None,
        }

    @staticmethod
    def calculate_health_score(
        node: dict,
        metrics: dict,
    ) -> int:
        """
        Simple node health score.
        """

        score = 100

        if node["status"] != "Ready":
            score -= 40

        for condition in node["conditions"]:

            t = condition.get("type")

            s = condition.get("status")

            if (
                t in (
                    "MemoryPressure",
                    "DiskPressure",
                    "PIDPressure",
                )
                and s == "True"
            ):
                score -= 15

        if not metrics["available"]:
            score -= 5

        return max(score, 0)

    def get_node_detail(
        self,
        node_name: str,
    ) -> dict:
        """
        Complete node information
        returned to the frontend.
        """

        node = self.get_node(node_name)

        metrics = self.get_metrics(node_name)

        node["metrics"] = metrics

        node["health_score"] = self.calculate_health_score(
            node,
            metrics,
        )

        node["yaml"] = self.get_yaml(node_name)

        node["events"] = self.get_events(node_name)

        return node