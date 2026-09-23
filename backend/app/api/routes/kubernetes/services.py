from __future__ import annotations

from fastapi import APIRouter, Depends

from app.kubernetes.services.service_service import (
    ServiceService,
)

router = APIRouter(
    prefix="/services",
    tags=["Services"],
)

def get_service_service() -> ServiceService:
    return ServiceService()


@router.get("")
def list_services(
    service: ServiceService = Depends(
        get_service_service,
    ),
):
    """
    List every Kubernetes Service.
    """
    return service.list_services()


@router.get("/{namespace}")
def list_namespace_services(
    namespace: str,
    service: ServiceService = Depends(
        get_service_service,
    ),
):
    """
    List Services in a namespace.
    """
    return service.list_services(
        namespace,
    )


@router.get("/{namespace}/{service_name}")
def get_service(
    namespace: str,
    service_name: str,
    service: ServiceService = Depends(
        get_service_service,
    ),
):
    """
    Get Service details.
    """

    return service.get_service(
        namespace,
        service_name,
    )


@router.get("/{namespace}/{service_name}/yaml")
def get_service_yaml(
    namespace: str,
    service_name: str,
    service: ServiceService = Depends(
        get_service_service,
    ),
):
    """
    Get Service YAML.
    """

    return {
        "yaml": service.get_service_yaml(
            namespace,
            service_name,
        )
    }

@router.get("/{namespace}/{service_name}/events")
def get_service_events(
    namespace: str,
    service_name: str,
    service: ServiceService = Depends(get_service_service),
):
    return service.get_events(namespace, service_name)
