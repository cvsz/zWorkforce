# API v3

All `/api/v1/*` endpoints require authentication. Tenant scope comes from the credential; superadmin may set `X-Tenant-ID`. JSON errors use `{"error":{"code","message"},"request_id"}`.

## Core

```text
GET  /health
GET  /ready
GET  /metrics
GET  /api/v1/overview
GET  /api/v1/providers
GET  /api/v1/models
GET  /api/v1/recommendations
GET  /api/v1/tools
```

## Agents / policy

```text
GET/POST /api/v1/agents
GET      /api/v1/agents/{id}/versions
GET/POST /api/v1/agent-templates
POST     /api/v1/agent-templates/{id}/instantiate
GET/POST /api/v1/policies
```

Policy document:

```json
{"default":"allow","rules":[{"id":"deny-shell","effect":"deny","action":"tool.shell_exec","when":{"department":"finance"}}]}
```

## Tasks

```text
GET/POST /api/v1/tasks
GET      /api/v1/tasks/{id}
GET      /api/v1/tasks/{id}/events
GET      /api/v1/tasks/{id}/approvals
POST     /api/v1/tasks/{id}/approve
POST     /api/v1/tasks/{id}/reject
POST     /api/v1/tasks/{id}/cancel
POST     /api/v1/tasks/{id}/retry
```

`POST /tasks` accepts `agent_id`, `prompt`, `mutating`, `tier_override`, `priority`, `success_criteria`, `max_attempts`. Use `Idempotency-Key` for safe retries.

## Workflow automation

```text
GET/POST /api/v1/workflows
GET/POST /api/v1/workflow-runs
GET      /api/v1/workflow-runs/{id}
POST     /api/v1/workflow-tick
GET/POST /api/v1/schedules
GET/POST /api/v1/event-rules
POST     /api/v1/events
POST     /api/v1/scheduler-tick
```

Use `Idempotency-Key` on `POST /api/v1/workflow-runs` when retrying a scheduled
or operator-triggered occurrence. Schedule and event dispatches derive a stable
occurrence key automatically. Task and workflow execution remain at-least-once
after lease expiry; external mutating consumers must deduplicate their own
side effects.

## Evaluation

```text
GET/POST /api/v1/evaluation-suites
POST     /api/v1/evaluation-runs
GET      /api/v1/evaluation-runs/{id}
POST     /api/v1/evaluation-tick
```

## Memory / artifacts

```text
GET/POST /api/v1/memories
GET      /api/v1/rag?q=...
POST     /api/v1/rag/reindex
GET/POST /api/v1/artifacts
GET/POST /api/v1/skills
```

Artifact POST body uses base64 payload because this API intentionally stays JSON-only in v3.

## FinOps / SLO

```text
GET/POST /api/v1/budgets
GET      /api/v1/chargeback?hours=24
GET      /api/v1/capacity?hours=24
GET      /api/v1/slo
POST     /api/v1/slo
POST     /api/v1/economics
```

## Identity / audit

```text
GET/POST /api/v1/tenants
GET/POST /api/v1/api-keys
POST     /api/v1/api-keys/{id}/revoke
GET      /api/v1/audit
GET      /api/v1/audit/verify
GET      /api/v1/tool-events
```

## MCP

`POST /mcp` accepts stateless JSON-RPC requests with `MCP-Protocol-Version: 2026-07-28`. It uses the same API authentication and tenant authorization as REST.

Supported methods:

```text
server/discover
tools/list
tools/call
```

Built-in MCP management tools are documented in [MCP.md](MCP.md).
