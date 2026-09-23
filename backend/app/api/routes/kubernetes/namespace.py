from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from app.kubernetes.services.namespace_service import NamespaceService
from app.schemas.namespace import NamespaceResponse

router = APIRouter(prefix="/namespaces")


def get_namespace_service() -> NamespaceService:
    return NamespaceService()


@router.get(
    "",
    response_model=list[NamespaceResponse],
)
def list_namespaces(
    service: NamespaceService = Depends(get_namespace_service),
) -> list[dict[str, Any]]:
    return service.list_namespaces()
