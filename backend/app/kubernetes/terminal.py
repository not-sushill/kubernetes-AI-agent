"""Cross-platform PTY transport for kubectl; all arguments remain an argv list."""
from __future__ import annotations

import codecs
import errno
import os
import signal
import socket
import threading
import time
import subprocess


def dimensions(rows, cols):
    if type(rows) is not int or type(cols) is not int or not (2 <= rows <= 200 and 2 <= cols <= 500):
        raise ValueError('Terminal size must be 2–200 rows and 2–500 columns.')
    return rows, cols


class PosixTerminal:
    def __init__(self, argv: list[str], rows: int, cols: int):
        import pty
        import fcntl
        import termios
        import struct
        rows, cols = dimensions(rows, cols)
        master, slave = pty.openpty()
        self.fd = master
        self.lock = threading.Lock()
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        try:
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
            env = dict(os.environ, TERM='xterm-256color')
            self.process = subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave,
                start_new_session=True, env=env, shell=False)
        except BaseException:
            os.close(master)
            raise
        finally:
            os.close(slave)

    def read(self):
        with self.lock:
            return self._read()

    def _read(self):
        import select
        if not select.select([self.fd], [], [], 0.1)[0]:
            return '' if self.process.poll() is None else None
        try:
            data = os.read(self.fd, 16384)
        except OSError as exc:
            if exc.errno == errno.EIO: return None
            raise
        if not data: return None
        return self.decoder.decode(data)

    def write(self, data: str):
        payload = data.encode('utf-8')
        while payload:
            sent = os.write(self.fd, payload)
            payload = payload[sent:]

    def resize(self, rows: int, cols: int):
        import fcntl
        import termios
        import struct
        rows, cols = dimensions(rows, cols)
        fcntl.ioctl(self.fd, termios.TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
        # kubectl is a session leader without a local controlling terminal;
        # notify it explicitly so it forwards the new size to the remote PTY.
        if self.process.poll() is None:
            try: os.kill(self.process.pid, signal.SIGWINCH)
            except ProcessLookupError: pass

    def poll(self):
        return self.process.poll()

    def close(self):
        try:
            if self.process.poll() is None:
                try: os.killpg(self.process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
            self.process.wait(timeout=5)
        finally:
            with self.lock:
                os.close(self.fd)


class WindowsTerminal:
    def __init__(self, argv: list[str], rows: int, cols: int):
        dimensions(rows, cols)
        try:
            from winpty import PtyProcess
        except ImportError as exc:
            raise RuntimeError('Windows terminal support requires pywinpty. Install backend requirements.txt and restart the backend.') from exc
        # PtyProcess owns the native reader thread. Never put a native read and
        # keyboard writes behind the same lock: a waiting read can starve input.
        self.process = PtyProcess.spawn(argv, dimensions=(rows, cols),
            env=dict(os.environ, TERM='xterm-256color'))
        self.process.fileobj.settimeout(0.1)
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')

    def read(self):
        try:
            data = self.process.fileobj.recv(16384)
        except socket.timeout:
            return '' if self.process.pty.isalive() else None
        except OSError:
            if self.process.closed: return None
            raise
        if not data: return None
        return self.decoder.decode(data)

    def write(self, data: str):
        self.process.write(data)

    def resize(self, rows: int, cols: int):
        self.process.setwinsize(*dimensions(rows, cols))

    def poll(self):
        return self.process.pty.get_exitstatus()

    def close(self):
        # Kill kubectl before releasing the reader socket to unblock the native
        # reader. Avoid isalive() on PtyProcess, which changes its closed flag.
        process = self.process
        try:
            if process.pty.isalive():
                try: os.kill(process.pid, signal.SIGTERM)
                except ProcessLookupError: pass
                deadline = time.monotonic() + 5
                while process.pty.isalive() and time.monotonic() < deadline:
                    time.sleep(0.02)
        finally:
            process.close(force=True)


def spawn_terminal(argv: list[str], rows: int = 24, cols: int = 80):
    return (WindowsTerminal if os.name == 'nt' else PosixTerminal)(argv, rows, cols)
