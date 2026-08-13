# Repository Memory

This file captures durable Z.A.R.V.I.S. project context for maintainers and coding agents. It is not a place for secrets, credentials, private user data, provider keys, payment data, wallet keys, KYC payloads, or production identifiers.

## Project Identity

- Repository: `cvsz/zWorkforce`
- Package: `packages/zarvis`
- Project type: security-first Z.A.R.V.I.S. assistant suite
- Production posture: blocked until operator approval and staging readiness sign-off

## Stable Decisions

- Browser and desktop clients must not receive provider secrets or service tokens.
- Tool execution requires allowlisted adapters, approval state, scoped action grants, timeout handling, and audit events.
- Memory, perception, and proactive workflows require explicit consent and retention controls.
- Realtime voice keeps short-lived session tickets at the gateway boundary.
- Non-Z.A.R.V.I.S. product surfaces and legacy platform services are intentionally out of scope for this package.

## Canonical Documents

- `README.md`
- `docs/requirements/master-requirements.md`
- `docs/architecture/README.md`
- `docs/architecture/zarvis.md`
- `SECURITY.md`

## Update Rules

Update this file only for durable project facts. Do not record temporary plans, secrets, credentials, personal data, or speculative decisions.
