# Roadmap

This roadmap summarizes the expected direction of `z-platform`. Detailed requirements live in `docs/requirements/master-requirements.md`; production gates live in `docs/operations/production-master.md`.

## Completed foundation

- Security-first repository baseline.
- Migration manifest and execution plan.
- AI Gateway boundary.
- Gateway-backed ZAI Coder web and CLI paths.
- Model catalog, upload adapters, attachment adapters, streaming, and workspace metadata boundary.
- Agent orchestration job lifecycle, approval, queue, sandbox, retry, cancellation, and audit boundaries.
- ZChat gateway-only migration.
- ZAI Factory generator and template validation.
- ZOW and workspace runtime split.
- Billing ledger usage, credits, invoice intents, and ZWallet denial boundary.
- Platform operations docs, CI expansion, dependency checks, SBOM, and provenance workflow.
- Master requirements, project overview, and production master documents.

## Near-term roadmap

1. Verify GitHub Actions result visibility for current workflows.
2. Assign product, platform, security, operations, billing, and operator owners.
3. Select production providers for identity, Cloudflare Access, secrets, database, queue, sandbox, observability, audit, billing, and backups.
4. Run staging readiness review against selected providers.
5. Add deployment-specific smoke tests for gateway, chat, upload, workspace metadata, agent lifecycle, workspace runtime, billing ledger, and ZWallet denial paths.
6. Record rollback playbooks per deployable service.

## Production readiness roadmap

- Configure protected branch rules and required checks.
- Verify secret scanning and dependency policy in GitHub Actions.
- Publish SBOM and provenance artifacts for release commits.
- Validate staging restore from backups.
- Confirm logs, metrics, traces, and alerts for every deployed service.
- Complete operator approval before external traffic.

## Later roadmap

- Expand audited generator templates after review.
- Add more provider adapters through the AI Gateway only.
- Add richer tenant administration and usage reporting.
- Add production deployment automation that plans by default and applies only with operator approval.
- Add release notes generated from requirement and migration references.
