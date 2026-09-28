import json
import os
import queue
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from app.main import app
from app.api.routes.kubernetes import container_access as access

ORIGIN = {'origin': 'http://localhost:3000'}
TARGET = {'context': 'test-cluster', 'namespace': 'default', 'pod': 'api', 'uid': 'uid-1', 'container': 'app'}
BASE = '/api/kubernetes/container-access'


@pytest.fixture(autouse=True)
def pod(monkeypatch):
    access._tickets.clear()
    monkeypatch.setattr(access, 'read_pod', lambda *args: {'metadata': {'uid': 'uid-1'}, 'status': {'containerStatuses': [
        {'name': 'app', 'state': {'running': {}}}, {'name': 'stopped', 'state': {'terminated': {}}}]}})
    yield
    access._tickets.clear()


def ticket(client):
    result = client.post(BASE + '/terminal', headers=ORIGIN, json={**TARGET, 'confirmation': 'EXEC test-cluster default/api/app'})
    assert result.status_code == 200, result.text
    return result.json()['ticket']


def test_origin_confirmation_and_target_identity():
    with TestClient(app) as client:
        payload = {**TARGET, 'confirmation': 'wrong'}
        assert client.post(BASE + '/terminal', json=payload).status_code == 403
        assert client.post(BASE + '/terminal', headers={'origin': 'https://evil.example'}, json=payload).status_code == 403
        assert client.post(BASE + '/terminal', headers=ORIGIN, json=payload).status_code == 400
        payload['confirmation'] = 'EXEC test-cluster default/api/app'
        payload['uid'] = 'replaced'
        assert client.post(BASE + '/terminal', headers=ORIGIN, json=payload).status_code == 409
        payload.update(uid='uid-1', shell='/bin/custom')
        assert client.post(BASE + '/terminal', headers=ORIGIN, json=payload).status_code == 422


def test_stopped_container_is_rejected():
    with TestClient(app) as client:
        response = client.post(BASE + '/terminal', headers=ORIGIN, json={**TARGET, 'container': 'stopped', 'confirmation': 'EXEC test-cluster default/api/stopped'})
        assert response.status_code == 409


def test_socket_origin_rejected():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(BASE + '/terminal/ws', headers={'origin': 'https://evil.example'}): pass


class FakeTerminal:
    def __init__(self):
        self.outputs = queue.Queue()
        self.inputs = []
        self.sizes = []
        self.closed = False
    def write(self, data):
        self.inputs.append(data)
        self.outputs.put('received:' + data)
    def read(self):
        try: return self.outputs.get(timeout=0.05)
        except queue.Empty: return None if self.closed else ''
    def resize(self, rows, cols): self.sizes.append((rows, cols))
    def poll(self): return 0 if self.closed else None
    def close(self): self.closed = True


def test_socket_streams_input_output_and_cleans_up(monkeypatch):
    processes, commands = [], []
    def spawn(command, rows, cols):
        commands.append(command)
        p = FakeTerminal()
        p.resize(rows, cols)
        processes.append(p)
        return p
    monkeypatch.setattr(access, 'spawn_terminal', spawn)
    with TestClient(app) as client:
        token = ticket(client)
        with client.websocket_connect(BASE + '/terminal/ws', headers=ORIGIN) as ws:
            ws.send_json({'ticket': token, 'rows': 30, 'cols': 100})
            assert ws.receive_json()['type'] == 'ready'
            ws.send_json({'type': 'resize', 'rows': 40, 'cols': 120})
            raw = 'cd /tmp/\t\t\x1b[A\x03'
            ws.send_json({'type': 'input', 'data': raw})
            frames = [ws.receive_json(), ws.receive_json()]
            assert next(f['data'] for f in frames if f['type'] == 'output') == 'received:' + raw
            assert any(f['type'] == 'input_ack' for f in frames)
            ws.send_json({'type': 'disconnect'})
            with pytest.raises(WebSocketDisconnect): ws.receive_json()
        assert processes[0].closed
        assert processes[0].inputs == [raw]
        assert processes[0].sizes == [(30, 100), (40, 120)]
        assert commands[0] == ['kubectl', '--context', 'test-cluster', '-n', 'default', 'exec', '-t', '-i', 'api', '-c', 'app', '--', '/bin/sh', '-c', 'export TERM=xterm-256color; exec "$0" -i', '/bin/sh']
        with client.websocket_connect(BASE + '/terminal/ws', headers=ORIGIN) as ws:
            ws.send_json({'ticket': token})
            assert ws.receive_json()['type'] == 'error'
        assert len(processes) == 1


def test_expired_ticket_does_not_open_process():
    with TestClient(app) as client:
        token = ticket(client)
        _, target, shell = access._tickets[token]
        access._tickets[token] = (time.monotonic() - 1, target, shell)
        with client.websocket_connect(BASE + '/terminal/ws', headers=ORIGIN) as ws:
            ws.send_json({'ticket': token})
            assert 'expired' in ws.receive_json()['message']


