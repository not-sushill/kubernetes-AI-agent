# Latest local release

See LOCAL_QUICKSTART.md for the console and startup script. Current offline suite: 103 tests. The notes below retain earlier backend installation history.

# Local backend update

This package contains the complete backend source based on your uploaded project, plus regression tests and a PowerShell test sequence. A local browser console is now included at /console; deployment work is outside this release.

## Replace the source once

1. Stop the running backend with Ctrl+C.
2. Back up your current backend folder.
3. Extract this ZIP into `D:\projects\ai-kubernetes-agent`, allowing its `backend` folder to merge with yours and replacing matching source files.
4. Keep your existing `.env`, `.venv`, SQLite database, logs and investigation data. They are not included in this package. Your existing `DATABASE_URL` remains supported. The default database location, if unset, is `backend/ai_kubernetes_agent.db`.

From PowerShell:

```powershell
Set-Location D:\projects\ai-kubernetes-agent\backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-local.ps1
```

For a fresh installation only, create a Python 3.12 virtual environment with `py -3.12 -m venv .venv`, activate it, and copy `.env.example` to `.env`. Do not overwrite an existing `.env`.

## Start and run live checks

Your `.env` should retain:

```dotenv
AI_DIAGNOSIS_ENABLED=true
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma3:4b
```

Start Ollama as usual and ensure `gemma3:4b` is installed. Confirm `kubectl config current-context` identifies the intended cluster, then start the backend:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

In a second PowerShell window, activate the environment and run:

```powershell
Set-Location D:\projects\ai-kubernetes-agent\backend
.\.venv\Scripts\Activate.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-local.ps1 -Live -Namespace default
```

The script reruns offline regression, checks the running API and Ollama, and submits namespace, pod, deployment and Service investigations using existing resources. It checks stored results/history and AI severity/confidence preservation. It lists the current Kubernetes context, and never creates, edits or deletes cluster resources. If a resource type is absent, its live test is explicitly skipped. A healthy selected pod does not verify a live OOM incident: use an existing affected pod when testing that path.

To choose exact resources, add `-PodName`, `-DeploymentName`, and `-ServiceName`, with their actual names in the selected namespace. No source edits are required between tests. CPU-only Ollama requests may take several minutes each. PARTIAL means some evidence could not be collected; inspect evidence errors and AI limitations. It does not mean the workload itself is partially healthy. COMPLETED refers to collection, not workload health.

API documentation: [Swagger UI](http://localhost:8000/docs)

## Included functionality

- Current and previous OOMKilled detection for regular and init containers, preserving source, timestamps and exit-code evidence. Exit code 137 alone is not classified as OOMKilled.
- Pending symptoms distinguished from FailedScheduling/Unschedulable evidence. Scheduling gates are not reported as scheduler failures.
- Node pressure/utilization and namespace quota capacity findings; application memory exhaustion is distinguished from Kubernetes OOMKilled.
- Deployment rollout failure and replica availability, respecting scaled-to-zero, paused and unobserved generations.
- Service investigations, selector matching, named targetPort resolution and ready EndpointSlices. ExternalName and selectorless Services are handled separately; missing permissions do not imply missing endpoints. Numeric target ports are not declared invalid merely because a containerPort declaration is absent.
- Separate readiness, liveness and startup probe findings. DNS variants, connection refusals, timeouts, network sandbox and routing errors use collected evidence.
- Existing build/TypeScript, image pull, configuration parsing, HTTP, storage and application diagnostics retained. Container configuration failures are distinguished from configuration syntax failures.
- Full pod metadata/status, init containers, deployment ownership/selector scope, related events, current/previous logs, PVCs, metrics, EndpointSlices, NetworkPolicies and quotas collected via kubectl. Logs are limited to 10 related pods per investigation with an explicit limitation when truncated; unhealthy pods are prioritized.
- Findings remain associated with their pod so unrelated workloads do not suppress each other's causes.
- Existing API routes and SQLite history preserved; `service` added to resource_type. Target validation, pagination and database error handling are included.
- Ollama failures and malformed responses fall back to deterministic results. Deterministic root-cause titles, evidence, severity and confidence are enforced. AI-generated narrative and suggestions remain model output, not independently verified facts.

A NetworkPolicy's presence is not proof that it blocked a specific connection. Policies are collected as context; this version does not execute traffic probes or automatically apply recommendations. A previous OOM is reported as historical termination evidence even if the container has since restarted successfully. Its inclusion does not establish an ongoing memory leak.

## Verification

The supplied test suite runs without Kubernetes or Ollama. It uses fixtures/mocked boundaries for detectors, collection scoping, AI failure/enforcement, request validation, API persistence and SQLite reopen checks. Tests use a temporary database and force AI off except where deliberately mocked.

The included Windows PowerShell live script must be run on your machine. Live Kubernetes access, local model inference and your particular Windows environment cannot be verified from this package-building environment. Run the browser acceptance steps in LOCAL_QUICKSTART.md after the live checks.

Kubernetes semantics referenced:
- [EndpointSlices](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
- [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

## Live-test corrections included

This revision includes the Windows SQLite test-cleanup fix and the context_manager import fix. Missing, empty or object-valued AI summaries trigger one retry with reduced evidence; a second invalid response produces an explicit deterministic fallback. Previous logs are skipped when collected container status reports zero restarts and no previous termination. Other log failures and the 10-pod limit remain visible as limitations.

The offline suite now contains 90 tests. Rerun the live script after restarting the backend. Historical OOM records do not prove current resource exhaustion, and HTTP 401 responses alone do not prove broken authentication configuration. Review timestamps and the current workload state before taking action.

## CPU AI performance update

AI generates only a short explanation; Python retains the complete deterministic
findings, severity, confidence and recommendations. The prompt samples up to
5,500 characters of findings (two short evidence lines per finding); raw cluster
inventory is excluded. Omitted findings are disclosed. Generation is limited to
256 tokens with a 60-second HTTP timeout per call. Invalid output gets at most
one retry; transport failures immediately return explicit deterministic fallback.
HTTP timeouts are not a strict whole-investigation deadline. Evidence collection
still takes time and interrupting a caller may not cancel server-side work.

HTTP 401 responses are informational observations, not proof of an authentication
outage. Explicit authentication-failure log patterns remain warnings. AI severity
now retains the enum type during serialization.

After merging this backend folder, restart Uvicorn with AI enabled and run:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\test-local.ps1 -Live -Namespace default -ResourceType deployment -DeploymentName apache-basic-auth
```
Offline expectation: 95 tests. This update was tested with mocked Ollama and
Kubernetes calls; live latency and model quality must be verified on your machine.
AI prose is interpretation, not independently verified evidence.
