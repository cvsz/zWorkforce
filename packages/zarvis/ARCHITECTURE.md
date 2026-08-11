# Architecture

`z-platform` is organized as a security-first platform with explicit trust boundaries between browser clients, platform services, AI providers, agent workers, workspace execution, and billing.

## Repository layout

| Path | Responsibility |
|---|---|
| `apps/` | User-facing applications and thin UI/proxy surfaces. |
| `services/` | Deployable APIs and workers with explicit runtime ownership. |
| `packages/` | Shared libraries and versioned contracts. |
| `tools/` | Developer tooling, generators, and operations checks. |
| `docs/` | Architecture, requirements, migration plans, runbooks, and project documentation. |
| `.github/workflows/` | CI, validation, and operations gates. |

## Core domains

| Domain | Runtime | Boundary |
|---|---|---|
| AI Gateway | `services/ai-gateway` | Owns upstream provider access, model catalog, attachment/upload adapters, and usage emission. |
| ZAI Coder | `apps/zaicoder` | Uses gateway-only web and CLI paths. |
| ZChat | `apps/zchat` | Thin chat UI and server-side gateway proxy. |
| Agent Orchestrator | `services/agent-orchestrator` | Durable jobs, queue, approval state, scoped tools, sandbox workers, audit events. |
| Workspace Runtime | `services/workspace-runtime` | Generated project validation, shell/deploy approval boundary, sandbox execution. |
| Billing Ledger | `services/billing-ledger` | Idempotent usage records, credits, invoice intents. |
| ZWallet | `apps/zwallet` | Billing-ledger adapter only; unsafe wallet/payment capabilities denied. |
| Contracts | `packages/contracts` | Versioned API and event schemas. |

## Trust boundaries

- Browsers never receive upstream provider secrets or service tokens.
- AI requests flow through the AI Gateway.
- Mutating agent work requires approval and scoped tool grants.
- Workspace shell/deploy requests require explicit approval grants.
- Billing receives usage, credits, and invoice intents only.
- Wallet signing, card data, KYC payloads, MPC shares, and swaps are outside AI and billing paths.
- Infrastructure apply actions require operator approval.

## Event and data model

Shared contracts live in `packages/contracts`. Agent and billing events are versioned and should remain backward compatible unless a migration plan documents the break.

## Production architecture

Production provider choices are operator decisions. Before external traffic, staging must verify identity, Cloudflare Access, secrets, databases, queues, audit pipeline, observability, backups, sandbox runtime, billing, and rollback.

See also:

- `docs/architecture/README.md`
- `docs/requirements/master-requirements.md`
- `docs/operations/production-master.md`
