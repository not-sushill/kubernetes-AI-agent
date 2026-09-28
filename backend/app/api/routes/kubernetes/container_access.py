"""Local browser container access; explicit context and pod identity for every operation."""
from __future__ import annotations

import asyncio
import anyio
import json
import os
import secrets
import subprocess
import tempfile
import threading
import time
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.kubernetes.terminal import spawn_terminal, dimensions
from app.kubernetes.constants import KUBECTL_BINARY
from app.kubernetes.executor import KubectlExecutor
from app.kubernetes.validators import validate_namespace, validate_pod_name, validate_container_name, validate_context

router = APIRouter(prefix="/container-access", tags=["Container access"])
ORIGINS = {"http://localhost:3000", "http://127.0.0.1:3000"}
MAX_BYTES = 16 * 1024 * 1024
IDLE_SECONDS = 300
SESSION_SECONDS = 3600
_tickets: dict[str, tuple[float, 'Target', str]] = {}
_lock = threading.Lock()
_slots = threading.BoundedSemaphore(4)


def origin_guard(origin: str | None):
    if origin not in ORIGINS:
        raise HTTPException(403, "Container access is restricted to the local frontend origin.")


class Target(BaseModel):
    context: str
    namespace: str
    pod: str
    uid: str
    container: str


class TerminalRequest(Target):
    shell: Literal['/bin/sh', '/bin/bash'] = '/bin/sh'
    confirmation: str


class DownloadRequest(Target):
    path: str


def base_args(target: Target) -> list[str]:
    return ['--context', validate_context(target.context), '-n', validate_namespace(target.namespace)]


def read_pod(context: str, namespace: str, pod: str) -> dict:
    result = KubectlExecutor().execute(['--context', validate_context(context), '-n', validate_namespace(namespace),
        'get', 'pod', validate_pod_name(pod), '-o', 'json'])
    return json.loads(result.stdout)


def verify(target: Target):
    validate_container_name(target.container)
    pod = read_pod(target.context, target.namespace, target.pod)
    if pod.get('metadata', {}).get('uid') != target.uid:
        raise HTTPException(409, 'Pod was replaced. Reload container access and confirm the new target.')
    statuses = pod.get('status', {})
    containers = statuses.get('containerStatuses', []) + statuses.get('initContainerStatuses', []) + statuses.get('ephemeralContainerStatuses', [])
    if not any(c.get('name') == target.container and c.get('state', {}).get('running') is not None for c in containers):
        raise HTTPException(409, 'Selected container is not running. Reload container access.')


def exec_args(target: Target, command: list[str], stdin: bool = False) -> list[str]:
    return [KUBECTL_BINARY, *base_args(target), 'exec', *(['-i'] if stdin else []), validate_pod_name(target.pod),
        '-c', validate_container_name(target.container), '--', *command]


def file_path(value: str) -> str:
    if not value.startswith('/') or value.endswith('/') or any(ord(c) < 32 for c in value) or len(value) > 4096:
        raise HTTPException(400, 'Enter an absolute container file path, such as /tmp/report.txt.')
    if '..' in value.split('/'):
        raise HTTPException(400, 'Use a file path without .. segments.')
    return value


@router.get('/{namespace}/{pod}')
def target_info(namespace: str, pod: str, request: Request):
    origin_guard(request.headers.get('origin'))
    context = KubectlExecutor().execute(['config', 'current-context']).stdout.strip()
    data = read_pod(context, namespace, pod)
    status = data.get('status', {})
    containers = status.get('containerStatuses', []) + status.get('initContainerStatuses', []) + status.get('ephemeralContainerStatuses', [])
    return {'context': context, 'namespace': namespace, 'pod': pod, 'uid': data['metadata']['uid'],
        'containers': [{'name': c['name'], 'running': c.get('state', {}).get('running') is not None} for c in containers]}


@router.post('/terminal')
def terminal_ticket(body: TerminalRequest, request: Request):
    origin_guard(request.headers.get('origin'))
    expected = f'EXEC {body.context} {body.namespace}/{body.pod}/{body.container}'
    if body.confirmation != expected:
        raise HTTPException(400, 'Terminal confirmation does not match the selected target.')
    verify(body)
    token = secrets.token_urlsafe(32)
    with _lock:
        now = time.monotonic()
        for key, value in list(_tickets.items()):
            if value[0] < now: _tickets.pop(key)
        if len(_tickets) >= 128:
            raise HTTPException(429, 'Too many pending terminal requests.')
        _tickets[token] = (now + 30, Target(**body.model_dump()), body.shell)
    return {'ticket': token}


def stop_process(process):
    if process.poll() is None:
        process.kill()
    process.wait(timeout=5)


