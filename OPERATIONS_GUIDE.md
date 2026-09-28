# Operations release — cumulative local source

This archive contains the complete backend and frontend source from the working UI release plus the features below. Existing terminal, log viewer, IST display, sorting, pagination, investigation history, typed approvals, backup and rollback flows are preserved.

## What is included

| Feature | Where to use it | Exact scope |
|---|---|---|
| Historical logs | Operations → Archive | Read an existing Loki archive using cluster/namespace/pod selectors, IST start/end times, literal text search, highlights and paginated results. |
| Incident timeline | Investigation → Timeline link | Saved creation times, condition transitions, terminations, retained events, timestamped error/warning log matches and recorded fix operations. No guessed timestamps or causal links. |
| AI follow-up checks | Existing AI assessment | Suggested check IDs from evidence-backed hypotheses are prioritized. Run checks, then reassess using fresh results. Model text is never executed as shell commands. |
| Post-fix verification | Operations → Changes → Verify live health | Operator-triggered, read-only comparison of approved spec/UID, rollout, owned pod readiness, matching endpoint readiness and a recent log sample. Results persist separately. No automatic rollback. |
| Background investigations | Queue button or Operations → Jobs | Persistent queued/running/completed jobs with saved cluster context. Browser navigation does not cancel the backend job. |
| Change comparison | Operations → Changes | Before/proposed editable-field diffs and operation history for recorded AI proposals. Existing Deployment YAML backups remain on the Deployment page. |
| Resource relationships | Operations → Relationships | Browse ownership, Ingress routing, Service selectors and Pod→Node placement. Node health is not inferred. |
| Saved runbooks | Operations → Runbooks | Built-in image-pull, readiness, OOM and database-triage check sequences. Save named combinations of approved checks; no arbitrary commands. Database runbooks do not query the database or change grants. |
| Alert inbox + webhook | Operations → Alerts | High/critical findings from new investigations, recent recurrence count, acknowledge and explicit Send notification. No continuous cluster monitoring or automatic delivery. |
| Optional access + audit | Access menu; Operations → Audit | Named per-user API tokens, viewer/operator/approver/admin permissions, and API mutation audit records. Existing typed confirmation is still required. |

## Install

1. Commit/back up newer local source edits. Stop both frontend and backend servers.
2. Extract this ZIP into `D:\projects\ai-kubernetes-agent`, replacing source files. Do not delete your existing `.env`, database, or Deployment backup directory.
3. Start the backend from its backend directory using your existing virtual environment and start command. New database tables are created automatically; existing investigation records are retained. Run exactly one backend process/worker. A lock prevents a second Operations worker from running against the same local installation.
4. In PowerShell:

```powershell
Set-Location D:\projects\ai-kubernetes-agent\frontend
if (Test-Path .next) { Remove-Item .next -Recurse -Force }
npm run dev
```

5. Refresh localhost:3000 with Ctrl+F5. Open Operations.

No new runtime packages are required beyond this project's existing dependencies. Source and example configuration are included; secrets, installed dependencies, build outputs and local databases are excluded.

## Queue and recovery behavior

- Queue captures the currently selected context; Operations also lets you choose it explicitly.
- Queue persists request and actor before any collection starts. One local worker handles jobs serially; at most 100 jobs may be queued/running.
- UI progress is stage-based: Queued, Collecting evidence, Analyzing evidence, Finished. No fabricated percentage.
- Closing the browser does not interrupt collection. Return to Operations → Jobs to open the saved investigation.
- On backend restart, queued jobs resume and previously running jobs become INTERRUPTED. Queue a fresh investigation; interrupted jobs are never automatically repeated.
- Existing Investigate buttons retain their synchronous behavior. Use the new Queue button for durable background work.
- This is a single-process local queue, not a distributed scheduler. Docker/multi-host operation is a separate validation phase.

## Historical logs: external setup required

The archive integration needs Loki already receiving your cluster's logs. A local application cannot recover logs that rotated before a collector saved them.

Configure backend/.env (use your actual URL and label values):

```dotenv
LOKI_URL=https://your-loki-query-endpoint
LOKI_TOKEN=
LOKI_TENANT=
LOKI_LABEL_CLUSTER=cluster
LOKI_LABEL_NAMESPACE=namespace
LOKI_LABEL_POD=pod
LOKI_LABEL_CONTAINER=container
```

The Cluster input must match the value stored in your archive's cluster label. If your collector uses a friendly cluster name instead of the kubeconfig context name, enter that archive value in the Archive cluster label field. Configure alternate label *names* using LOKI_LABEL_*.

