# Z.A.R.V.I.S. Master Requirements

This document is the requirements baseline for the Z.A.R.V.I.S. package suite in `cvsz/zWorkforce`.

## Scope

The package includes:

- browser, Windows, and realtime voice Z.A.R.V.I.S. surfaces;
- command orchestration and audit events;
- task approval and action gateway boundaries;
- memory, perception, and proactive signal services;
- voice gateway and speech runtime services;
- shared contracts and operator tooling;
- CI, security, SBOM, provenance, and release gates.

Non-Z.A.R.V.I.S. product surfaces and legacy platform services are out of scope.

## Requirement Language

| Word | Meaning |
|---|---|
| MUST | Required before merge or production use |
| MUST NOT | Prohibited behavior |
| SHOULD | Expected unless an operator-approved exception exists |
| MAY | Optional behavior |
| OPERATOR APPROVAL | Explicit human approval recorded outside automated agent execution |

## System Objectives

| ID | Requirement | Acceptance criteria |
|---|---|---|
| OBJ-001 | Clients MUST NOT receive provider secrets or service tokens. | Browser, Windows, and voice clients expose no upstream credentials. |
| OBJ-002 | Tool execution MUST be allowlisted. | Unsupported or mutating tools fail closed unless explicitly approved. |
| OBJ-003 | Z.A.R.V.I.S. services MUST use least-privilege boundaries. | Each service has documented ownership, trusted callers, and denied capabilities. |
| OBJ-004 | The package MUST be independently buildable and testable. | CI covers the Z.A.R.V.I.S. package and fails on missing required paths. |
| OBJ-005 | Memory, perception, and proactive flows MUST be consent-bound. | Tests or docs prove consent, retention, and deletion behavior before production. |

## Architecture Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| ARCH-001 | User-facing Z.A.R.V.I.S. apps MUST stay in `apps/*`. | Console, Windows, and voice surfaces live under app directories. |
| ARCH-002 | Deployable runtime boundaries MUST stay in `services/*`. | APIs, gateways, memory, perception, proactive, and voice runtimes have explicit package boundaries. |
| ARCH-003 | Shared schemas MUST stay in `packages/contracts`. | Versioned contracts include tests and are not duplicated ad hoc. |
| ARCH-004 | Infrastructure apply actions MUST require operator approval. | No automated agent can deploy production infrastructure without approval. |
| ARCH-005 | Service boundaries MUST deny capabilities outside their responsibility. | Deny rules are tested or documented per service. |
| ARCH-006 | OpenJarvis-inspired changes MUST integrate with existing zWorkforce execution/security boundaries rather than add parallel scheduler, approval, tenant, or audit systems. | Architecture review and tests show one authoritative durable/policy path. |

## Command and Tool Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| CMD-001 | Commands MUST use versioned request and completion contracts. | `zarvis.command.requested.v1` and completion contracts validate in tests. |
| CMD-002 | External API calls MUST be constructed from validated segments. | Tool adapters deny raw URLs, redirects, and unsupported methods. |
| CMD-003 | Mutating actions MUST require explicit approval. | Requests without scoped approval cannot execute mutating tools. |
| CMD-004 | Audit events MUST be emitted for success and failure. | Audit payloads are structured, versioned, and redacted. |
| CMD-005 | Voice/model/scheduled/continuous decisions MUST NOT be treated as implicit mutation approval. | Approval-required tests prove mutation is denied until a valid scoped approval is recorded. |

## Voice Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| VOICE-001 | Voice sessions MUST use short-lived tickets. | Gateway tickets have bounded lifetime and are validated before WebSocket upgrade. |
| VOICE-002 | Service tokens MUST remain server-side. | Browser clients never receive service tokens. |
| VOICE-003 | Speech runtimes SHOULD be internal-only by default. | Published ports bind to loopback or internal networks unless explicitly approved. |
| VOICE-004 | Realtime interruption and transcription paths MUST be tested. | Voice gateway, voice agent, and zvoice tests cover live/final events and failure states. |
| VOICE-005 | The zWorkforce dashboard MUST support an authenticated Z.A.R.V.I.S. voice card without weakening ZVoice framing protection. | Dashboard uses a browser-safe shared client/BFF contract; no iframe/CSP weakening is required. |
| VOICE-006 | Push-to-talk MUST support pointer/touch and keyboard-accessible operation with explicit microphone state. | Tests cover press/release/cancel, keyboard repeat prevention, permission denial and cleanup. |
| VOICE-007 | Dashboard and ZVoice SHOULD share one presentation-independent realtime voice client/state contract. | Protocol conformance tests run against both surfaces. |
| VOICE-008 | Voice presence animation MUST expose equivalent text state and respect reduced-motion preferences. | Accessibility tests/manual evidence cover labels, live state and `prefers-reduced-motion`. |
| VOICE-009 | Speech providers MUST be explicit, health-reporting and policy-aware. | STT/TTS provider selection and local/cloud classification are visible server-side; secrets are redacted. |
| VOICE-010 | A pinned speech provider MUST fail visibly rather than silently substitute an incompatible backend. | Provider-selection tests cover unavailable pinned backend behavior. |

