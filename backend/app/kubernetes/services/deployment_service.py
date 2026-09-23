from __future__ import annotations

from typing import Any

from app.kubernetes.client import KubectlClient
from app.kubernetes.parser import parse_json_output
from app.kubernetes.services.events import map_event_items


class DeploymentService:
    """
    Business logic for Kubernetes deployment operations.
    """

    def __init__(self, client: KubectlClient | None = None) -> None:
        self.client = client or KubectlClient()

    def list_deployments(
        self,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        result = self.client.get_deployments(namespace)
        data = parse_json_output(result)

        return [self._deployment_summary(item) for item in data.get("items", [])]

    def get_deployment(
        self,
        namespace: str,
        deployment: str,
    ) -> dict[str, Any]:
        result = self.client.get_deployment(namespace, deployment)
        data = parse_json_output(result)

        spec = data.get("spec") or {}
        template = spec.get("template") or {}
        template_spec = template.get("spec") or {}
        metadata = data.get("metadata") or {}
        status = data.get("status") or {}

        details = self._deployment_summary(data)
        details.update(
            {
                "selector_expressions": (spec.get("selector") or {}).get("matchExpressions") or [],
                "selector": self._string_map(
                    (spec.get("selector") or {}).get("matchLabels") or {}
                ),
                "labels": self._string_map(metadata.get("labels") or {}),
                "annotations": self._string_map(metadata.get("annotations") or {}),
                "containers": [
                    {
                        "name": container.get("name") or "",
                        "image": container.get("image") or "",
                    }
                    for container in template_spec.get("containers") or []
                ],
                "conditions": [
                    {
                        "type": condition.get("type") or "",
                        "status": condition.get("status") or "",
                        "reason": condition.get("reason") or "",
                        "message": condition.get("message") or "",
                        "last_transition_time": (
                            condition.get("lastTransitionTime") or ""
                        ),
                    }
                    for condition in status.get("conditions") or []
                ],
            }
        )

        return details

    def get_events(
        self,
        namespace: str,
        deployment: str,
    ) -> dict[str, Any]:
        result = self.client.get_deployment_events(namespace, deployment)
        data = parse_json_output(result)
        events = map_event_items(data.get("items", []))

        return {
            "deployment": deployment,
            "namespace": namespace,
            "total_events": len(events),
            "events": events,
        }

    def get_yaml(
        self,
        namespace: str,
        deployment: str,
    ) -> dict[str, str]:
        result = self.client.get_deployment_yaml(namespace, deployment)

        return {
            "deployment": deployment,
            "namespace": namespace,
            "yaml": result.stdout,
        }

    @staticmethod
    def _deployment_summary(item: dict[str, Any]) -> dict[str, Any]:
        metadata = item.get("metadata") or {}
        spec = item.get("spec") or {}
        status = item.get("status") or {}

        return {
            "namespace": metadata.get("namespace") or "",
            "name": metadata.get("name") or "",
            "uid": metadata.get("uid", ""),
            "generation": metadata.get("generation", 0),
            "observed_generation": status.get("observedGeneration", 0),
            "paused": spec.get("paused", False),
            "conditions": status.get("conditions") or [],
            "replicas": spec.get("replicas", 1),
            "ready_replicas": status.get("readyReplicas") or 0,
            "available_replicas": status.get("availableReplicas") or 0,
            "updated_replicas": status.get("updatedReplicas") or 0,
            "strategy": (spec.get("strategy") or {}).get("type") or "",
            "age": metadata.get("creationTimestamp") or "",
        }

    @staticmethod
    def _string_map(values: dict[str, Any]) -> dict[str, str]:
        return {str(key): str(value) for key, value in values.items()}
