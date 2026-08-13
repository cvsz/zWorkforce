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

## Non-Negotiable Rules

- Do not commit secrets, provider keys, service tokens, wallet keys, card data, KYC payloads, production identifiers, or private user data.
- Do not expose provider credentials to browsers, desktop clients, logs, traces, or tests.
- Keep tool execution behind explicit allowlists, approval state, and scoped action grants.
- Keep memory, perception, and proactive workflows behind consent and retention controls.
- Do not reintroduce non-Z.A.R.V.I.S. product surfaces or legacy platform services without a documented owner, tests, security review, and rollback path.
- Do not apply production infrastructure from an agent without operator approval.

## Work Style

- Prefer small, reviewable changes.
- Match existing package style and tests.
- Add or update tests for success, failure, authorization, timeout, and denial paths when behavior changes.
- Update docs when architecture, operations, requirements, or security boundaries change.
- Keep generated files reproducible and free of secret-bearing paths.

## Validation Expectations

Run the relevant package tests locally when available. GitHub Actions remain the release gate for CI, validation, secret scanning, dependency policy, SBOM generation, and provenance verification.
