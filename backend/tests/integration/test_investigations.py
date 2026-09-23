from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.investigations.models import (
    Investigation,
    InvestigationCreate,
    InvestigationEvidence,
    InvestigationSection,
    InvestigationStatus,
    InvestigationTarget,
)
from app.investigations.router import get_investigation_service
from app.main import app


def investigation_fixture() -> Investigation:
    evidence = InvestigationEvidence(
        namespace=InvestigationSection.collected({"name": "default", "found": True}),
        pod=InvestigationSection.collected([]),
        deployment=InvestigationSection.collected([]),
        replicaset=InvestigationSection.collected([]),
        node=InvestigationSection.collected([]),
        events=InvestigationSection.collected([]),
        logs=InvestigationSection.skipped("No pod was available."),
        services=InvestigationSection.collected([]),
        pvc=InvestigationSection.collected([]),
        metrics=InvestigationSection.collected({"pods": [], "nodes": []}),
    )
    now = datetime.now(timezone.utc)

    return Investigation(
        id="inv-1",
        target=InvestigationTarget(
            namespace="default",
            resource_type="namespace",
            resource_name="default",
        ),
        status=InvestigationStatus.COMPLETED,
        evidence=evidence,
        created_at=now,
        updated_at=now,
    )


class FakeInvestigationService:
    def create(self, request: InvestigationCreate) -> Investigation:
        return investigation_fixture()

    def get(self, investigation_id: str) -> Investigation:
        return investigation_fixture()


def test_investigation_routes_are_registered() -> None:
    app.dependency_overrides[get_investigation_service] = FakeInvestigationService

    try:
        client = TestClient(app)

        created_response = client.post(
            "/api/v1/investigations",
            json={
                "namespace": "default",
                "resource_type": "namespace",
            },
        )
        fetched_response = client.get("/api/v1/investigations/inv-1")

        assert created_response.status_code == 201
        assert created_response.json()["id"] == "inv-1"
        assert fetched_response.status_code == 200
        assert fetched_response.json()["target"]["namespace"] == "default"
    finally:
        app.dependency_overrides.clear()
