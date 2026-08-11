# Repository Memory

This file captures durable project context for maintainers and coding agents. It is not a place for secrets, credentials, private user data, provider keys, payment data, wallet keys, MPC shares, KYC payloads, or production identifiers.

## Project identity

- Repository: `cvsz/z-platform`
- Migration reference: `cvsz/zeaz-platform`
- Project type: security-first platform successor
- Production posture: blocked until operator approval and staging readiness sign-off

## Stable decisions

- AI provider access is gateway-only through `services/ai-gateway`.
- Browser clients must not receive provider secrets or service tokens.
- Agent jobs require durable state, queue-backed execution, approval state, scoped tools, sandbox limits, cancellation, retry idempotency, and audit events.
- Workspace shell and deploy require explicit approval grants.
- ZWallet is a billing-ledger adapter only.
- Billing receives usage, credits, and invoice intents only.
- Wallet signing, cards, KYC, MPC, and swaps are denied from AI and billing paths.
- Production external traffic waits for CI, observability, backups, identity, Cloudflare Access, and operator sign-off.

## Canonical documents

- `docs/project/project-overview.md`
- `docs/requirements/master-requirements.md`
- `docs/operations/production-master.md`
- `docs/migration/execution-plan.md`
- `docs/migration/manifest.md`
- `docs/architecture/README.md`
- `SECURITY.md`

## Update rules

Update this file only for durable project facts. Do not record temporary plans, secrets, credentials, personal data, or speculative decisions.
