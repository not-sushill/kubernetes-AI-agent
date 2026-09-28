# Interactive container terminal upgrade

This version replaces the line-based console with xterm.js and a real PTY behind
kubectl exec -it. It preserves container selection, context/UID checks, typed
confirmation, idle limits, and upload/download controls.

## Install on Windows

Stop both servers and extract this ZIP into D:\projects\ai-kubernetes-agent.
The ZIP includes backend/ and frontend/ source, not .env, databases, backups or
Git metadata. Dependencies changed; install both before restarting.

Backend terminal:

```powershell
Set-Location D:\projects\ai-kubernetes-agent\backend
& D:\projects\.venv\Scripts\python.exe -m pip install -r requirements.txt
& D:\projects\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend terminal:

```powershell
Set-Location D:\projects\ai-kubernetes-agent\frontend
npm ci
npm run dev
```

New dependencies: @xterm/xterm 5.5.0 and @xterm/addon-fit 0.10.0, with a committed
npm lockfile; pywinpty 2.0.15 on Windows only. The Windows wheel is available for
the project's Python 3.12. Linux uses its native PTY support.
Use a single backend worker because short-lived session tickets are in memory.

## Use

1. Open http://localhost:3000/pods and select a running pod.
2. In Container terminal and files, choose the running container.
3. Select /bin/bash if it is installed and you want Bash completion. /bin/sh is
   also available, but its completion/history features depend on the implementation.
4. Open terminal and type the exact target confirmation. Confirm enables only on
   an exact match.
5. Click inside the terminal. Type `cd /t` then Tab. Try double Tab to list matches,
   arrow keys for history, and Ctrl+C to interrupt a foreground command.
6. Resize the browser; terminal size updates are sent to Kubernetes.
7. Shift+Escape moves focus out of the terminal, then Tab can navigate the page.

Shell commands execute with your Kubernetes permissions. Full-screen programs
work only if installed in the container. Nothing is installed inside containers.
TERM is set to xterm-256color in the remote shell. No host shell is used to build
the kubectl command.

## Session and file-transfer behavior

- Four concurrent sessions maximum; 5-minute input idle timeout and 1-hour session limit.
- Leaving the page, selecting another pod or clicking Disconnect closes the session.
- Disconnect does not undo changes or guarantee detached remote processes stop.
- Terminal scrollback retains 3,000 lines locally in the browser.
- Upload/download are single-file transfers up to 16 MiB. Existing files are
  refused by default; explicitly select Allow overwrite to replace one.
- Download requires cat; upload requires /bin/sh and cat. Destination directories
  must already exist. A failed upload may leave a partial destination file.
- The tool stays local. Origin checks and typed confirmation are not authentication.
  Do not expose a shared remote shell service without authentication/authorization.
- Terminal command content is not saved to investigation history or app logs.
- Earlier confidence percentage fix is included.

## Verification

144 backend tests and 17 frontend tests pass on Linux; the production frontend
build passes with three pre-existing unused import warnings.
A real Linux PTY test checks isatty, raw Tab/arrow/Ctrl+C bytes, dimensions and exit
cleanup. Windows adapter calls are checked with a test double and against the
pinned package API. Native Windows + kubectl + EKS must still be checked on your
machine. On Windows, the two POSIX-only tests are skipped.

```powershell
# In backend/
& D:\projects\.venv\Scripts\python.exe -m pytest tests -q
# In frontend/
node --test tests/*.cjs
npm run build
```

Live acceptance: check `tty`, `echo $TERM`, path completion in Bash, Up/Down,
Ctrl+C during `sleep 10`, and `stty size` before/after resizing. Then Disconnect.
A missing Bash executable means choose /bin/sh or another image with Bash;
it is not automatically installed. Preserve Git changes by reviewing git diff
before committing. This ZIP does not change your remote or push code.

## Windows input and focus correction

Windows now uses PtyProcess with a separate output reader, so waiting for output
does not hold a lock needed by keyboard writes. The UI synchronizes input enablement
with connection state and includes a Focus terminal button.

After updating, stop and restart BOTH servers, refresh the browser, open a new
terminal, click Focus terminal and type `pwd` followed by Enter.
The input indicator helps isolate remaining issues:
- No input sent: the browser has not sent a keystroke; click Focus terminal.
- Input sent; waiting for PTY acknowledgement: backend delivery is pending.
- Input accepted by PTY: the backend adapter accepted input; this does not confirm
  that the container executed a command.

Tests cover input enablement/focus and concurrent Windows reader/writer behavior
with a test double. Native Windows execution remains to be verified locally.
