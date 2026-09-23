from pathlib import Path
import sys

from loguru import logger

from app.core.config import settings


LOG_PATH = Path(settings.LOG_DIRECTORY)

LOG_PATH.mkdir(
    parents=True,
    exist_ok=True,
)

logger.remove()

logger.add(
    sys.stdout,
    level=settings.LOG_LEVEL,
    colorize=True,
    enqueue=True,
    backtrace=True,
    diagnose=True,
)

logger.add(
    LOG_PATH / "application.log",
    level=settings.LOG_LEVEL,
    rotation=settings.LOG_ROTATION,
    retention=settings.LOG_RETENTION,
    enqueue=True,
    backtrace=True,
    diagnose=False,
)

app_logger = logger
