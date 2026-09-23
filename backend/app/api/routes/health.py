from datetime import datetime, timezone

from fastapi import APIRouter

from app.core import settings

router = APIRouter(
    prefix="/health",
    tags=["Health"],
)


@router.get("")
async def health():
    return {
        "status": "healthy",
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/live")
async def liveness():
    return {"status": "alive"}


@router.get("/ready")
async def readiness():
    return {"status": "ready"}
