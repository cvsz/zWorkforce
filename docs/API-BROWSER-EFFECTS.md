# Browser effect API

This document complements `docs/API.md` for the durable browser mutation side-effect boundary introduced in schema v8.

All endpoints use normal zWorkforce authentication and tenant resolution. Read access requires `viewer` + `workforce:read`. Mutation lifecycle calls require `operator` + `task:write`; manual reconciliation requires `admin` + `task:write`.

```text
POST /api/v1/browser-effects
GET  /api/v1/browser-effects/{effect_id}
POST /api/v1/browser-effects/{effect_id}/claim
POST /api/v1/browser-effects/{effect_id}/finish
POST /api/v1/browser-effects/{effect_id}/reconcile
```

`POST /api/v1/browser-effects` accepts `idempotency_key`, `action_sha256`, and `approval_task_id`. The approval task must belong to the authenticated tenant, represent a mutating task, have the required distinct durable approvals, and not be canceled/rejected/failed.

`claim` is atomic and revalidates the approval before transitioning `not_started -> executing`. `finish` accepts `succeeded`, `failed`, `unknown`, or `canceled` only while executing. `reconcile` is reserved for explicitly resolving `unknown -> succeeded|failed` and never replays the browser action.

The API stores action/result digests and bounded error codes only; raw browser form values and credentials are not persisted in this ledger.
