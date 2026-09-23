# Local console release

Merge this archive's backend directory into your existing project; preserve your
environment and database. This is a local application, not a production deployment.

## Start

In PowerShell from D:\projects\ai-kubernetes-agent\backend:

```powershell
& D:\projects\.venv\Scripts\python.exe -m pytest tests -q
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-local.ps1
```

Expect 110 tests to pass. The startup script prints the current Kubernetes context.
Open http://127.0.0.1:8000/console. No Node installation or second UI process is needed.
Use -WithoutAI on the startup script to run deterministic investigations only.
Use -Python to supply another environment's python.exe.

## Use

Start with deployment/apache-basic-auth in namespace default. The UI shows elapsed
time, recorded evidence, deterministic findings, AI interpretation and limitations.
History is paginated and searchable; select an entry to reopen it. Export JSON
downloads the full investigation including logs.

COMPLETED means collection completed; it does not imply the workload is healthy.
PARTIAL indicates missing evidence or collection limits. AI fallback is explicitly
described in the explanation/limitations. Findings and confidence are rule-based,
not statistically calibrated probabilities.

The UI has no percentage progress or cancellation claim: the API is synchronous.
Closing a tab can leave server-side work running. If a request disconnects, inspect
history before submitting again. Namespace requests take longer; related log
collection is capped at ten pods and discloses omitted coverage.

## Final local acceptance

1. Open the console, run a focused investigation, inspect findings and evidence.
2. Reopen it from history and export JSON.
3. Stop/restart the backend; confirm the history remains available.
4. Optionally exercise namespace, pod, deployment and service live checks:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-local.ps1 -Live -Namespace default
```
That command submits multiple investigations and takes longer. Existing resources
only; the test does not create or modify workloads.

Backend tests use mock Kubernetes/Ollama boundaries. Your earlier 39.66-second
deployment run verifies the previous CPU optimization on your machine; this
release still needs your browser/live acceptance. AI summary prose is not
independently verified. Local model output quality and latency vary.

## Correlation correction

Probe events no longer create duplicate remote-dependency or authorization causes. Independent application errors remain detectable. Previous-state OOM findings are labeled historical; severity is retained and does not establish current impact. Existing stored investigations are snapshots: run a new investigation to see corrected results.

Timeout findings require failure evidence. Logging a configured timeout value alone is not a failure. Existing history is unchanged; new investigations use this correction.
