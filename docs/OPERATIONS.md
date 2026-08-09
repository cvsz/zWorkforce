# Operations

## Health

- `/health` — process liveness.
- `/ready` — database readiness plus at least one available provider.
- `/metrics` — authenticated Prometheus exposition.
- `zworkforce doctor` — configuration/database/provider summary plus audit verification.

## Dead letters

A task enters `dead_letter` when its attempt budget is exhausted, including repeated worker lease expiry. Inspect task error/events/tool-events, provider health, budgets, worker logs and storage latency. After remediation use retry to reset attempts and requeue.

## Provider incidents

Real request failures update persistent health. At the configured consecutive-failure threshold, the provider circuit opens temporarily and other configured providers that support the tier can take over. A later successful call resets health.

## Audit verification

Run periodically:

```bash
zworkforce audit-verify --tenant default
```

A failed chain is a high-severity integrity signal. Preserve the database and host logs before remediation.

## Cost operations

Use tenant/department/agent budgets as preventive controls. `/api/v1/recommendations` is a heuristic rightsizing signal; validate quality before changing default tiers.
