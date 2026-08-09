# zWorkforce

**AI Workforce Operating System — control plane, durable agent runtime, policy gateway and AI FinOps.**

zWorkforce turns LLM providers into a governed workforce runtime: users submit outcome-oriented tasks to named agents, a model router chooses a cost tier, durable workers execute bounded tool loops, approvals gate mutations, provider failover keeps jobs moving, and the control plane measures cost and business outcomes by tenant, department, agent and model tier.

## v2.0.0

- Multi-tenant isolation across agents, tasks, memory, budgets, API keys, audit and usage.
- Durable lease queue with worker claims, heartbeats, stale-lease recovery, retries and dead-letter states.
- Separate API and worker modes, plus embedded-worker mode for local development.
- Health-aware multi-provider pool with priority, model-per-tier mapping, retry, circuit breaking and fallback.
- Luna / Terra / Sol policy tiers with complexity routing, explicit override and escalation.
- Four-eyes approvals: requester cannot approve their own mutating task; up to three distinct approvals.
- Per-agent tool grants with runtime enforcement for mutations.
- Rooted workspace IO, atomic writes, bounded calculator, SSRF-aware allowlisted HTTP, sanitized shell execution, tenant memory and sub-agent delegation.
- Persistent API keys with roles, scopes, revocation and one-time secret issuance. Optional HMAC-signed identity-aware proxy mode.
- Per-tenant tamper-evident SHA-256 audit chain and verification command/API.
- Workforce memory and signed skill manifests.
- Deterministic outcome evaluation, outcome pass rate, cost per successful outcome, p95 runtime and model-rightsizing recommendations.
- AI FinOps model/provider mix, budgets, token/credit accounting and Prometheus metrics.
- Responsive dashboard, Docker/Compose, non-root container, dropped capabilities, CI on Python 3.12–3.14 and safe migration from v1.

## Architecture

```text
Users / Teams / Automation
          |
          v
+------------------------------+
| zWorkforce Control Plane     |
| Auth / RBAC / Tenant Context |
| Agents / Budgets / Approvals |
| Audit / Memory / Skills      |
+--------------+---------------+
               | durable task
               v
+------------------------------+
| SQLite/WAL Lease Queue       |
| claim / heartbeat / retry    |
| dead-letter / recovery       |
+--------------+---------------+
               |
               v
        +-------------+
        | Worker Pool |
        +------+------+ 
               |
               v
        +-------------+
        | Model Router|
        | L/T/S tiers |
        +------+------+ 
               |
               v
+------------------------------+
| Provider Pool                |
| priority / health / fallback |
| circuit breaker              |
+--------------+---------------+
               |
               v
 Workspace / HTTP / Shell / Memory / Sub-agents
```

See [ARCHITECTURE.md](ARCHITECTURE.md), [SECURITY.md](SECURITY.md), and [docs/THREAT-MODEL.md](docs/THREAT-MODEL.md).

## Quick start

Requires Python 3.12+ and has no mandatory third-party runtime dependencies.

```bash
git clone https://github.com/cvsz/zWorkforce.git
cd zWorkforce
cp .env.example .env
python -m zworkforce doctor
python -m zworkforce serve
```

Open `http://localhost:9569`. Development keys are for local use only.

### API and worker separately

```bash
ZWORKFORCE_EMBEDDED_WORKERS=0 python -m zworkforce serve
python -m zworkforce worker --id worker-1
```

Multiple worker processes on the same reliable local filesystem can claim work safely through SQLite WAL + transactional leases. Do not place the SQLite database on NFS/SMB and claim cross-host HA; use a future PostgreSQL/managed-queue adapter for that topology.

## Docker Compose

```bash
export ZWORKFORCE_API_KEYS="$(python -c 'import secrets; print(secrets.token_urlsafe(32))'):superadmin:default:bootstrap:*"
docker compose up -d --build
```

Compose runs separate `api` and `worker` services sharing a local durable data volume and workspace.

## Providers

Development:

```env
ZWORKFORCE_PROVIDER=mock
```

Single OpenAI-compatible endpoint:

