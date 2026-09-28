from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.router import api_router
from app.core import app_logger, settings
from app.database.base import Base
from app.db.database import engine


Base.metadata.create_all(
    bind=engine,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("=" * 70)
    app_logger.info(f"Starting {settings.APP_NAME}")
    app_logger.info(f"Environment : {settings.ENVIRONMENT}")
    app_logger.info(f"Version     : {settings.APP_VERSION}")
    app_logger.info("=" * 70)

    from app.operations.jobs import start_worker, stop_worker
    from app.operations.security import configured_users
    configured_users()
    start_worker()
    try:
        yield
    finally:
        stop_worker()

    app_logger.info("=" * 70)
    app_logger.info("Application shutdown completed")
    app_logger.info("=" * 70)


app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

from app.operations.security import TeamAccessMiddleware
app.add_middleware(TeamAccessMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    api_router,
    prefix=settings.API_PREFIX,
)

register_exception_handlers(app)


@app.get("/", tags=["Root"])
async def root() -> dict[str, str]:
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }

@app.get("/console", include_in_schema=False)
async def local_console():
    from pathlib import Path
    from fastapi.responses import FileResponse
    return FileResponse(Path(__file__).parent / "local_ui" / "index.html")
