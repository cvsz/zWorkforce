# Architecture

## Domain ownership

| Domain | Location | Responsibility |
|---|---|---|
| Product UI | `apps/zarvis-console`, `apps/zarvis-windows`, `apps/zvoice` | Explicit command, native operator, and voice surfaces |
| Orchestration | `services/zarvis-orchestrator` | Command validation, tool allowlisting, speech-ready summaries, and audit events |
| Task and action gateways | `services/zarvis-task-gateway`, `services/zarvis-action-gateway` | Approval-scoped task and action execution boundaries |
| Memory and perception | `services/zarvis-memory`, `services/zarvis-perception`, `services/zarvis-proactive` | Consent-bound context, perception sessions, and proactive signals |
| Voice runtime | `services/voice-gateway`, `services/voice-agent` | Short-lived voice tickets and internal speech pipeline |
| Public API | `services/zarvis-api` | HTTP API boundary for external integration |
| Shared contracts | `packages/contracts` | Versioned API/event schemas |

## Trust boundaries

Clients never receive provider secrets or service tokens. Tool execution remains allowlisted and least-privilege. Mutating work requires versioned approval events and bounded action grants. Perception and proactive workflows require explicit consent and retention controls.
