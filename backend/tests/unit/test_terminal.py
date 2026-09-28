import json
import os
import sys
import time
from types import SimpleNamespace

import pytest
from app.kubernetes.terminal import PosixTerminal, WindowsTerminal, dimensions


@pytest.mark.parametrize('rows,cols', [(0, 80), (24, 0), (201, 80), (24, 501), ('24', 80), (True, 80)])
def test_terminal_rejects_invalid_dimensions(rows, cols):
    with pytest.raises(ValueError): dimensions(rows, cols)


@pytest.mark.skipif(os.name == 'nt', reason='POSIX PTY test')
def test_posix_pty_is_tty_and_delivers_raw_keys_and_resize():
    script = '''import os,sys,tty,json,time
print('TTY:' + str(os.isatty(0)),flush=True)
tty.setraw(0)
print('READY',flush=True)
data=os.read(0,100)
size=os.get_terminal_size(0)
print(json.dumps({'bytes':list(data),'rows':size.lines,'cols':size.columns}),flush=True)
time.sleep(10)
'''
    terminal = PosixTerminal([sys.executable, '-u', '-c', script], 24, 80)
    def until(marker):
        output = ''
        deadline = time.monotonic() + 5
        while marker not in output and time.monotonic() < deadline:
            data = terminal.read()
            if data is None: break
            output += data
        assert marker in output, output
        return output
    try:
        assert 'TTY:True' in until('READY')
        terminal.resize(35, 110)
        terminal.write('\t\t\x1b[A\x03')
        output = until('}')
        payload = json.loads(output[output.index('{'):output.index('}')+1])
        assert payload == {'bytes':[9,9,27,91,65,3], 'rows':35, 'cols':110}
    finally: terminal.close()
    assert terminal.process.poll() is not None


def test_windows_reader_does_not_block_keyboard_writes(monkeypatch):
    import threading
    from app.kubernetes import terminal as module
    reading, written = threading.Event(), threading.Event()
    calls = []
    class Socket:
        def settimeout(self, value): calls.append(('timeout', value))
        def recv(self, size):
            reading.set()
            assert written.wait(1), 'Read blocked keyboard writes'
            return b'shell>'
    class Process:
        def __init__(self):
            self.fileobj=Socket();self.pty=self;self.closed=False;self.alive=True;self.pid=123
        def isalive(self): return self.alive
        def get_exitstatus(self): return None if self.alive else 0
        def write(self, data): calls.append(('write', data));written.set()
        def setwinsize(self, rows, cols): calls.append(('resize', rows, cols))
        def close(self, force): self.closed=True;calls.append(('close',force))
    process=Process()
    def spawn(argv, **kwargs): calls.append(('spawn',argv,kwargs));return process
    monkeypatch.setitem(sys.modules,'winpty',SimpleNamespace(PtyProcess=SimpleNamespace(spawn=spawn)))
    monkeypatch.setattr(module.os,'kill',lambda pid,sig:setattr(process,'alive',False))
    argv=['kubectl','--context','cluster name','exec','-it','pod','--','/bin/bash']
    terminal=WindowsTerminal(argv,24,80)
    output=[]
    reader=threading.Thread(target=lambda:output.append(terminal.read()))
    reader.start()
    assert reading.wait(1)
    terminal.write('\t\x03')
    reader.join(2)
    assert not reader.is_alive()
    assert output==['shell>']
    terminal.resize(30,100)
    terminal.close()
    assert ('write','\t\x03') in calls
    assert ('resize',30,100) in calls
    assert calls[0][1] == argv
    assert process.closed
