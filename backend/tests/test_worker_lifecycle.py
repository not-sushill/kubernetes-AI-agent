import os
import subprocess
import sys
from pathlib import Path
from threading import Event
from types import SimpleNamespace

import pytest

from app.operations import jobs, locking
from app.operations.locking import WorkerFileLock


def test_lock_exclusion_release_and_no_file_growth(tmp_path):
    path = tmp_path / 'worker.lock'
    for _ in range(3):
        first = WorkerFileLock(path).acquire()
        try:
            with pytest.raises(RuntimeError, match='lock is in use'):
                WorkerFileLock(path).acquire()
        finally:
            first.close()
        assert path.stat().st_size == 0
    assert path.exists()  # Never unlink a live lock inode.


def test_windows_locks_and_unlocks_exactly_byte_zero(monkeypatch, tmp_path):
    calls = []
    def locking_call(fd, mode, size):
        calls.append((mode, os.lseek(fd, 0, os.SEEK_CUR), size))
    monkeypatch.setattr(locking, 'IS_WINDOWS', True)
    monkeypatch.setitem(sys.modules, 'msvcrt', SimpleNamespace(locking=locking_call, LK_NBLCK=2, LK_UNLCK=0))
    path = tmp_path / 'windows.lock'
    path.write_bytes(b'existing contents')
    lock = WorkerFileLock(path).acquire()
    lock.close()
    lock.close()
    assert calls == [(2, 0, 1), (0, 0, 1)]
    assert path.read_bytes() == b'existing contents'


def test_test_configuration_isolates_a_held_application_lock(tmp_path):
    production_path = tmp_path / 'live-backend.lock'
    lock = WorkerFileLock(production_path).acquire()
    env = dict(os.environ, OPERATIONS_LOCK_PATH=str(production_path))
    backend = Path(__file__).resolve().parents[1]
    env['PYTHONPATH'] = str(backend)
    code = '''
import os, runpy
original = os.environ['OPERATIONS_LOCK_PATH']
config = runpy.run_path('tests/conftest.py')
assert os.environ['OPERATIONS_LOCK_PATH'] != original
from app.operations.locking import WorkerFileLock
lock = WorkerFileLock(os.environ['OPERATIONS_LOCK_PATH']).acquire()
lock.close()
config['pytest_unconfigure'](None)
'''
    try:
        result = subprocess.run([sys.executable, '-c', code], cwd=backend, env=env, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        with pytest.raises(RuntimeError):
            WorkerFileLock(production_path).acquire()
    finally:
        lock.close()


@pytest.fixture
def isolated_worker(monkeypatch, tmp_path):
    jobs.stop_worker()
    assert jobs.worker is None
    path = tmp_path / 'lifecycle.lock'
    monkeypatch.setenv('OPERATIONS_LOCK_PATH', str(path))
    monkeypatch.setattr(jobs, '_recover_interrupted_jobs', lambda: None)
    monkeypatch.setattr(jobs, 'process_one', lambda: False)
    yield path
    jobs.stop_worker()


def test_repeated_lifespans_release_worker_lock(isolated_worker):
    for _ in range(4):
        jobs.start_worker()
        assert jobs.worker.is_alive()
        jobs.stop_worker()
        assert jobs.worker is None and jobs.worker_lock is None
        WorkerFileLock(isolated_worker).acquire().close()


def test_failed_recovery_releases_lock(monkeypatch, isolated_worker):
    def fail(): raise RuntimeError('recovery failed')
    monkeypatch.setattr(jobs, '_recover_interrupted_jobs', fail)
    with pytest.raises(RuntimeError, match='recovery failed'): jobs.start_worker()
    assert jobs.worker is None and jobs.worker_lock is None
    WorkerFileLock(isolated_worker).acquire().close()


def test_failed_thread_start_releases_lock(monkeypatch, isolated_worker):
    class BrokenThread:
        def __init__(self, **kwargs): pass
        def start(self): raise RuntimeError('thread failed')
    monkeypatch.setattr(jobs, 'Thread', BrokenThread)
    with pytest.raises(RuntimeError, match='thread failed'): jobs.start_worker()
    WorkerFileLock(isolated_worker).acquire().close()


def test_stopping_worker_retains_exclusion_until_job_exits(monkeypatch, isolated_worker):
    entered, release = Event(), Event()
    def process():
        entered.set()
        release.wait(timeout=5)
        return True
    monkeypatch.setattr(jobs, 'process_one', process)
    try:
        jobs.start_worker()
        assert entered.wait(timeout=2)
        jobs.stop_worker(timeout=0.01)
        with pytest.raises(RuntimeError, match='shutting down'): jobs.start_worker()
        with pytest.raises(RuntimeError, match='lock is in use'): WorkerFileLock(isolated_worker).acquire()
    finally:
        release.set()
        jobs.stop_worker()
    WorkerFileLock(isolated_worker).acquire().close()
