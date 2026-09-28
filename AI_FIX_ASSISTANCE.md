# AI fix assistance — local release

## Install

This cumulative ZIP includes backend/ and frontend/ source, including the working
Windows container terminal. It excludes .env, databases, node_modules, virtual
environments, backup data and Git metadata. Review your local Git diff before
replacing source if you have additional edits.

1. Stop the backend and frontend.
2. Extract into D:\projects\ai-kubernetes-agent, replacing source files.
3. Restart with the same Python environment and database configuration as before.

Backend PowerShell:

```powershell
Set-Location D:\projects\ai-kubernetes-agent\backend
& D:\projects\.venv\Scripts\python.exe -m pip install -r requirements.txt
& D:\projects\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend, in a separate PowerShell terminal:

```powershell
Set-Location D:\projects\ai-kubernetes-agent\frontend
npm ci
npm run dev
```

Refresh localhost:3000 using Ctrl+F5. On backend startup, the existing create_all
initialization adds the fix_proposals table without removing investigation data.
Keep the existing database: proposals, approvals and recovery snapshots live there.
The new feature uses your existing OLLAMA_BASE_URL and OLLAMA_MODEL configuration.
Generation explicitly requested from this panel works independently of the automatic
AI_DIAGNOSIS_ENABLED setting. It uses one bounded JSON generation (90-second HTTP
timeout, 1000 output tokens, 8192 context); invalid model output never becomes a fix.

## Where to find it

Open Investigations -> a saved investigation -> AI fix assistance, near the top.
From Pods, use Open saved investigation after investigating. For the simplest first
run, investigate one Deployment and open its saved record; its name is prefilled.
The selector lists Deployments from collected evidence. For a pod investigation,
it resolves the live Pod -> ReplicaSet -> Deployment controller chain, checking
UIDs against the saved evidence and owner references. Stale/replaced pods must be
investigated again. If no Deployment is available, run a Deployment investigation
first; other controller kinds are not supported.

1. Describe the desired correction and verified facts. Do not enter credentials.
2. Generate AI fix proposal. This reads the live Deployment but does not mutate it.
3. Review explanation, supporting evidence, checks, and the YAML diff.
4. Validate with Kubernetes. This uses a server dry-run and does not persist a change.
5. Choose Review approval and apply. Type the EXACT displayed text, including
   context, namespace/name and proposal ID. Wrong text keeps Confirm disabled;
   the backend independently rejects incorrect approval.
6. Read the outcome. Rollout completion is not proof of application correctness.
   Re-run the investigation and check the application behavior that failed.
7. If needed, use Review rollback approval with its separate exact confirmation.

For a readiness 403, ask the model what information is missing first. It should
not guess a health URL. If you independently verified an unauthenticated health
route, state its exact path and port in a new objective. Do not assume /health
exists simply because it is a common example.

## Supported changes and boundaries

Supported Deployment fields: replicas (1–100), regular container image, init-container image, CPU and memory
requests/limits, and existing readiness/liveness/startup probe HTTP paths, ports,
timings and thresholds. No probe deletion, scaling to zero, env/Secret changes,
RBAC, securityContext, command/args, node operations or arbitrary model commands.
These require separate operator review outside this assistant. No automatic fixes.

The model sees a bounded finding sample plus editable Deployment fields, not the
full live spec, environment values or probe authorization headers. Evidence text
and the operator objective are sent to your configured Ollama endpoint; they can
still contain sensitive text. The recovery snapshot contains the original full
spec and may contain literal environment values. Protect your local database.

The diff shows editable fields only. Other spec fields are preserved. The API
uses a server-stored immutable proposal; clients cannot submit replacement YAML
through an approval. Every proposal is HIGH risk and needs review. The model can
return NEEDS_INFORMATION without an applicable change.

## Concurrency, validation and recovery

Every kubectl operation is explicitly bound to the investigation's stored context.
A new read captures the Deployment UID and spec. Apply and rollback reject a
recreated Deployment or any intervening spec edit. JSON Patch tests on UID and
resourceVersion protect the final write against races, including status updates
between the read and patch. If that narrow race occurs, inspect state and create
a new proposal rather than forcing the old one.

Validation expires after ten minutes and must be repeated. Apply repeats server
dry-run and rejects admission changes that would alter the reviewed spec. A
persisted state transition prevents duplicate apply requests. The original spec
is saved before mutation; View recovery YAML provides it independently of the
manual YAML editor's file-based backup list.

- APPLIED: write accepted and rollout check completed.
- APPLIED_UNCONFIRMED: write accepted, rollout not confirmed. Rollback remains
  available if the live spec still equals the applied proposal.
- ROLLED_BACK / ROLLED_BACK_UNCONFIRMED: original spec restored, with rollout
  either confirmed or unconfirmed respectively.
- OUTCOME_UNKNOWN: a write may have reached Kubernetes, or admission changed its
  result. No automatic retry or rollback is offered. Inspect the live Deployment
  and recovery YAML before using the manual YAML editor for a reviewed recovery.
- APPLYING / ROLLING_BACK after backend interruption: likewise inspect live state;
  restarting does not silently resume or repeat a mutation.

Rollback restores the Deployment specification only. It does not restore data,
external side effects, deleted resources, or the old contents of a mutable image
tag. It refuses to overwrite a newer operator change. It is never automatic.

Operation history and proposals survive navigation and backend restart when the
same database is used. The panel refreshes saved proposals every five seconds.
There is no authenticated operator identity or multi-user authorization added in
this release; use the existing local-only installation.

## Verification

184 backend tests, 20 frontend tests, and the production frontend build pass.
New tests cover proposal persistence, allowed fields, no commands/security edits,
no mutation during generation/validation, exact approval, stale UID/spec, expiry,
duplicate apply, timeout handling, admission differences, and conditional rollback.
Frontend tests check approval cancellation and proposal-bound request payloads.
Three existing unused-import build warnings remain.

Kubernetes and Ollama are simulated in automated tests. No live EKS mutation or
live model generation was performed from the development workspace. Complete a
reviewed test on a disposable non-production Deployment before operational use.

```powershell
# backend/
& D:\projects\.venv\Scripts\python.exe -m pytest tests -q
# frontend/
node --test tests/*.cjs
npm run build
```

Implementation references:
https://kubernetes.io/docs/reference/kubectl/generated/kubectl_patch/
https://kubernetes.io/docs/reference/using-api/api-concepts/

## ImagePullBackOff in an init container

The regular application container may remain PodInitializing until the init
container succeeds. The proposed image change must target initContainers/INDEX/image,
not the main container image unless there is separate evidence for that change.
This update supports that distinction and preserves init commands and mounts.

For an unknown replacement image, use this objective:
"Investigate the image pull failure for init container init-copy-folders. I have
not verified a replacement image. Return the missing information and checks;
do not guess a repository or tag."

After independently confirming the intended image exists and is reachable by the
cluster, generate a new proposal with its exact reference. Inspect the diff to
confirm it changes only the intended init-container image before validation and
approval. The assistant does not verify registry contents or pull credentials.
The image name alone does not establish that a particular replacement exists.

A remaining deterministic confidence display multiplied percentages by 100;
this update shows 95% and 90%, matching the stored values.

## Ollama generation error correction

Fix requests now send ModelPlan's JSON schema in Ollama's format field rather
than plain JSON mode. The backend still validates schema, evidence references,
supported fields, dry-run results and approvals. Structured output constrains
format; it does not establish factual correctness or permission to apply.

Errors now distinguish an unreachable Ollama server (503), missing model/API route
(503), generation timeout (504), rejected request (502), incomplete/token-limited
output (502), invalid API envelope (502), and proposal schema mismatch (502).
Schema mismatch messages name fields and error types without including model
responses or their input values. There is no automatic retry or speculative fix.

On your machine, after installing this version and restarting the backend, retry
Generate AI fix proposal. If it still fails, copy the new specific message.
Read-only checks in PowerShell:

```powershell
ollama list
Invoke-RestMethod "http://localhost:11434/api/tags" -TimeoutSec 10
```

The model must match backend OLLAMA_MODEL. The default configured model is used;
it is not selected from whichever model happens to be loaded. Live generation
has not been tested from the development workspace.

Structured-output reference: https://ollama.com/blog/structured-outputs

## Assessment-only mode and supported paths

Assessment only is checked by default in the frontend. Leave it checked when
asking what the evidence establishes or what information is missing. Click
Assess with AI. The response is saved as ASSESSMENT and has no Validate or Apply
action. The server constrains the model to needs_information and an empty changes
array, and independently rejects a model response that violates this restriction.
For an actual change proposal, uncheck Assessment only and provide verified facts.
Existing API clients keep the previous behavior when assessment_only is omitted.

Fix generation now enumerates the supported paths for the live Deployment in the
model's JSON schema. No non-existent container indexes or missing probe handlers
are listed. Backend field/value validation remains mandatory.

This release changes proposal generation only. The existing deterministic
classifier can still overstate malformed request-target exceptions as runtime or
authorization failures. A request parsing log alone is not evidence of Kubernetes
RBAC or filesystem failure, and must not justify those mutations.