## Runtime Skill Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| SKILL-001 | Runtime skills MUST use versioned manifests with input/output schemas. | Invalid schema/version manifests are rejected. |
| SKILL-002 | Runtime skills MUST declare capabilities, allowed tools and mutability. | Unknown or undeclared capability/tool use is denied. |
| SKILL-003 | Mutating runtime skills MUST declare an approval policy. | A mutating skill without approval policy fails validation/activation. |
| SKILL-004 | Runtime skills MUST declare bounded timeout/concurrency and retry/idempotency behavior. | Tests cover timeout, retry and duplicate external-effect prevention. |
| SKILL-005 | Skill dependencies MUST be validated and cycles rejected. | Dependency-cycle tests fail closed. |
| SKILL-006 | Discovery MUST NOT imply authorization or production activation. | Discovered/generated skills remain disabled until policy/config enables a reviewed version. |
| SKILL-007 | Trace-mined skill candidates MUST require review and tests before activation. | No self-generated skill can auto-promote into production. |

## Runtime Agent Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| AGENT-001 | Runtime agents MUST declare `on_demand`, `scheduled`, or `continuous` mode. | Agent manifest validation rejects unsupported/ambiguous mode. |
| AGENT-002 | Scheduled agents MUST use existing durable scheduler/event occurrence and idempotency semantics. | Duplicate occurrence tests produce one durable run/effect. |
| AGENT-003 | Continuous agents MUST use leases/heartbeats, rate limits, concurrency limits and failure budgets. | Stale/runaway tests demonstrate containment. |
| AGENT-004 | Scheduled/continuous agents MUST support pause/disable and version pinning/rollback. | Operator tests cover pause/resume/version rollback state. |
| AGENT-005 | Agent handoffs MUST NOT expand capabilities, tools, tenant scope or mutation scope. | Handoff validation rejects privilege expansion. |
| AGENT-006 | Existing specialist agents SHOULD be reused before adding overlapping roles. | Architecture review documents why any new specialist is necessary. |
| AGENT-007 | A supervisor MAY recommend recovery/rollback but MUST NOT autonomously broaden privileges or apply protected production changes. | Policy/approval tests deny unauthorized recovery mutation. |

## Memory, Perception, and Proactive Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| CTX-001 | Memory writes MUST include owner and retention semantics. | Memory records include owner, retention, and deletion metadata. |
| CTX-002 | Perception sessions MUST require explicit consent. | Perception APIs reject missing or expired consent. |
| CTX-003 | Proactive signals MUST be policy-filtered. | Proactive actions are bounded by subscription, consent, and quiet-hour policy. |
| CTX-004 | Raw sensitive content SHOULD NOT be stored in traces. | Logs and traces use correlation IDs and redacted metadata. |
| CTX-005 | Voice-derived durable memory MUST follow the same consent/retention/delete controls as other memory. | Session-memory tests prove ephemeral transcript does not automatically become durable memory. |

## CI, Security, and Supply-Chain Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| CI-001 | CI MUST run Z.A.R.V.I.S. Node workspace tests. | `pnpm install --frozen-lockfile`, peer checks, and tests run for package changes. |
| CI-002 | CI MUST run Z.A.R.V.I.S. API tests. | `services/zarvis-api` Python tests and dependency audit run in CI. |
| CI-003 | CI MUST validate the Windows client restore/build path. | Z.A.R.V.I.S. Windows restore and Windows workflow gates remain enabled. |
| CI-004 | Dependency policy MUST cover retained package ecosystems. | Dependabot monitors root npm, `zarvis-api`, `zctl`, and Windows NuGet dependencies. |
| CI-005 | Release builds MUST produce SBOM and provenance signals. | Release workflows produce checksums, SBOMs, and attestations for published artifacts. |
| CI-006 | Voice-card/shared-client tests MUST cover cleanup, interruption, auth denial and secret isolation. | CI fails on regressions in the browser/BFF voice boundary. |
| CI-007 | Skill/agent-mode tests MUST cover policy denial, duplicate/idempotency, lease/heartbeat and rollback behavior. | CI contains deterministic fake-backed coverage for these boundaries. |

## Production Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| PROD-001 | Production deployment MUST be blocked until staging readiness is complete. | Staging readiness checklist is signed off by the operator. |
| PROD-002 | Production MUST have rollback notes. | Rollback SHA, service version, data migration status, and verification commands are recorded. |
| PROD-003 | External traffic MUST remain gated until health, logs, metrics, traces, and alerts are visible. | Operator confirms visibility before external traffic. |
| PROD-004 | Interactive voice SLOs MUST be measured in production-equivalent staging before external promotion. | Ticket/STT/reasoning/TTS/end-to-end measurements are attached to release evidence. |
| PROD-005 | Continuous-agent rollout MUST be bounded and reversible. | Canary/cohort, failure-budget, pause and rollback evidence is recorded before broad enablement. |