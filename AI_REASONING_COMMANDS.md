# Evidence-backed AI reasoning and diagnostic commands

## Install

This ZIP is cumulative: backend/ and frontend/ include the terminal, log search,
highlighting/display fixes, AI assessment, approved fixes and rollback.
Stop both servers; extract into D:\projects\ai-kubernetes-agent; restart with the
same environment/database; Ctrl+F5. No new dependencies. Local .env, databases,
backups, virtual environments, node_modules and Git metadata are excluded.
The backend adds diagnostic_runs through its existing create_all initialization.
Keep the same database to preserve investigations, proposals and diagnostic history.

## Workflow

1. Run a fresh Deployment investigation and open its saved record.
2. Keep Assessment only enabled. Describe the incident and request evidence-backed
   likely causes, uncertainty, and useful checks. Click Assess with AI.
3. Read Evidence-based reasoning: hypotheses, supporting evidence IDs, qualitative
   confidence, uncertainty and a suggested diagnostic check or manual check.
4. Expand Read-only diagnostic commands. Review the displayed kubectl commands,
   then click Run read-only check for the relevant check. Nothing runs merely
   because the model suggested it.
5. Read the saved result and actual executed commands. Failed checks remain FAILED
   rather than being presented as evidence of a healthy workload.
6. Click Reassess with check results. This creates a new ASSESSMENT; it cannot apply
   a change. Results must be successful, less than 15 minutes old, and match the
   live Deployment UID/spec. Otherwise run fresh checks.
7. If a specific supported correction is established, click Prepare fix using
   these checks. The form switches out of assessment mode and identifies its
   source proposal. Edit the objective to include the exact verified correction.
8. Generate -> review diff -> server validate -> exact typed approval -> apply.
   The previous UID/spec/resourceVersion safeguards and separate rollback approval
   remain. A new proposal never inherits approval from an earlier one.

The assistant does not guess image tags, database grants or application code
changes when the evidence is insufficient. Reasoning is an observable support /
uncertainty summary, not proof that the model's hypothesis is correct.

## Read-only checks in this release

- Deployment rollout and images: replicas, conditions, generation and editable
  image/resource/probe fields. Literal env values and probe headers are excluded.
- Owned pod health: phase, conditions, current/previous container state and restart
  counts. Owner UIDs connect Deployment -> ReplicaSet -> Pod. Unrelated pods are
  excluded from returned results. First 20 pods / 20 statuses per pod are sampled.
- Warning events: retained warnings for the Deployment, its ReplicaSets and Pods,
  newest first, limited to 30. No events does not prove no historical incident.

Commands are predefined server-side argv arrays using kubectl get. Requests contain
only a check ID; arbitrary command text, shell pipelines, exec, apply, delete and
Secret retrieval are not supported by this executor. Every command explicitly
uses the saved context and namespace. Ownership inventory reads namespace-level
ReplicaSets and Pods; the returned result is filtered by controller UID. These
checks therefore require list permissions on those resources, plus deployment
get and events list as appropriate.

The Deployment UID is checked before collection. Multi-command checks recheck UID
and spec afterward to reject a target changed during collection. Each command has
a 15-second Kubernetes request timeout and at most a 20-second process timeout;
a check has a 60-second execution budget. Output is capped at 12,000 characters,
with truncation marked. Reassessment uses at most one fresh result per check type,
three checks total, 2,400 characters each. These are samples, not complete history.

Runs are persisted separately from immutable fix proposals. Repeated reads do not
change fix approval state. Backend interruption can leave a RUNNING read-only run;
it can be run again. Neither restart nor reassessment resumes a mutation.

Logs remain available in the log viewer. There is no new automatic terminal or
log execution, central log retention, database connection, SQL mutation, node fix,
or arbitrary model-command execution. Existing manual exec remains separate.
This is still the local single-user app, not a multi-user authorization system.

## Diagnosis corrections

Fresh investigations now classify:
- Invalid character found in the request target: malformed HTTP request rejected,
  warning; not proof of an application outage or Kubernetes authorization failure.
- MySQL SELECT command denied / 1142: database SELECT privilege denial; check the
  actual database account, schema and grants with the database owner. No automatic
  RBAC, securityContext or database-permission change is proposed.

Existing saved investigations are not rewritten. Re-run an investigation to see
these corrected findings. Other heuristic diagnostic rules can still need review.

## Validation and local acceptance

200 backend tests and 26 frontend tests pass, including fixed-command execution,
owner filtering, persistence, stale-source rejection, assessment-only behavior,
exact approval/rollback, the two diagnosis corrections, and explicit UI check runs.
Production frontend build passes with the existing three unused-import warnings.
Kubernetes/Ollama interactions are simulated in tests. No live cluster commands or
model generations were run from the development workspace for this release.

For your sim-be test: run a fresh investigation, assess the malformed request-target
exception, run Deployment rollout and Owned pod health, then reassess. Check that
it distinguishes the logged request rejection from current workload availability
and does not invent an RBAC fix. Stop at assessment if a correction is unverified.
