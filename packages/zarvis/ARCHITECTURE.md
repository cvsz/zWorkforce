# Architecture

Z.A.R.V.I.S. is organized as a security-first assistant suite with explicit trust boundaries between browser clients, orchestrator services, voice runtimes, perception, memory, task approval, and external APIs.

## Repository layout

| Path | Responsibility |
|---|---|
| `apps/` | User-facing applications and thin UI/proxy surfaces. |
| `services/` | Deployable APIs and workers with explicit runtime ownership. |
| `packages/` | Shared libraries and versioned contracts. |
| `tools/` | Developer and operator tooling. |
| `docs/` | Architecture, requirements, migration plans, runbooks, and project documentation. |
| `.github/workflows/` | CI, validation, and operations gates. |

## Core domains

| Domain | Runtime | Boundary |
|---|---|---|
| Z.A.R.V.I.S. Console | `apps/zarvis-console` | Explicit user command surface. |
| Z.A.R.V.I.S. Windows | `apps/zarvis-windows` | Native operator client. |
| Voice | `apps/zvoice`, `services/voice-gateway`, `services/voice-agent` | Browser voice surface, ticket gateway, and speech runtime. |
| Orchestration | `services/zarvis-orchestrator` | Command validation, tool allowlisting, speech-ready summaries, audit events. |
| Task Approval | `services/zarvis-task-gateway`, `services/zarvis-action-gateway` | Plan validation and approval-scoped action execution. |
| Memory and Perception | `services/zarvis-memory`, `services/zarvis-perception`, `services/zarvis-proactive` | Consent-bound context, perception, and proactive signals. |
| Z.A.R.V.I.S. API | `services/zarvis-api` | HTTP API boundary for external integration. |
| Contracts | `packages/contracts` | Versioned API and event schemas. |

## Trust boundaries

- Browsers never receive upstream provider secrets or service tokens.
- Voice and command requests cross server-side service boundaries before any model or tool execution.
- Mutating work requires approval and scoped action grants.
- Perception and proactive signals require explicit consent and retention controls.
- Infrastructure apply actions require operator approval.

## Event and data model

Shared contracts live in `packages/contracts`. Z.A.R.V.I.S. command, task, memory, perception, and audit events are versioned and should remain backward compatible unless a migration plan documents the break.

## Production architecture

Production provider choices are operator decisions. Before external traffic, staging must verify identity, secrets, databases, queues, audit pipeline, observability, backups, consent controls, and rollback.

See also:

- `docs/architecture/README.md`
- `docs/requirements/master-requirements.md`
