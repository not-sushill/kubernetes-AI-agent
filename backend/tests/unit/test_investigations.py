from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
from app.investigations.collector import InvestigationCollector
from app.investigations.models import (
    InvestigationCreate,
    InvestigationResourceType,
    InvestigationSectionStatus,
)
from app.investigations.service import InvestigationService


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
    def __init__(self) -> None:
        self.logged_pod: str | None = None

    def list_pods(self, namespace: str | None = None) -> list[dict[str, Any]]:
        return [
            {
                "namespace": namespace or "default",
                "name": "api-1",
                "labels": {"app": "api"},
                "status": "Running",
                "ready": "1/1",
                "restarts": 0,
                "node": "worker-1",
                "pod_ip": "10.0.0.10",
                "age": "2026-01-01T00:00:00Z",
            },
            {
                "namespace": namespace or "default",
                "name": "api-2",
                "labels": {"app": "api"},
                "status": "CrashLoopBackOff",
                "ready": "0/1",
                "restarts": 4,
                "node": "worker-1",
                "pod_ip": "10.0.0.11",
                "age": "2026-01-01T00:00:00Z",
            },
        ]

    def get_pod(self, namespace: str, pod: str) -> dict[str, Any]:
        return {
            "namespace": namespace,
            "name": pod,
            "status": "Running",
        }

    def get_events(self, namespace: str, pod: str) -> dict[str, Any]:
        return {
            "pod": pod,
            "namespace": namespace,
            "total_events": 0,
            "events": [],
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
        self.logged_pod = pod

        return {
            "pod": pod,
            "namespace": namespace,
            "line_count": 1,
            "logs": ["failed readiness probe"],
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
                "replicas": 2,
                "ready_replicas": 1,
                "available_replicas": 1,
                "updated_replicas": 2,
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
            "replicas": 2,
            "ready_replicas": 1,
            "available_replicas": 1,
            "updated_replicas": 2,
            "strategy": "RollingUpdate",
            "age": "2026-01-01T00:00:00Z",
            "selector": {"app": deployment},
            "labels": {"app": deployment},
            "annotations": {},
            "containers": [],
            "conditions": [],
        }

    def get_events(self, namespace: str, deployment: str) -> dict[str, Any]:
        return {
            "deployment": deployment,
            "namespace": namespace,
            "total_events": 0,
            "events": [],
        }


class FakeInventoryService:
    def list_endpoint_slices(self, namespace):
        return []

    def list_network_policies(self, namespace):
        return []

    def list_resource_quotas(self, namespace):
        return []

    def list_replicasets(self, namespace: str) -> list[dict[str, Any]]:
        return [{"namespace": namespace, "name": "api-abc"}]

    def list_nodes(self) -> list[dict[str, Any]]:
        return [{"name": "worker-1", "ready": "True"}]

    def list_namespace_events(self, namespace: str) -> list[dict[str, Any]]:
        return []

    def list_services(self, namespace: str) -> list[dict[str, Any]]:
        return [{"namespace": namespace, "name": "api"}]

    def list_persistent_volume_claims(
        self,
        namespace: str,
    ) -> list[dict[str, Any]]:
        return []

    def get_metrics(self, namespace: str) -> dict[str, Any]:
        return {
            "pods": [{"name": "api-2",
                "labels": {"app": "api"}, "cpu": "10m", "memory": "64Mi"}],
            "nodes": [{"name": "worker-1", "cpu": "200m"}],
        }


class FakeCollector:
    def collect(self, request: InvestigationCreate):
        return InvestigationCollector(
            namespace_service=FakeNamespaceService(),  # type: ignore[arg-type]
            pod_service=FakePodService(),  # type: ignore[arg-type]
            deployment_service=FakeDeploymentService(),  # type: ignore[arg-type]
            inventory_service=FakeInventoryService(),  # type: ignore[arg-type]
        ).collect(request)


class FakeClusterService:
    def get_context(self) -> str:
        return "test-cluster"


def test_collector_gathers_required_sections() -> None:
    pod_service = FakePodService()
    collector = InvestigationCollector(
        namespace_service=FakeNamespaceService(),  # type: ignore[arg-type]
        pod_service=pod_service,  # type: ignore[arg-type]
        deployment_service=FakeDeploymentService(),  # type: ignore[arg-type]
        inventory_service=FakeInventoryService(),  # type: ignore[arg-type]
    )

    evidence = collector.collect(InvestigationCreate(namespace="default"))

    assert evidence.namespace.status is InvestigationSectionStatus.COLLECTED
    assert evidence.pod.status is InvestigationSectionStatus.COLLECTED
    assert evidence.deployment.status is InvestigationSectionStatus.COLLECTED
    assert evidence.replicaset.status is InvestigationSectionStatus.COLLECTED
    assert evidence.node.status is InvestigationSectionStatus.COLLECTED
    assert evidence.events.status is InvestigationSectionStatus.COLLECTED
    assert evidence.logs.status is InvestigationSectionStatus.COLLECTED
    assert evidence.services.status is InvestigationSectionStatus.COLLECTED
    assert evidence.pvc.status is InvestigationSectionStatus.COLLECTED
    assert evidence.metrics.status is InvestigationSectionStatus.COLLECTED
    assert pod_service.logged_pod == "api-2"


def test_investigation_service_persists_normalized_evidence() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        service = InvestigationService(
            db=session,
            collector=FakeCollector(),  # type: ignore[arg-type]
            cluster_service=FakeClusterService(),  # type: ignore[arg-type]
        )

        created = service.create(
            InvestigationCreate(
                namespace="default",
                resource_type=InvestigationResourceType.DEPLOYMENT,
                resource_name="api",
            )
        )
        fetched = service.get(created.id)

    assert created.id == fetched.id
    assert fetched.target.namespace == "default"
    assert fetched.target.resource_name == "api"
    assert fetched.evidence.metrics.data["pods"][0]["name"] == "api-2"
    assert isinstance(fetched.created_at, datetime)
