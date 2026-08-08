# REST API

All `/api/v1/*` routes require `Authorization: Bearer <key>` or `X-API-Key`. `/health` and `/ready` are public; `/metrics` requires viewer role.

| Method | Path | Role |
|---|---|---|
| GET | `/api/v1/overview` | viewer |
| GET/POST | `/api/v1/agents` | viewer/admin |
| GET/POST | `/api/v1/tasks` | viewer/operator |
| GET | `/api/v1/tasks/{id}` | viewer |
| POST | `/api/v1/tasks/{id}/approve` | operator |
| POST | `/api/v1/tasks/{id}/cancel` | operator |
| GET | `/api/v1/models` | viewer |
| GET/POST | `/api/v1/budgets` | viewer/admin |
| GET | `/api/v1/audit` | viewer |

Task request: `{"agent_id":"software-engineer","prompt":"...","mutating":true,"tier_override":"terra"}`. `tier_override` is optional. Use `Idempotency-Key` on task submission.
