# Production Readiness

This checklist defines the minimum release gate for a real zWorkforce production environment. Repository CI proves application behavior; operators must still prove their own infrastructure, identity, network and recovery controls.

## 1. Release integrity

- Deploy an immutable semantic-version image from `ghcr.io/cvsz/zworkforce:vX.Y.Z`; do not deploy `latest` in production.
- Verify `SHA256SUMS`, release provenance and the published SBOM.
- Confirm the deployed version matches `zworkforce --version` and `/health`.
- Keep production changes behind reviewed pull requests and required status checks.

## 2. Database

- Use PostgreSQL for multi-process or multi-host production.
- Enable TLS in transit and encrypted storage at rest.
- Run the database with a least-privilege application role; do not use a superuser from zWorkforce.
- Configure automated backups, retention and periodic restore drills.
- Define RPO/RTO and test them using `docs/DISASTER-RECOVERY.md`.
- Alert on storage pressure, connection exhaustion, lock contention and replication/backup failures.

## 3. Identity and authorization

- Disable development/bootstrap credentials after administrative bootstrap.
- Configure OIDC or a signed identity-aware proxy for human users.
- Validate issuer, audience, signing keys and group-to-role mappings in the production tenant.
- Require separate approvers for four-eyes operations.
- Keep superadmin identities rare and monitored.
- Review policy-as-code rules and tool grants before enabling mutating agents.

## 4. Secrets

- Store provider keys, database credentials, OIDC secrets, signing keys and webhook secrets outside Git.
- Prefer mounted secret files, Vault or AWS Secrets Manager references over plaintext environment values.
- Rotate bootstrap/API/provider/signing credentials on a documented cadence and immediately after suspected exposure.
- Ensure logs, traces and error exports are covered by redaction and data-retention controls.

## 5. Network

- Terminate TLS at an ingress/reverse proxy or service mesh.
- Keep the API private unless public exposure is required.
- Maintain default-deny egress and explicitly permit PostgreSQL, model providers, OIDC/JWKS, OTLP, approved HTTP tools, object/vector stores and remote registries.
- Restrict `/metrics` and administrative APIs to trusted networks/identities.
- Add WAF/rate limiting at the edge for internet-facing deployments.

## 6. Runtime isolation

- Run containers as non-root with read-only root filesystems, dropped capabilities and `no-new-privileges`.
- Keep shell execution disabled unless there is a documented workload requiring it.
- Mount only the workspace/artifact paths required by each deployment.
- Use separate service accounts and namespace/network policies in Kubernetes.
- Set CPU/memory requests and limits from measured workload data.

## 7. Providers and tools

- Configure at least one production provider and test circuit-breaker/failover behavior if multiple providers are configured.
- Use explicit model IDs supported by the provider; Luna/Terra/Sol are policy tiers, not provider guarantees.
- Review HTTP allowlists, remote skill registry allowlists and tool grants.
- Test provider credential redaction and error handling before traffic cutover.

## 8. Observability and FinOps

- Export traces/metrics to a durable backend.
- Alert on task failure/dead-letter rate, queue age, lease recovery, scheduler/outbox leadership, provider health and SLO violations.
- Configure budgets, chargeback/showback economics and capacity thresholds per tenant.
- Retain audit events according to compliance requirements and export them if local retention is insufficient.

## 9. Recovery and rollback

- Complete a PostgreSQL backup/restore drill before go-live.
- Verify application rollback to the previous immutable image without schema/data loss.
- Test provider outage, worker crash, scheduler failover and expired task lease recovery.
- Document the person/team authorized to declare incidents, restore databases and rotate secrets.

## 10. Go-live exit criteria

Production is ready only when all of the following are true:

1. `main` CI and CodeQL are green for the release commit.
2. Release artifacts, checksums, SBOM and provenance exist for the exact tag.
3. PostgreSQL backup and restore have been demonstrated in a non-production environment.
4. `zworkforce doctor` succeeds with production-equivalent configuration.
5. `scripts/smoke-test.sh` succeeds through the production ingress path.
6. Identity, policy, secret, egress and observability reviews are signed off by the operator.
7. Rollback and incident contacts are documented and tested.
