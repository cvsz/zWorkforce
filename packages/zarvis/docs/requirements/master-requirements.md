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

## Command and Tool Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| CMD-001 | Commands MUST use versioned request and completion contracts. | `zarvis.command.requested.v1` and completion contracts validate in tests. |
| CMD-002 | External API calls MUST be constructed from validated segments. | Tool adapters deny raw URLs, redirects, and unsupported methods. |
| CMD-003 | Mutating actions MUST require explicit approval. | Requests without scoped approval cannot execute mutating tools. |
| CMD-004 | Audit events MUST be emitted for success and failure. | Audit payloads are structured, versioned, and redacted. |

## Voice Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| VOICE-001 | Voice sessions MUST use short-lived tickets. | Gateway tickets have bounded lifetime and are validated before WebSocket upgrade. |
| VOICE-002 | Service tokens MUST remain server-side. | Browser clients never receive service tokens. |
| VOICE-003 | Speech runtimes SHOULD be internal-only by default. | Published ports bind to loopback or internal networks unless explicitly approved. |
| VOICE-004 | Realtime interruption and transcription paths MUST be tested. | Voice gateway, voice agent, and zvoice tests cover live/final events and failure states. |

## Memory, Perception, and Proactive Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| CTX-001 | Memory writes MUST include owner and retention semantics. | Memory records include owner, retention, and deletion metadata. |
| CTX-002 | Perception sessions MUST require explicit consent. | Perception APIs reject missing or expired consent. |
| CTX-003 | Proactive signals MUST be policy-filtered. | Proactive actions are bounded by subscription, consent, and quiet-hour policy. |
| CTX-004 | Raw sensitive content SHOULD NOT be stored in traces. | Logs and traces use correlation IDs and redacted metadata. |

## CI, Security, and Supply-Chain Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| CI-001 | CI MUST run Z.A.R.V.I.S. Node workspace tests. | `pnpm install --frozen-lockfile`, peer checks, and tests run for package changes. |
| CI-002 | CI MUST run Z.A.R.V.I.S. API tests. | `services/zarvis-api` Python tests and dependency audit run in CI. |
| CI-003 | CI MUST validate the Windows client restore/build path. | Z.A.R.V.I.S. Windows restore and Windows workflow gates remain enabled. |
| CI-004 | Dependency policy MUST cover retained package ecosystems. | Dependabot monitors root npm, `zarvis-api`, `zctl`, and Windows NuGet dependencies. |
| CI-005 | Release builds MUST produce SBOM and provenance signals. | Release workflows produce checksums, SBOMs, and attestations for published artifacts. |

## Production Requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| PROD-001 | Production deployment MUST be blocked until staging readiness is complete. | Staging readiness checklist is signed off by the operator. |
| PROD-002 | Production MUST have rollback notes. | Rollback SHA, service version, data migration status, and verification commands are recorded. |
| PROD-003 | External traffic MUST remain gated until health, logs, metrics, traces, and alerts are visible. | Operator confirms visibility before external traffic. |