@router.websocket('/terminal/ws')
async def terminal_socket(ws: WebSocket):
    # Token is sent in the first frame, never in URLs/access logs.
    if ws.headers.get('origin') not in ORIGINS:
        await ws.close(code=1008); return
    await ws.accept()
    process = None
    acquired = False
    tasks = []
    try:
        hello = await asyncio.wait_for(ws.receive_json(), 10)
        token = hello.get('ticket')
        if not isinstance(token, str): raise ValueError('Invalid terminal ticket.')
        with _lock: ticket = _tickets.pop(token, None)
        if not ticket or ticket[0] < time.monotonic(): raise ValueError('Terminal ticket expired. Reconnect and confirm again.')
        acquired = _slots.acquire(blocking=False)
        if not acquired: raise ValueError('Four terminal sessions are already open. Disconnect one first.')
        _, target, shell = ticket
        await asyncio.to_thread(verify, target)
        rows, cols = dimensions(hello.get('rows', 24), hello.get('cols', 80))
        args = exec_args(target, [shell, '-c', 'export TERM=xterm-256color; exec "$0" -i', shell], True)
        args.insert(args.index('exec') + 1, '-t')
        process = await asyncio.to_thread(spawn_terminal, args, rows, cols)
        await ws.send_json({'type': 'ready'})
        started = last_input = time.monotonic()

        async def output():
            while True:
                chunk = await asyncio.to_thread(process.read)
                if chunk is None: break
                if chunk:
                    await ws.send_json({'type': 'output', 'data': chunk})
                else:
                    await asyncio.sleep(0.02)
            await ws.send_json({'type': 'exit', 'code': process.poll()})

        async def input_loop():
            nonlocal last_input
            while True:
                message = await ws.receive_json()
                if message.get('type') == 'disconnect': return
                if message.get('type') == 'resize':
                    rows, cols = dimensions(message.get('rows'), message.get('cols'))
                    await asyncio.to_thread(process.resize, rows, cols)
                    continue
                if message.get('type') != 'input': continue
                data = message.get('data')
                if not isinstance(data, str) or len(data) > 8192: raise ValueError('Input is too large.')
                last_input = time.monotonic()
                await asyncio.to_thread(process.write, data)
                await ws.send_json({"type": "input_ack"})

        async def expiry():
            while True:
                await asyncio.sleep(1)
                now = time.monotonic()
                if now - last_input > IDLE_SECONDS or now - started > SESSION_SECONDS:
                    await ws.send_json({'type': 'error', 'message': 'Session expired after inactivity or the one-hour session limit.'})
                    return

        tasks = [asyncio.create_task(fn()) for fn in (output, input_loop, expiry)]
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done: task.result()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try: await ws.send_json({'type': 'error', 'message': exc.detail if isinstance(exc, HTTPException) else str(exc)})
        except Exception: pass
    finally:
        # Stop readers before killing kubectl, so disconnect cannot emit another exit frame.
        # Shield cleanup when the server cancels a WebSocket handler during shutdown.
        with anyio.CancelScope(shield=True):
            for task in tasks: task.cancel()
            try:
                if process is not None:
                    await asyncio.to_thread(process.close)
                if tasks: await asyncio.gather(*tasks, return_exceptions=True)
            finally:
                if acquired: _slots.release()
            try: await ws.close()
            except RuntimeError: pass


@router.post('/download')
def download(body: DownloadRequest, request: Request):
    origin_guard(request.headers.get('origin'))
    path = file_path(body.path)
    verify(body)
    # No archive extraction: only return bytes from this exact path.
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(exec_args(body, ['cat', path]), stdout=subprocess.PIPE, stderr=errors, shell=False)
        expired = threading.Event()
        def timeout():
            expired.set()
            if process.poll() is None: process.kill()
        timer = threading.Timer(60, timeout)
        timer.start()
        try:
            result = bytearray()
            while len(result) <= MAX_BYTES:
                chunk = process.stdout.read(min(65536, MAX_BYTES + 1 - len(result)))
                if not chunk: break
                result.extend(chunk)
            if len(result) > MAX_BYTES: raise HTTPException(413, 'File exceeds the 16 MiB download limit.')
            process.wait(timeout=5)
            if expired.is_set(): raise HTTPException(504, 'Download timed out.')
            if process.returncode:
                errors.seek(0)
                raise HTTPException(400, errors.read(4096).decode('utf-8', 'replace') or 'Download failed. The container must include cat.')
            return Response(bytes(result), media_type='application/octet-stream')
        finally:
            timer.cancel()
            stop_process(process)
            process.stdout.close()


@router.post('/upload')
def upload(request: Request, target: str = Form(...), path: str = Form(...), confirmation: str = Form(...),
           overwrite: bool = Form(False), file: UploadFile = File(...)):
    origin_guard(request.headers.get('origin'))
    try: body = Target.model_validate_json(target)
    except ValueError as exc: raise HTTPException(400, 'Invalid upload target.') from exc
    path = file_path(path)
    expected = f'UPLOAD {body.context} {body.namespace}/{body.pod}/{body.container} {path}'
    if confirmation != expected: raise HTTPException(400, 'Upload confirmation does not match the destination.')
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size > MAX_BYTES: raise HTTPException(413, 'File exceeds the 16 MiB upload limit.')
    verify(body)
    # User paths are arguments, never interpolated into shell code. Noclobber refuses existing files by default.
    script = 'cat > "$1"' if overwrite else 'set -C; cat > "$1"'
    try:
        result = subprocess.run(exec_args(body, ['/bin/sh', '-c', script, 'upload', path], True),
            stdin=file.file, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60, shell=False)
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(504, 'Upload timed out; destination may be partial. Inspect it before retrying.') from exc
    if result.returncode:
        raise HTTPException(400, result.stderr.decode('utf-8', 'replace')[:4096] or 'Upload failed; destination may be partial. Requires /bin/sh and cat.')
    return {'message': f'Uploaded {size} bytes to {path}.', 'bytes': size}
