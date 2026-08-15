# Changelog

All notable changes follow Keep a Changelog. Zeto uses semantic versioning.

## [Unreleased]

### Added

- Production execution plan and initial engineering baseline.
- Engineering agent guide, architecture boundaries, security, and contribution policies.
- Node test runner, lint, formatting, CI, container, and secret-scanning gates.
- Architecture, security, contribution, and environment documentation.
- PostgreSQL 16 schema and migration runner for all planned core entities.
- Transactional idempotency, immutable audit/approval records, durable job claiming, and approval-gated publications.
- Authenticated `/v1` brand API with validation, pagination, request IDs, and OpenAPI contract.
- ProMaster compiler and the `zato` content-brand policy for Niche Content with a white/light-purple palette.
- M01-M05 asset-pack contracts, 12-point QA scoring, model fallback/cost routing, M06 calendar/retry primitives, M07 monitoring rules, and AUTO-PILOT guardrails.
- Production Compose stack, readiness checks, graceful shutdown, and operations runbook.
- Durable workflow runs with ordered artifact handoff, worker ownership, heartbeats, retries, cancellation, idempotent starts, and cost accounting.
- Facebook publishing-provider contract with normalized errors, token-expiry diagnostics, capabilities, rate-limit metadata, and provider fakes.
- Persisted daily analytics, prior-period KPI reports, mention classification, sentiment, and complaint escalation SLAs.
- Protected Prometheus metrics for HTTP, jobs, publications, approvals, provider failures, and generation cost.
- SSRF controls, image signature checks, guaranteed temporary-file cleanup, and executable backup/restore verification.
- Z.A.R.V.I.S. (Zeto Autonomous Runtime Virtual Intelligence System) operator view with live queue/approval/publishing state and the JARVIS reverse-engineering baseline.
- Master Z.A.R.V.I.S. Operator Runtime specification (`docs/JARVIS-VIDEO-REVERSE-ENGINEERING.md`) with video evidence, state-transition table, command/voice/agent/computer-use contracts, event catalog, persistence model, SLOs and acceptance matrix.
- Timeline evidence in the M12 spec populated from automated frame extraction + OCR of the source recording (`media/zarvis-ref.mp4`, SHA-256 `9f93ebdd…`; local-only, git-ignored, not committed), replacing the scaffold-only placeholder.
- M12 spec state machine hardened per review: `PAUSABLE_STATES` defined (pause only from `AWAITING_APPROVAL / EXECUTING / VERIFYING / DEGRADED` ∪ recovery; voice/planner pause defers or cancels to IDLE), `PAUSED → CANCELLED` for ordinary cancel, persisted `previous_state`/`resume_state` checkpoint contract (DEGRADED recovery target never guessed), timestamp-based evidence sample IDs (`t000`–`t250`) with actual frame numbers, per-row confirmation provenance (`pending_human` → `human_confirmed`), and a reference-media manifest (SHA-256, license/redistribution status).
- Arin AI assistant: push-to-talk voice companion with dashboard commands, speech recognition, and voice replies.
- M12 slice 1: Z.A.R.V.I.S. operator runtime contracts, §3.3 state machine (guarded transitions, deterministic pause policy, checkpoint/resume contract, terminal isolation), canonical §10 event catalog with `(session_id, generation, sequence_id)`-scoped monotonic event stream, `operator_*` persistence (sessions, commands, events, plans, steps, tool executions with scoped idempotency, verification evidence), and the `/v1/operator` API including SSE with `Last-Event-ID` resume.
- M12 slice 2: `/zarvis` command center wired to real operator events (spec §2.2 S1, §2.3, §2.4, §4.2) — SSE session lifecycle with persisted `Last-Event-ID` resume, command stream rendered from the canonical event catalog with empty/error states and recovery hints, text command intake against the runtime, orb presentation driven by canonical session state with reduced-motion fallbacks, a shared unit-tested stream/orb mapping module (`public/js/operatorStream.js`), and `GET /v1/operator/sessions/:id` for reload restore.
- M12 slice 3: Sequence Builder persistence and execution (spec §4.3, §9, §11) — durable sequence definitions with ordered steps, `GET/POST/PUT/DELETE /v1/operator/sequences` + `GET /v1/operator/sequences/:id`, sequential execution with `s<N>.result` arg resolution, per-run idempotent step execution, dry-run, partial-failure stop with resume (same run reused, succeeded steps skipped), operator confirmation gate for high-risk replay, canonical event emission (`input.received` type sequence + `step.started/finished/failed`), built-in read-only intents grounded in persisted state (`queue.read`, `session.status`, `events.recent`) with loud unsupported-intent failures, and `GET /v1/operator/sequence-runs/:id` for the resume UI.

### Changed

- Product and runtime identity migrated from the legacy name to Zeto.
- Production encryption configuration now fails closed without an explicit key.
- Legacy JSON operational persistence has been replaced by encrypted PostgreSQL-backed state.

## [1.1.0] - 2026-08-11

- Facebook automation dashboard baseline imported for the Zeto migration.