def test_binary_download_and_size_limit(monkeypatch):
    real_popen = subprocess.Popen
    commands = []
    def popen(command, **kwargs):
        commands.append(command)
        return real_popen([sys.executable, '-c', 'import sys;sys.stdout.buffer.write(bytes([0,255,13,10,128]))'], **kwargs)
    monkeypatch.setattr(access.subprocess, 'Popen', popen)
    with TestClient(app) as client:
        response = client.post(BASE + '/download', headers=ORIGIN, json={**TARGET, 'path': '/tmp/a;echo bad'})
        assert response.content == bytes([0,255,13,10,128])
        assert commands[0][-2:] == ['cat', '/tmp/a;echo bad']
        monkeypatch.setattr(access, 'MAX_BYTES', 3)
        assert client.post(BASE + '/download', headers=ORIGIN, json={**TARGET, 'path': '/tmp/file'}).status_code == 413


def test_upload_confirmation_binary_and_overwrite(monkeypatch):
    calls = []
    def run(command, **kwargs):
        calls.append((command, kwargs['stdin'].read()))
        return SimpleNamespace(returncode=0, stderr=b'')
    monkeypatch.setattr(access.subprocess, 'run', run)
    path = '/tmp/file;touch nope'
    data = {'target': json.dumps(TARGET), 'path': path, 'confirmation': 'wrong'}
    content = bytes([0,255,128])
    with TestClient(app) as client:
        assert client.post(BASE + '/upload', headers=ORIGIN, data=data, files={'file': ('a', content)}).status_code == 400
        assert calls == []
        data['confirmation'] = f'UPLOAD test-cluster default/api/app {path}'
        assert client.post(BASE + '/upload', headers=ORIGIN, data=data, files={'file': ('a', content)}).status_code == 200
        assert calls[-1][1] == content
        assert calls[-1][0][-5:] == ['/bin/sh', '-c', 'set -C; cat > "$1"', 'upload', path]
        data['overwrite'] = 'true'
        assert client.post(BASE + '/upload', headers=ORIGIN, data=data, files={'file': ('a', content)}).status_code == 200
        assert calls[-1][0][-3] == 'cat > "$1"'
        monkeypatch.setattr(access, 'MAX_BYTES', 2)
        assert client.post(BASE + '/upload', headers=ORIGIN, data=data, files={'file': ('a', content)}).status_code == 413
        assert len(calls) == 2


@pytest.mark.parametrize('path', ['relative.txt', '/tmp/', '/tmp/../etc/file', '/tmp/a\n'])
def test_invalid_file_paths(path):
    with TestClient(app) as client:
        assert client.post(BASE + '/download', headers=ORIGIN, json={**TARGET, 'path': path}).status_code == 400


def test_idle_expiry_terminates_process(monkeypatch):
    process = FakeTerminal()
    monkeypatch.setattr(access, 'spawn_terminal', lambda *args: process)
    monkeypatch.setattr(access, 'IDLE_SECONDS', 0)
    with TestClient(app) as client:
        token = ticket(client)
        with client.websocket_connect(BASE + '/terminal/ws', headers=ORIGIN) as ws:
            ws.send_json({'ticket': token})
            assert ws.receive_json()['type'] == 'ready'
            assert 'expired' in ws.receive_json()['message']
            with pytest.raises(WebSocketDisconnect): ws.receive_json()
        assert process.closed


def test_target_is_reverified_before_opening_socket(monkeypatch):
    with TestClient(app) as client:
        token = ticket(client)
        monkeypatch.setattr(access, 'read_pod', lambda *args: {'metadata': {'uid': 'new-pod'}})
        with client.websocket_connect(BASE + '/terminal/ws', headers=ORIGIN) as ws:
            ws.send_json({'ticket': token})
            assert 'replaced' in ws.receive_json()['message']


@pytest.mark.skipif(os.name == "nt", reason="POSIX shell behavior is tested on Linux; Windows uses kubectl to run the container shell")
def test_upload_refuses_existing_file_until_overwrite_is_selected(monkeypatch, tmp_path):
    real_run = subprocess.run
    def run(command, **kwargs):
        return real_run(command[command.index('--') + 1:], **kwargs)
    monkeypatch.setattr(access.subprocess, 'run', run)
    path = str(tmp_path / 'file.txt')
    data = {'target': json.dumps(TARGET), 'path': path, 'confirmation': f'UPLOAD test-cluster default/api/app {path}'}
    with TestClient(app) as client:
        assert client.post(BASE + '/upload', headers=ORIGIN, data=data, files={'file': ('a', b'original')}).status_code == 200
        assert client.post(BASE + '/upload', headers=ORIGIN, data=data, files={'file': ('a', b'changed')}).status_code == 400
        assert (tmp_path / 'file.txt').read_bytes() == b'original'
        data['overwrite'] = 'true'
        assert client.post(BASE + '/upload', headers=ORIGIN, data=data, files={'file': ('a', b'changed')}).status_code == 200
        assert (tmp_path / 'file.txt').read_bytes() == b'changed'