```env
ZWORKFORCE_PROVIDER=openai-compatible
ZWORKFORCE_PROVIDER_BASE_URL=https://api.openai.com/v1
ZWORKFORCE_PROVIDER_API_KEY=...
ZWORKFORCE_MODEL_SOL=your-frontier-model
ZWORKFORCE_MODEL_TERRA=your-balanced-model
ZWORKFORCE_MODEL_LUNA=your-low-cost-model
```

For failover, set `ZWORKFORCE_PROVIDERS_JSON` to an array of providers with `name`, `kind`, `base_url`, `api_key_env`, `priority`, and `models.luna|terra|sol`. Repeated failures open a circuit temporarily so a lower-priority healthy provider can take over.

## Security model

Mutations are deny-by-default. A mutating tool call requires: authenticated role/scope, correct tenant context, an agent grant, a task declared `mutating`, completed distinct approvals where policy requires them, and an enabled server-side capability. Shell and outbound HTTP have additional allowlists.

Provider secrets remain server-side and are never placed in static assets or prompts. Shell uses `shell=False` and a sanitized environment. HTTP tools require explicit host allowlisting, revalidate redirects and reject private/non-routable DNS results by default. Workspace access is rooted and writes are atomic. Task iterations, retries, delegation depth, tool runtime/output and spend are bounded.

DNS preflight reduces SSRF risk but is not a substitute for a network egress proxy that pins destinations. High-assurance deployments should add egress policy.

## CLI

```text
zworkforce serve
zworkforce worker [--id NAME] [--once]
zworkforce doctor
zworkforce init
zworkforce tenant-create TENANT [--name NAME]
zworkforce key-create --name NAME --role ROLE [--tenant TENANT] [--scopes SCOPE,...]
zworkforce audit-verify [--tenant TENANT]
zworkforce skill-sign manifest.json
```

`key-create` returns the plaintext secret once; only its SHA-256 digest is stored.

## Task lifecycle

```text
waiting_approval -- approve(s) --> queued --> running --> succeeded
       |                             |          |  |
       +-- reject --> canceled       |          |  +--> failed
                                     |          +-----> queued (retry)
                                     |                  |
                                     +------------------+--> dead_letter after max attempts
```

Worker claims have leases and heartbeats. Expired work is requeued or dead-lettered after the attempt budget is exhausted.

## Outcome economics

Task submission can include deterministic `success_criteria` using `non_empty`, `contains`, `regex`, `json`, or `max_chars`. Runtime success is tracked separately from business outcome pass so the platform can calculate `cost_per_success` and produce evidence-based tier-rightsizing recommendations.

## Agent policy

Each agent defines default tier, max credits, iterations, sub-agent limit, approval count, tool grants, approval-sensitive tools, signed skill IDs and system instructions. Seeded departments receive different grants rather than a universal capability set.

## Major API surface

```text
GET/POST /api/v1/agents
GET/POST /api/v1/tasks
GET      /api/v1/tasks/{id}
GET      /api/v1/tasks/{id}/events
GET      /api/v1/tasks/{id}/approvals
POST     /api/v1/tasks/{id}/approve|reject|cancel|retry
GET      /api/v1/overview
GET      /api/v1/providers
GET      /api/v1/models
GET      /api/v1/recommendations
GET/POST /api/v1/memories
GET/POST /api/v1/skills
GET      /api/v1/audit
GET      /api/v1/audit/verify
GET/POST /api/v1/api-keys
POST     /api/v1/api-keys/{id}/revoke
GET/POST /api/v1/budgets
GET      /api/v1/tools
GET      /api/v1/tool-events
GET/POST /api/v1/tenants
```

See [docs/API.md](docs/API.md).

## Production boundary

v2.0.0 is production-capable for a single-host/multi-process deployment on reliable local storage. Native cross-host HA, multi-region scheduling, PostgreSQL leases, managed queues, native OIDC/SAML/SCIM and external immutable audit storage are deliberately not claimed as implemented. Identity federation can terminate at a hardened identity-aware proxy using the HMAC-signed identity boundary.

## License

MIT.
