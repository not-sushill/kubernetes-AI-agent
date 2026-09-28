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
# Tests must never contend with a running local application's worker or use
# its integrations. Set this BEFORE app/settings modules are imported.
os.environ["OPERATIONS_LOCK_PATH"] = str(Path(_TEST_DIRECTORY.name) / "operations-worker.lock")
os.environ["AI_DIAGNOSIS_ENABLED"] = "false"
os.environ["TEAM_USERS_JSON"] = "[]"
os.environ["LOKI_URL"] = ""
os.environ["LOKI_TOKEN"] = ""
os.environ["ALERT_WEBHOOK_URL"] = ""


def pytest_unconfigure(config) -> None:
    """Release SQLite handles before deleting the test directory on Windows."""
    jobs = sys.modules.get("app.operations.jobs")
    if jobs is not None:
        jobs.stop_worker()
    close_all_sessions()

    disposed: set[int] = set()
    for module_name in ("app.db.database", "app.database.session"):
        module = sys.modules.get(module_name)
        engine = getattr(module, "engine", None)
        if engine is not None and id(engine) not in disposed:
            engine.dispose()
            disposed.add(id(engine))

    _TEST_DIRECTORY.cleanup()
