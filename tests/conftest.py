"""
Module-scoped DB isolation for the backend test suite.

Each test module (file) gets its own named in-memory SQLite database so that
state written by one module's tests cannot bleed into another module's tests.
The fixture is autouse so no test file needs to import or request it.

test_notification_service.py and test_fueliq_service.py use sqlite3.connect(":memory:")
directly and are already isolated — the fixture runs for them too but they ignore
the named DB, which is harmless.
"""
import itertools
from unittest.mock import MagicMock

import pytest

from api import database as _dbmod
from api.services.db_migrations import run_all
from db.setup import init_db  # opens _persistent_memory_conn as the module-DB keepalive


@pytest.fixture(autouse=True, scope="session")
def _disable_scheduler_thread():
    """
    Prevent APScheduler's background daemon thread from starting during the
    test suite.  The scheduler's add_job/modify_job still work (in-memory job
    store), but no jobs ever execute because the daemon thread never starts.

    Without this, configure_calendar_sync_startup() fires an immediate
    calendar-sync catchup job via a background thread every time a test module
    creates a fresh TestClient with an empty DB.  That background write races
    with the main-thread test writes on the shared-cache named in-memory DB
    and causes intermittent SQLITE_LOCKED errors.

    Some test fixtures call _wipe() which deletes every table row (including
    scheduler_heartbeats), so pre-seeding the heartbeat row is not enough —
    the only reliable fix is to prevent the scheduler thread from ever running.
    """
    import api.main as _main
    _main._scheduler.start = MagicMock(return_value=None)


_counter = itertools.count(1)


@pytest.fixture(autouse=True, scope="module")
def _fresh_db():
    n = next(_counter)
    _dbmod._test_db_uri = f"file:testdb_{n}?mode=memory&cache=shared"
    # init_db() opens _persistent_memory_conn to this URI, which is the
    # keepalive that prevents the named in-memory DB from being destroyed.
    # No separate keepalive connection is needed here — a 3rd idle connection
    # on the same shared-cache DB triggers SQLITE_LOCKED under test writes.
    init_db()
    run_all()
    yield
    _dbmod._test_db_uri = None
    # _persistent_memory_conn stays open; the next module's init_db() will
    # detect the URI change and recycle it onto a fresh testdb.
