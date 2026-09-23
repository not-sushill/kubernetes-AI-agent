from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query

from app.kubernetes.validators import MAX_LOG_TAIL_LINES
from app.kubernetes.services.pod_service import PodService
from app.schemas.describe import PodDescribeResponse
from app.schemas.event import PodEventsResponse
from app.schemas.log import PodLogsResponse
from app.schemas.pod import PodDetailResponse, PodResponse
from app.kubernetes.services.investigation import (
    PodInvestigationService,
)
router = APIRouter(prefix="/pods")
def get_pod_investigation_service() -> PodInvestigationService:
    return PodInvestigationService()

def get_pod_service() -> PodService:
    return PodService()
def get_investigation_service() -> PodInvestigationService:
    return PodInvestigationService()
@router.get(
    "/{namespace}/{pod}/investigate",
    summary="Investigate Pod",
)
def investigate_pod(
    namespace: str,
    pod: str,
    tail: int = Query(default=200, ge=1, le=1000),
    service: PodInvestigationService = Depends(
        get_pod_investigation_service,
    ),
) -> dict[str, Any]:
    return service.investigate(
        namespace=namespace,
        pod=pod,
        tail=tail,
    )
@router.get(
    "",
    response_model=list[PodResponse],
)
def list_all_pods(
    service: PodService = Depends(get_pod_service),
) -> list[dict[str, Any]]:
    return service.list_pods()


@router.get(
    "/{namespace}",
    response_model=list[PodResponse],
)
def list_namespace_pods(
    namespace: str,
    service: PodService = Depends(get_pod_service),
) -> list[dict[str, Any]]:
    return service.list_pods(namespace)
@router.get(
    "/{namespace}/{pod}/investigate",
    summary="Investigate Pod",
)
def investigate_pod(
    namespace: str,
    pod: str,
    tail: int = Query(
        default=200,
        ge=1,
        le=MAX_LOG_TAIL_LINES,
    ),
    service: PodInvestigationService = Depends(
        get_investigation_service,
    ),
) -> dict[str, Any]:
    return service.investigate(
        namespace=namespace,
        pod=pod,
        tail=tail,
    )

@router.get(
    "/{namespace}/{pod}",
    response_model=PodDetailResponse,
)
def get_pod(
    namespace: str,
    pod: str,
    service: PodService = Depends(get_pod_service),
) -> dict[str, Any]:
    return service.get_pod(namespace, pod)


@router.get(
    "/{namespace}/{pod}/logs",
    response_model=PodLogsResponse,
    summary="Get Pod Logs",
)
def get_logs(
    namespace: str,
    pod: str,
    container: str | None = None,
    previous: bool = False,
    tail: int | None = Query(default=200, ge=0, le=MAX_LOG_TAIL_LINES),
    since: str | None = None,
    timestamps: bool = False,
    service: PodService = Depends(get_pod_service),
) -> dict[str, Any]:
    return service.get_logs(
        namespace=namespace,
        pod=pod,
        container=container,
        previous=previous,
        tail=tail,
        since=since,
        timestamps=timestamps,
    )


@router.get(
    "/{namespace}/{pod}/events",
    response_model=PodEventsResponse,
    summary="Get Pod Events",
)
def get_events(
    namespace: str,
    pod: str,
    service: PodService = Depends(get_pod_service),
) -> dict[str, Any]:
    return service.get_events(
        namespace=namespace,
        pod=pod,
    )


@router.get(
    "/{namespace}/{pod}/describe",
    response_model=PodDescribeResponse,
    summary="Describe Pod",
)
def describe_pod(
    namespace: str,
    pod: str,
    service: PodService = Depends(get_pod_service),
) -> dict[str, Any]:
    return service.describe_pod(namespace, pod)
