# zWorkforce

**AI Workforce Operating System** — a production-oriented control plane for running bounded AI agents, routing work across model tiers, enforcing approvals and budgets, executing allowlisted tools, and measuring cost per outcome.

zWorkforce uses internal aliases **Luna → Terra → Sol** for low-cost/high-volume, balanced, and frontier workloads. Provider model IDs are environment-configured so model migrations do not require code changes.

## v1.0.0 features
- Agent registry with department, system policy, per-task cost ceiling, iteration and sub-agent limits.
- Complexity-based model router with explicit override and progressive escalation.
- OpenAI-compatible `/chat/completions` adapter plus deterministic mock mode.
- Persistent SQLite/WAL task state, idempotency, restart recovery and audit events.
- Human approval for mutating tasks and cancelation for active work.
- Tool gateway: calculator, rooted workspace list/read, allowlisted HTTP GET, opt-in allowlisted shell, bounded agent delegation.
- AI FinOps: input/cached/output accounting, configurable tier rates, global/department/agent daily or monthly budgets, model mix and top-cost analytics.
- RBAC API keys (`viewer`, `operator`, `admin`) with constant-time verification.
- Responsive dashboard, REST API, Prometheus metrics, Docker/Compose and CI.
- Dependency-free Python 3.12+ runtime.

## Quick start
```bash
python -m zworkforce serve
```
Open `http://localhost:9569`. In local development with no explicit keys, use `dev-admin`.

Checks:
```bash
make check
python -m zworkforce doctor
```

## Live provider
```env
ZWORKFORCE_PROVIDER=openai-compatible
ZWORKFORCE_PROVIDER_BASE_URL=https://api.openai.com/v1
ZWORKFORCE_PROVIDER_API_KEY=...
ZWORKFORCE_MODEL_SOL=<actual-provider-model-id>
ZWORKFORCE_MODEL_TERRA=<actual-provider-model-id>
ZWORKFORCE_MODEL_LUNA=<actual-provider-model-id>
```
The model values in `.env.example` are defaults, not a guarantee that a provider exposes those exact IDs. Set the IDs supported by your account/provider.

## Submit a task
```bash
export ZW_KEY=dev-admin
curl -X POST http://localhost:9569/api/v1/tasks \
  -H "Authorization: Bearer $ZW_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-001" \
  -d '{"agent_id":"researcher","prompt":"Compare three market-entry strategies and recommend one."}'
```
Mutating work can enter `waiting_approval` and is started with `POST /api/v1/tasks/<id>/approve`.

## Security defaults
Shell execution is off. HTTP tools are deny-by-default until hosts are allowlisted. Workspace tools reject traversal. Production mode refuses to start without explicit API keys. Docker runs non-root with dropped capabilities and a read-only root filesystem.

Read [SECURITY.md](SECURITY.md) and [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md) before enabling write-capable tools.

## Architecture
```text
Users / Departments
        │
Dashboard + REST API
        │
Control Plane ── RBAC / Audit / Budgets / Approvals
        │
Model Router ── Luna → Terra → Sol
        │
Bounded Agent Runtime ── Tool Gateway ── Sub-agents
        │
OpenAI-compatible Provider
        │
Usage Ledger / AI FinOps / Prometheus
```

## Scaling boundary
v1.0.0 is a single-node release using SQLite and an in-process worker pool. Do **not** run multiple active replicas against the same SQLite file. PostgreSQL + distributed leasing is tracked in [ROADMAP.md](ROADMAP.md).

MIT licensed.
