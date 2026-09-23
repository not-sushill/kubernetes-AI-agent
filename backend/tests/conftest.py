from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from sqlalchemy.orm import close_all_sessions


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

_TEST_DIRECTORY = tempfile.TemporaryDirectory(prefix="k8s-agent-tests-")
os.environ["DATABASE_URL"] = (
    "sqlite:///" + (Path(_TEST_DIRECTORY.name) / "history.db").as_posix()
)
os.environ["AI_DIAGNOSIS_ENABLED"] = "false"


def pytest_unconfigure(config) -> None:
    """Release SQLite handles before deleting the test directory on Windows."""
    close_all_sessions()

    disposed: set[int] = set()
    for module_name in ("app.db.database", "app.database.session"):
        module = sys.modules.get(module_name)
        engine = getattr(module, "engine", None)
        if engine is not None and id(engine) not in disposed:
            engine.dispose()
            disposed.add(id(engine))

    _TEST_DIRECTORY.cleanup()
