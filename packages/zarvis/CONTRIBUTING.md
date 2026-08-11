# Contributing

Thank you for contributing to `z-platform`. This repository is a security-first platform migration, so contribution quality is measured by correctness, testability, reviewability, and respect for platform boundaries.

## Before you start

Read:

- `README.md`
- `AGENTS.md`
- `docs/project/project-overview.md`
- `docs/requirements/master-requirements.md`
- `docs/migration/execution-plan.md`
- `docs/migration/manifest.md`
- `SECURITY.md`

## Contribution rules

- Keep changes small and focused.
- Reference the relevant requirement ID, migration item, issue, or runbook.
- Do not commit secrets, production identifiers, provider keys, wallet keys, MPC shares, card data, KYC payloads, or payment credentials.
- Do not add direct browser access to upstream AI providers.
- Do not add wallet signing, card, KYC, MPC, or swap behavior to AI or billing paths.
- Do not add production infrastructure apply behavior without operator approval.

## Development workflow

1. Identify the target boundary: app, service, package, tool, docs, or workflow.
2. Implement the smallest independently testable change.
3. Add tests for success and failure behavior.
4. Add denial-path tests for auth, approval, unsafe payloads, unsupported providers, or forbidden capabilities when relevant.
5. Update docs if behavior, requirements, migration status, architecture, operations, or security posture changes.
6. Run relevant tests locally when possible.
7. Open a pull request or commit with a clear message.

## Testing expectations

Use package-local tests where available. CI is expected to run Node and Python runtime tests, validation, secret scanning, dependency checks, SBOM generation, and provenance verification.

## Pull request checklist

- [ ] Scope is focused.
- [ ] Relevant requirements or migration items are referenced.
- [ ] Tests were added or updated.
- [ ] Security boundaries were preserved.
- [ ] Docs were updated when behavior changed.
- [ ] No secrets or production identifiers are included.
- [ ] Rollback notes are clear for production-affecting changes.

## Production-affecting changes

Production-affecting changes require operator approval and must satisfy `docs/operations/production-master.md` and `docs/operations/staging-readiness.md`.
