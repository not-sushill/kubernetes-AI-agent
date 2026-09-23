from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.kubernetes.services.ingress_service import IngressService
from app.schemas.event import EventResponse
from app.schemas.ingress import (
    IngressDetailResponse,
    IngressEventsResponse,
    IngressResponse,
    IngressYamlResponse,
)

router = APIRouter(
    prefix="/ingresses",
    tags=["Ingresses"],
)


def get_ingress_service() -> IngressService:
    return IngressService()


# ==========================================================
# List all ingresses
# ==========================================================


@router.get(
    "",
    response_model=list[IngressResponse],
)
def list_all_ingresses(
    service: IngressService = Depends(
        get_ingress_service,
    ),
) -> list[dict[str, Any]]:
    """
    List Kubernetes Ingress resources across all namespaces.
    """
    return service.list_ingresses()


# ==========================================================
# List ingresses in namespace
# ==========================================================


@router.get(
    "/{namespace}",
    response_model=list[IngressResponse],
)
def list_namespace_ingresses(
    namespace: str,
    service: IngressService = Depends(
        get_ingress_service,
    ),
) -> list[dict[str, Any]]:
    """
    List Kubernetes Ingress resources in a namespace.
    """
    return service.list_ingresses(namespace)


# ==========================================================
# Get ingress details
# ==========================================================


@router.get(
    "/{namespace}/{ingress}",
    response_model=IngressDetailResponse,
)
def get_ingress(
    namespace: str,
    ingress: str,
    service: IngressService = Depends(
        get_ingress_service,
    ),
) -> dict[str, Any]:
    """
    Return detailed information about an Ingress.
    """
    return service.get_ingress(
        namespace,
        ingress,
    )


# ==========================================================
# Get ingress events
# ==========================================================


@router.get(
    "/{namespace}/{ingress}/events",
    response_model=IngressEventsResponse,
)
def get_ingress_events(
    namespace: str,
    ingress: str,
    service: IngressService = Depends(
        get_ingress_service,
    ),
) -> dict[str, Any]:
    """
    Return Kubernetes events associated with an Ingress.
    """
    return service.get_events(
        namespace,
        ingress,
    )


# ==========================================================
# Get ingress YAML
# ==========================================================


@router.get(
    "/{namespace}/{ingress}/yaml",
    response_model=IngressYamlResponse,
)
def get_ingress_yaml(
    namespace: str,
    ingress: str,
    service: IngressService = Depends(
        get_ingress_service,
    ),
) -> dict[str, Any]:
    """
    Return the raw Kubernetes YAML for an Ingress.
    """
    return service.get_yaml(
        namespace,
        ingress,
    )