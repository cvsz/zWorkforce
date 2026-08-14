# Agent Instructions

This file defines repository instructions for automated coding agents working in `packages/zarvis`.

## Mission

Help evolve Z.A.R.V.I.S. as a focused, security-first assistant suite inside `cvsz/zWorkforce`. Keep the package boundary limited to Z.A.R.V.I.S. applications, services, contracts, voice runtime, memory, perception, task approval, action gateways, and operator tooling.

## Required Reading

Before changing code, read the relevant files:

- `README.md`
- `docs/requirements/master-requirements.md`
- `docs/architecture/README.md`
- `docs/architecture/zarvis.md`
- `SECURITY.md`

For voice UI, speech-provider, runtime-skill, agent-mode, scheduled/continuous operator, or OpenJarvis-inspired work, also read:

- `../../ROADMAPS.md`
- `../../EXEC-PLANING.md`
- `docs/architecture/openjarvis-upgrade-map.md`
- `docs/architecture/skills-agents.md`
- `docs/architecture/voice-agent.md`

## Non-Negotiable Rules

- Do not commit secrets, provider keys, service tokens, wallet keys, card data, KYC payloads, production identifiers, or private user data.
- Do not expose provider credentials to browsers, desktop clients, logs, traces, or tests.
- Keep tool execution behind explicit allowlists, approval state, and scoped action grants.
- Keep memory, perception, and proactive workflows behind consent and retention controls.
- Do not reintroduce non-Z.A.R.V.I.S. product surfaces or legacy platform services without a documented owner, tests, security review, and rollback path.
- Do not apply production infrastructure from an agent without operator approval.
- Do not vendor or recreate a parallel OpenJarvis scheduler/security/runtime stack; adapt selected registry, skill, speech-provider, and agent-mode patterns to existing zWorkforce boundaries.
- Do not iframe ZVoice by weakening its defensive framing policy. Dashboard voice integration must use a browser-safe shared client/BFF contract.
- Do not treat a spoken request, model decision, scheduled trigger, or continuous-agent decision as implicit approval for a mutating action.
- Scheduled and continuous agents must remain bounded by leases/heartbeats, concurrency/rate limits, version pinning, policy, audit, pause/disable controls, and existing durable scheduler semantics.

## Work Style

- Prefer small, reviewable changes.
- Match existing package style and tests.
- Add or update tests for success, failure, authorization, timeout, and denial paths when behavior changes.
- Update docs when architecture, operations, requirements, or security boundaries change.
- Keep generated files reproducible and free of secret-bearing paths.
- Reuse existing Z.A.R.V.I.S. specialists before adding a new agent role.
- Keep repository coding-agent skills under `.agents/skills` distinct from product/runtime Z.A.R.V.I.S. skills.

## Validation Expectations

Run the relevant package tests locally when available. GitHub Actions remain the release gate for CI, validation, secret scanning, dependency policy, SBOM generation, and provenance verification.