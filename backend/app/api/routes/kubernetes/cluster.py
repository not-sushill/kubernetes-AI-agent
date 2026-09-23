from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.kubernetes.services.cluster_service import ClusterService
from app.schemas.cluster import ClusterHealthResponse

router = APIRouter(prefix="/cluster", tags=["Kubernetes"])


def get_cluster_service() -> ClusterService:
    return ClusterService()


@router.get(
    "/health",
    response_model=ClusterHealthResponse,
)
def cluster_health(
    service: ClusterService = Depends(get_cluster_service),
) -> dict[str, Any]:
    return service.health()
