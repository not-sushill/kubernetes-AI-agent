from __future__ import annotations

from typing import Any

from app.kubernetes.client import KubectlClient
from app.kubernetes.parser import parse_json_output
from app.kubernetes.services.events import map_event_items


class PodService:
    """
    Business logic for Kubernetes pod operations.
    """

    def __init__(self, client: KubectlClient | None = None) -> None:
        self.client = client or KubectlClient()

    def list_pods(self, namespace: str | None = None) -> list[dict[str, Any]]:
        data = parse_json_output(self.client.get_pods(namespace))
        return [self._normalize_pod(item) for item in data.get("items", [])]

    def get_pod(self, namespace: str, pod: str) -> dict[str, Any]:
        return self._normalize_pod(parse_json_output(self.client.get_pod(namespace, pod)))

    @staticmethod
    def _normalize_pod(data: dict[str, Any]) -> dict[str, Any]:
        metadata, spec, status = (data.get(k) or {} for k in ("metadata", "spec", "status"))
        def containers(spec_key, status_key):
            statuses = {c["name"]: c for c in status.get(status_key, [])}
            specs = {c["name"]: c for c in spec.get(spec_key, [])}
            result = []
            for name in dict.fromkeys([*specs, *statuses]):
                c, cs = statuses.get(name, {}), specs.get(name, {})
                state = c.get("state") or {}
                result.append({
                    "name": name, "image": c.get("image") or cs.get("image", ""),
                    "ready": c.get("ready", False), "restart_count": c.get("restartCount", 0),
                    "state": {k: state.get(k) for k in ("waiting", "terminated", "running")},
                    "last_state": c.get("lastState") or {}, "started": c.get("started", False),
                    "container_id": c.get("containerID", ""), "image_id": c.get("imageID", ""),
                    "resources": cs.get("resources") or {}, "ports": cs.get("ports") or [],
                    "readiness_probe": cs.get("readinessProbe"), "liveness_probe": cs.get("livenessProbe"),
                    "startup_probe": cs.get("startupProbe"),
                })
            return result
        regular = containers("containers", "containerStatuses")
        init = containers("initContainers", "initContainerStatuses")
        return {
            "namespace": metadata.get("namespace", ""), "name": metadata.get("name", ""),
            "uid": metadata.get("uid", ""), "status": status.get("phase", ""),
            "reason": status.get("reason", ""), "message": status.get("message", ""),
            "node": spec.get("nodeName", ""), "pod_ip": status.get("podIP", ""),
            "host_ip": status.get("hostIP", ""), "qos_class": status.get("qosClass", ""),
            "service_account": spec.get("serviceAccountName", ""),
            "labels": metadata.get("labels") or {}, "annotations": metadata.get("annotations") or {},
            "owner_references": metadata.get("ownerReferences") or [],
            "conditions": status.get("conditions") or [], "volumes": spec.get("volumes") or [],
            "node_selector": spec.get("nodeSelector") or {}, "tolerations": spec.get("tolerations") or [],
            "affinity": spec.get("affinity") or {}, "containers": regular, "init_containers": init,
            "ready": f"{sum(c['ready'] for c in regular)}/{len(regular)}",
            "restarts": sum(c["restart_count"] for c in regular + init),
            "age": metadata.get("creationTimestamp", ""),
        }

    def get_logs(
        self,
        namespace: str,
        pod: str,
        container: str | None = None,
        previous: bool = False,
        tail: int | None = None,
        since: str | None = None,
        timestamps: bool = False,
    ) -> dict[str, Any]:
        try:
            result = self.client.logs(
                pod=pod,
                namespace=namespace,
                container=container,
                previous=previous,
                tail=tail,
                since=since,
                timestamps=timestamps,
            )

            lines = result.stdout.splitlines()

            return {
                "pod": pod,
                "namespace": namespace,
                "container": container,
                "previous": previous,
                "available": True,
                "line_count": len(lines),
                "logs": lines,
            }

        except Exception as exc:
            if previous:
                return {
                    "pod": pod,
                    "namespace": namespace,
                    "container": container,
                    "previous": True,
                    "available": False,
                    "line_count": 0,
                    "logs": [],
                    "message": (
                        f"Previous logs unavailable: {exc}"
                    ),
                }

            return {
                "pod": pod,
                "namespace": namespace,
                "container": container,
                "previous": False,
                "available": False,
                "line_count": 0,
                "logs": [],
                "message": str(exc),
            }

    def get_events(
        self,
        namespace: str,
        pod: str,
    ) -> dict[str, Any]:
        result = self.client.get_pod_events(namespace, pod)
        data = parse_json_output(result)
        events = map_event_items(data.get("items", []))

        return {
            "pod": pod,
            "namespace": namespace,
            "total_events": len(events),
            "events": events,
        }

    def describe_pod(
        self,
        namespace: str,
        pod: str,
    ) -> dict[str, Any]:
        result = self.client.describe_pod(namespace, pod)

        return {
            "pod": pod,
            "namespace": namespace,
            "description": result.stdout,
        }
