from __future__ import annotations

import os

from app.core.logging import app_logger


class ReadOnlyMode:
    """
    Global Read Only controller.

    When enabled every write operation
    must be blocked by the API layer.
    """

    ENV_NAME = "READ_ONLY_MODE"

    @classmethod
    def enabled(cls) -> bool:
        value = os.getenv(
            cls.ENV_NAME,
            "true",
        )

        return value.lower() in (
            "1",
            "true",
            "yes",
            "on",
        )

    @classmethod
    def ensure_write_allowed(cls) -> None:

        if cls.enabled():

            app_logger.warning(
                "Write operation blocked because "
                "READ_ONLY_MODE is enabled."
            )

            raise PermissionError(
                "Cluster is running in Read Only Mode."
            )