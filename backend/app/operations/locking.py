"""Cross-platform worker exclusion. A lock file is never deleted or truncated."""
import errno
import os
from pathlib import Path

IS_WINDOWS = os.name == 'nt'


class WorkerFileLock:
    def __init__(self, path):
        self.path = Path(path)
        self.file = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # No append/write-before-lock: on Windows another process may own byte zero.
        fd = os.open(str(self.path), os.O_CREAT | os.O_RDWR, 0o600)
        try:
            handle = os.fdopen(fd, 'r+b', buffering=0)
        except BaseException:
            os.close(fd)
            raise
        try:
            handle.seek(0)
            if IS_WINDOWS:
                import msvcrt
                # Windows permits a region extending beyond EOF, including an empty file.
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            handle.close()
            if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise RuntimeError(
                    f'Operations worker lock is in use: {self.path}. '
                    'Start one backend process for this installation. '
                    'Tests must use their own temporary lock path.'
                ) from exc
            raise
        except BaseException:
            handle.close()
            raise
        self.file = handle
        return self

    def close(self):
        handle, self.file = self.file, None
        if handle is None:
            return
        try:
            handle.seek(0)
            if IS_WINDOWS:
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()
