from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.api.routes.kubernetes.cluster import get_cluster_service
from app.api.routes.kubernetes.deployments import get_deployment_service
from app.api.routes.kubernetes.namespace import get_namespace_service
from app.api.routes.kubernetes.pods import get_pod_service
from app.main import app


class FakeClusterService:
    def health(self) -> dict[str, Any]:
        return {
            "connected": True,
            "current_context": "kind-local",
            "kubectl_version": "v1.30.0",
            "server_version": "v1.30.0",
            "latency_ms": 2.5,
        }


class FakeNamespaceService:
    def list_namespaces(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "default",
                "status": "Active",
                "age": "2026-01-01T00:00:00Z",
            }
        ]


class FakePodService:
    def list_pods(
        self,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "namespace": namespace or "default",
                "name": "api-7d8b4c5c9f-x9x9x",
                "status": "Running",
                "ready": "1/1",
                "restarts": 0,
                "node": "worker-1",
                "pod_ip": "10.0.0.10",
                "age": "2026-01-01T00:00:00Z",
            }
        ]

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
        return {
            "pod": pod,
            "namespace": namespace,
            "line_count": 2,
            "logs": ["starting", "ready"],
        }


class FakeDeploymentService:
    def list_deployments(
        self,
        namespace: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "namespace": namespace or "default",
                "name": "api",
                "replicas": 3,
                "ready_replicas": 3,
                "available_replicas": 3,
                "updated_replicas": 3,
                "strategy": "RollingUpdate",
                "age": "2026-01-01T00:00:00Z",
            }
        ]

    def get_deployment(
        self,
        namespace: str,
        deployment: str,
    ) -> dict[str, Any]:
        return {
            "namespace": namespace,
            "name": deployment,
            "replicas": 3,
            "ready_replicas": 3,
            "available_replicas": 3,
            "updated_replicas": 3,
            "strategy": "RollingUpdate",
            "age": "2026-01-01T00:00:00Z",
            "selector": {"app": deployment},
            "labels": {"app": deployment},
            "annotations": {},
            "containers": [
                {
                    "name": deployment,
                    "image": f"registry.example.com/{deployment}:v1",
                }
            ],
            "conditions": [
                {
                    "type": "Available",
                    "status": "True",
                    "reason": "MinimumReplicasAvailable",
                    "message": "Deployment has minimum availability.",
                    "last_transition_time": "2026-01-01T00:01:00Z",
                }
            ],
        }

    def get_events(
        self,
        namespace: str,
        deployment: str,
    ) -> dict[str, Any]:
        return {
            "deployment": deployment,
            "namespace": namespace,
            "total_events": 1,
            "events": [
                {
                    "type": "Normal",
                    "reason": "ScalingReplicaSet",
                    "message": "Scaled up replica set.",
                    "count": 1,
                    "first_timestamp": "2026-01-01T00:00:00Z",
                    "last_timestamp": "2026-01-01T00:00:00Z",
                }
            ],
        }

    def get_yaml(
        self,
        namespace: str,
        deployment: str,
    ) -> dict[str, str]:
        return {
            "deployment": deployment,
            "namespace": namespace,
            "yaml": "apiVersion: apps/v1\nkind: Deployment\n",
        }


def test_kubernetes_routes_return_registered_resource_payloads() -> None:
    app.dependency_overrides[get_cluster_service] = FakeClusterService
    app.dependency_overrides[get_namespace_service] = FakeNamespaceService
    app.dependency_overrides[get_pod_service] = FakePodService
    app.dependency_overrides[get_deployment_service] = FakeDeploymentService

    try:
        client = TestClient(app)

        cluster_response = client.get("/api/kubernetes/cluster/health")
        namespaces_response = client.get("/api/kubernetes/namespaces")
        pods_response = client.get("/api/kubernetes/pods/default")
        logs_response = client.get(
            "/api/kubernetes/pods/default/api-7d8b4c5c9f-x9x9x/logs",
        )
        deployments_response = client.get("/api/kubernetes/deployments")
        namespace_deployments_response = client.get(
            "/api/kubernetes/deployments/default",
        )
        deployment_response = client.get(
            "/api/kubernetes/deployments/default/api",
        )
        deployment_events_response = client.get(
            "/api/kubernetes/deployments/default/api/events",
        )
        deployment_yaml_response = client.get(
            "/api/kubernetes/deployments/default/api/yaml",
        )

        assert cluster_response.status_code == 200
        assert cluster_response.json()["current_context"] == "kind-local"

        assert namespaces_response.status_code == 200
        assert namespaces_response.json()[0]["name"] == "default"

        assert pods_response.status_code == 200
        assert pods_response.json()[0]["ready"] == "1/1"

        assert logs_response.status_code == 200
        assert logs_response.json()["logs"] == ["starting", "ready"]

        assert deployments_response.status_code == 200
        assert deployments_response.json()[0]["name"] == "api"

        assert namespace_deployments_response.status_code == 200
        assert namespace_deployments_response.json()[0]["namespace"] == "default"

        assert deployment_response.status_code == 200
        assert deployment_response.json()["containers"][0]["name"] == "api"

        assert deployment_events_response.status_code == 200
        assert (
            deployment_events_response.json()["events"][0]["reason"]
            == "ScalingReplicaSet"
        )

        assert deployment_yaml_response.status_code == 200
        assert "kind: Deployment" in deployment_yaml_response.json()["yaml"]
    finally:
        app.dependency_overrides.clear()
