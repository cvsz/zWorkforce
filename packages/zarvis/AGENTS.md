# Agent Instructions

This file defines repository instructions for automated coding agents working in `z-platform`.

## Mission

Help evolve `z-platform` as a clean, security-first successor to `cvsz/zeaz-platform` while preserving explicit platform boundaries, gateway-only AI access, durable orchestration, and production readiness gates.

## Required reading

Before changing code, read the relevant files:

- `README.md`
- `docs/project/project-overview.md`
- `docs/requirements/master-requirements.md`
- `docs/architecture/README.md`
- `docs/migration/execution-plan.md`
- `docs/migration/manifest.md`
- `docs/operations/production-master.md`
- `SECURITY.md`

## Non-negotiable rules

- Do not commit secrets, provider keys, service tokens, wallet keys, MPC shares, card data, KYC payloads, or production identifiers.
- Do not expose upstream provider credentials to browsers, IDE clients, generated projects, logs, traces, or tests.
- Keep AI provider access behind `services/ai-gateway`.
- Do not install files, scripts, or configurations outside the `z-platform` directory (e.g., avoid `/opt`, `/usr/local`, or `$HOME/.config`). The stack must remain standalone.
- Keep mutating agent jobs behind explicit approval state and scoped tool grants.
- Keep workspace shell and deployment behind explicit `shell` or `deploy` approval grants.
- Keep ZWallet limited to billing-ledger adapter behavior; reject signing, cards, KYC, MPC, and swaps.
- Do not apply production infrastructure from an agent without operator approval.

## Work style

- Prefer small, reviewable changes.
- Match existing package style and tests.
- Add or update tests for success, failure, authorization, timeout, and denial paths when behavior changes.
- Update docs when architecture, operations, migration status, requirements, or security boundaries change.
- Keep generated files reproducible and free of secret-bearing paths.

## Validation expectations

Run the relevant package tests locally when available. GitHub Actions must remain the release gate for CI, validation, secret scanning, dependency policy, SBOM generation, and provenance verification.

## Production changes

Production-affecting work must reference:

- `docs/operations/production-master.md`
- `docs/operations/staging-readiness.md`
- `docs/requirements/master-requirements.md`

Production traffic remains blocked until operator approval is recorded outside automated agent execution.
