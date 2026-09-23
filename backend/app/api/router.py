from fastapi import APIRouter

from app.api.routes.health import router as health_router

from app.api.routes.kubernetes.cluster import (
    router as cluster_router,
)
from app.api.routes.kubernetes.contexts import (
    router as contexts_router,
)
from app.api.routes.kubernetes.deployments import (
    router as deployments_router,
)
from app.api.routes.kubernetes.namespace import (
    router as namespace_router,
)
from app.api.routes.kubernetes.nodes import (
    router as nodes_router,
)
from app.api.routes.kubernetes.pods import (
    router as pods_router,
)
from app.api.routes.kubernetes.services import (
    router as services_router,
)
from app.api.routes.kubernetes.ingress import (
    router as ingress_router,
)

from app.investigations.router import (
    router as investigations_router,
)


api_router = APIRouter()


api_router.include_router(
    health_router,
    tags=["Health"],
)

api_router.include_router(
    cluster_router,
    prefix="/kubernetes",
    tags=["Kubernetes"],
)

api_router.include_router(
    contexts_router,
    prefix="/kubernetes",
    tags=["Kubernetes"],
)

api_router.include_router(
    namespace_router,
    prefix="/kubernetes",
    tags=["Kubernetes"],
)

api_router.include_router(
    pods_router,
    prefix="/kubernetes",
    tags=["Kubernetes"],
)

api_router.include_router(
    deployments_router,
    prefix="/kubernetes",
    tags=["Kubernetes"],
)

api_router.include_router(
    nodes_router,
    prefix="/kubernetes",
    tags=["Kubernetes"],
)

api_router.include_router(
    services_router,
    prefix="/kubernetes",
    tags=["Kubernetes"],
)

api_router.include_router(
    ingress_router,
    prefix="/kubernetes",
    tags=["Kubernetes"],
)

api_router.include_router(
    investigations_router,
    prefix="/v1",
)