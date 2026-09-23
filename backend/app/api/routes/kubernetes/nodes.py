from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.kubernetes.services.node_service import NodeService
from app.schemas.node import NodeDetail, NodeSummary

router = APIRouter(
    prefix="/nodes",
    tags=["Nodes"],
)


def get_node_service() -> NodeService:
    return NodeService()


@router.get(
    "",
    response_model=list[NodeSummary],
)
def list_nodes(
    service: NodeService = Depends(
        get_node_service,
    ),
):
    """
    List every Kubernetes node.
    """
    return service.list_nodes()


@router.get(
    "/{node_name}",
    response_model=NodeDetail,
)
def get_node(
    node_name: str,
    service: NodeService = Depends(
        get_node_service,
    ),
):
    """
    Return detailed information for a node.
    """
    try:
        return service.get_node_detail(node_name)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc