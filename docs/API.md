# API Reference — zWorkforce v2.0

Base path: `/api/v1`. JSON write requests require `Content-Type: application/json`.

Authentication supports `Authorization: Bearer <key>` or `X-API-Key`. API keys carry role, tenant and scopes. `superadmin` may select another existing tenant with `X-Tenant-ID`.

## Public runtime endpoints

- `GET /health` — liveness and version.
- `GET /ready` — DB readiness and current provider availability.

## Read APIs

- `GET /overview` — 24h runtime/outcome/FinOps metrics.
- `GET /agents` — tenant agent registry.
- `GET /tasks?limit=&offset=&status=&agent_id=` — tenant tasks.
- `GET /tasks/{id}` — task detail.
- `GET /tasks/{id}/events` — task state/event history.
- `GET /tasks/{id}/approvals` — approval decisions.
- `GET /budgets` — tenant budgets.
- `GET /providers` — configured provider pool and health.
- `GET /models` — Luna/Terra/Sol rates and provider preview.
- `GET /recommendations?days=7` — outcome-based rightsizing hints.
- `GET /memories?q=&limit=` — tenant memory search/list.
- `GET /skills` — signed skill registry.
- `GET /tools` — tool catalog and mutation classification.

Admin reads:

- `GET /audit?limit=&offset=`
- `GET /audit/verify`
- `GET /api-keys`
- `GET /tool-events?task_id=&limit=`

Superadmin:

- `GET /tenants`

## Tasks

`POST /tasks`

```json
{
  "agent_id": "researcher",
  "prompt": "Return a JSON market summary",
  "mutating": false,
  "tier_override": "terra",
  "priority": 10,
  "max_attempts": 3,
  "success_criteria": [
    {"type":"json"},
    {"type":"contains","value":"market"}
  ]
}
```

Optional `Idempotency-Key` is scoped to tenant + actor and includes a request payload hash; reusing a key with a different request is rejected.

Task actions:

- `POST /tasks/{id}/approve` with optional `{ "comment": "..." }`
- `POST /tasks/{id}/reject`
- `POST /tasks/{id}/cancel`
- `POST /tasks/{id}/retry`

The requester cannot approve or reject their own approval-gated task. Multiple approvals require distinct actor names.

## Agents

`POST /agents`

```json
{
  "id":"release-engineer",
  "name":"Release Engineer",
  "department":"engineering",
  "default_tier":"terra",
  "max_cost_credits":60,
  "max_iterations":10,
  "max_subagents":2,
  "required_approvals":1,
  "requires_approval_for_mutations":true,
  "allowed_tools":["workspace_list","workspace_read","workspace_write","shell_exec","agent_delegate"],
  "approval_tools":["workspace_write","shell_exec"],
  "skill_ids":[],
  "system_prompt":"Verify tests and artifacts before claiming success.",
  "enabled":true
}
```

`approval_tools` must be a subset of `allowed_tools`.

## Budgets

`POST /budgets`

```json
{"scope_type":"department","scope_id":"engineering","period":"daily","limit_credits":500}
```

Scope types: `global`, `department`, `agent`. Periods: `daily`, `monthly`.

## Memories

`POST /memories`

```json
{"title":"Release policy","content":"Production deploys need approval.","tags":["release","policy"],"agent_id":"operations"}
```

Search with `GET /memories?q=release&limit=20`.

## Skills

`POST /skills`

```json
{
  "manifest": {
    "id":"repo-review",
    "version":"1.0.0",
    "allowed_tools":["workspace_read"],
    "system_prompt_append":"Check tests and security boundaries."
  },
  "signature":"<hex hmac>",
  "enabled":true
}
```

Generate signatures with `zworkforce skill-sign manifest.json`.

## API keys

`POST /api-keys`

```json
{"name":"ci-worker","role":"operator","scopes":["workforce:read","task:write"]}
```

The plaintext secret is returned once. Revoke with `POST /api-keys/{id}/revoke`.

## Tenants

Superadmin can create a tenant:

```json
{"id":"acme","name":"Acme"}
```

Each new tenant receives the default six-agent registry.

## Metrics

`GET /metrics` requires viewer + `metrics:read` (or `*`). Prometheus metrics include active/queued/dead-letter tasks, 24h runtime success, outcome pass, credits, cost per successful outcome, p95 duration and model/provider health/mix.

## Error format

```json
{"error":{"code":"invalid_request","message":"..."},"request_id":"..."}
```

Production responses suppress internal exception details.
