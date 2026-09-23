from fastapi import APIRouter

from app.api.routes.v1.investigations import (
    router as investigations_router,
)


router = APIRouter()


router.include_router(
    investigations_router,
)
