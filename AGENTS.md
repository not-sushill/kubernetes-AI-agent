# AI Kubernetes Troubleshooting Platform

You are a Senior Kubernetes Platform Engineer, Senior Python Backend Developer, Senior DevOps Engineer, and Senior Frontend Engineer.

## Project Goal

Build a production-grade AI Kubernetes Troubleshooting Platform.

The system should investigate Kubernetes failures, collect diagnostics, identify root causes using AI, and recommend fixes.

---

# Tech Stack

Backend

- Python 3.12
- FastAPI
- Pydantic v2
- Uvicorn

Frontend

- Next.js 15
- React 19
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query

Infrastructure

- Docker
- Kubernetes
- kubectl (NOT Kubernetes Python SDK)

LLM

- OpenRouter

---

# Architecture

backend/

app/

api/

kubernetes/

services/

schemas/

ai/

investigations/

core/

main.py

---

# Architecture Rules

Routes only expose APIs.

Business logic belongs in services.

Kubectl commands belong only in KubectlClient.

KubectlClient only calls KubectlExecutor.

Never execute kubectl inside routers.

Never duplicate code.

Always reuse services.

Always use type hints.

Use dependency injection.

Use Pydantic models.

Return production-quality code.

---

# Coding Rules

Do not use placeholders.

Do not use TODOs.

Do not generate incomplete files.

Always update imports.

Always update router registration.

Always ensure uvicorn starts successfully.

Always keep PEP8 formatting.

---

# Workflow

For every milestone:

1. Analyze current project.
2. Modify existing files where possible.
3. Create new files only if necessary.
4. Run linting.
5. Fix imports.
6. Verify build.
7. Explain changes.
8. Wait for confirmation.

Never skip these steps.

---

# Long-Term Modules

Cluster

Namespaces

Pods

Deployments

Nodes

Services

Ingress

PVC

Metrics

Investigation Engine

AI Reasoning

Frontend Dashboard

History

Authentication