Queries use Loki's `/loki/api/v1/query_range`, with exact JSON-escaped labels and literal text filtering. Time windows are limited to 7 days, 5000 result lines and an 8 MB response. Limit reached means earlier/later matching lines may still exist; narrow the time range. TLS verification is enabled. Credentials and tenant headers stay on the backend. This release does not install a cluster log collector or provision archive storage.

Reference: https://grafana.com/docs/loki/latest/reference/loki-http-api/

## Alert delivery

New high/critical findings create inbox entries after an investigation is saved. This is not a continuous monitoring service. Recurrence count is scoped to the most recent 100 inbox records and includes cluster identity.

Set `ALERT_WEBHOOK_URL` to an HTTPS receiver you control. Set `CONSOLE_URL` to the URL recipients can reach. Then choose Send notification. No test messages or notifications are sent by installing this release.

Payload is generic JSON containing title, severity, namespace, resource, investigation_id and a console URL. Use an adapter for providers requiring a different message schema. No raw logs, YAML or credentials are included. Acknowledgement records review only; it does not assert the incident is resolved. Successful delivery is marked DELIVERED. Timeout/failure is marked DELIVERY_UNKNOWN and blocked from resending; inspect the receiver to avoid duplicate alerts. Redirects are not followed.

## Optional team tokens

Default `TEAM_USERS_JSON=[]` retains the existing trusted-local mode. Do not expose that mode on a public network.

Generate a user token:

```powershell
Set-Location D:\projects\ai-kubernetes-agent\backend
& D:\projects\.venv\Scripts\python.exe .\scripts\create-team-user.py operator1 --role operator
```

Create an admin entry as well. Combine the printed JSON entries into a list in backend/.env:

```dotenv
TEAM_USERS_JSON='[{"name":"operator1","role":"operator","token_sha256":"YOUR_GENERATED_64_CHARACTER_HASH"},{"name":"admin1","role":"admin","token_sha256":"YOUR_OTHER_GENERATED_HASH"}]'
```

Restart the backend. Each user enters their *token*, not hash, through Access. Token hashes remain backend-side. Tokens are stored in browser sessionStorage per tab and sent as X-API-Key headers, never URLs. New tabs may require signing in again. Sign out clears the tab token and cached data. Rotate/revoke tokens by editing the configured users and restarting. Terminal tickets remain single-use and short-lived; terminal session content is not recorded in audit.

| Role | Permissions |
|---|---|
| Viewer | Read inventory, history, reports and saved results. |
| Operator | Viewer plus investigations, archive searches, assessments, dry-run validation, approved read-only diagnostics, runbooks, verification, alert acknowledgement/delivery and file downloads. |
| Approver | Operator plus approved apply/restore/rollback, file uploads and terminal creation. Typed approvals still apply. |
| Admin | Approver plus shared context switching and API audit access. |

Unrecognized write routes require approver. Roles are application-wide, not per namespace. All users share the backend Kubernetes identity. This is local token access, not SSO, multi-tenancy or a replacement for Kubernetes RBAC. Existing local-origin restrictions remain. HTTP mutations are audited with actor, route, method, status and time; request bodies, token values and terminal keystrokes are excluded.

## Verification semantics

Checks are bounded to 75 seconds and persisted even when incomplete. CHECKS_PASSED means sampled checks passed at that time, not that every application path is healthy. NEEDS_REVIEW includes failed/empty log checks or scaled-to-zero deployments. INCOMPLETE includes collection failures or configuration drift. Inspect limitations, compare the original evidence, and test legitimate application traffic before closing an incident. No automatic fixes, retries or rollbacks occur from verification.

## Validation and remaining environment checks

Validation: 224 backend tests and 30 frontend tests passed; Next.js production build and TypeScript checks passed. Tests simulate Kubernetes, Loki and notification receivers; they do not prove connectivity to your EKS cluster or collector. Live Windows terminal, actual archive retention, webhook delivery, team-token login and a controlled approved fix must be checked on your installation. Docker execution has not yet been validated.

Suggested local acceptance sequence:
1. Queue a pod investigation; navigate away, refresh, and reopen the completed job.
2. Open Timeline and Relationships for the same namespace.
3. Run a saved runbook from an assessment; reassess with its results.
4. Verify a previously approved fix and inspect stored check results.
5. Configure Loki and search a known historical event using IST times.
6. Configure test team users; confirm a viewer cannot apply or open a terminal.
7. Configure a test webhook and explicitly send one inbox alert.
