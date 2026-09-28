# Operations release

Read OPERATIONS_GUIDE.md for the feature map and optional integration setup.

## Update the working local installation

1. Stop both servers and back up any newer source edits.
2. Extract this ZIP into D:\projects\ai-kubernetes-agent.
3. Keep your existing .env, database and backup files.
4. Start backend:

```powershell
Set-Location D:\projects\ai-kubernetes-agent\backend
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

5. In a second terminal:

```powershell
Set-Location D:\projects\ai-kubernetes-agent\frontend
if (Test-Path .next) { Remove-Item .next -Recurse -Force }
npm run dev
```

6. Ctrl+F5 in localhost:3000. Open Operations, or use Queue next to a pod investigation.

This package preserves the prior working UI and adds Operations. It does not include installed dependencies, credentials, databases, or archived logs. On a fresh machine, install backend/requirements.txt and run npm ci in frontend first. The backend still requires kubectl, your configured kubeconfig/AWS authentication and Ollama for AI. Docker packaging remains a separate phase.

Validation: 231 backend tests pass on Linux after the worker lock correction. Windows lock/unlock calls are covered with a simulated Windows API. The unchanged frontend previously passed 30 tests, production build and TypeScript checks. Live EKS, Loki, webhook and Windows integrations need acceptance checks on your installation; none were exercised against your cluster here.

## Worker lock correction

Tests now use a temporary database AND temporary worker lock, so they can run while the local backend is running. Worker startup failures and shutdown release ownership correctly; a job still shutting down retains its lock. The database compatibility import no longer depends on import order. Single-worker protection remains enabled for the real backend.

After extracting the updated source, run:

```powershell
Set-Location D:\projects\ai-kubernetes-agent\backend
& D:\projects\.venv\Scripts\python.exe -m pytest tests -q
```

Do not delete the worker lock or change the running backend's lock path to bypass exclusion. If the backend itself reports lock contention, ensure only one backend process is running. Two native terminal tests may be skipped on Windows.

## AI evidence correction

When no deterministic root cause is established, the backend skips Ollama and returns an explicit insufficient-evidence summary. It does not show speculative CPU, network, Pending-pod or latency claims. Confidence zero is unassigned root-cause confidence, not a health score. Existing history is preserved; create a new investigation after restarting the backend. Regression validation: 233 backend tests pass on Linux.
