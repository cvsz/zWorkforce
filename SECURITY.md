# Security

## Security properties

- Provider, database, vector-store and object-store credentials remain server-side.
- API keys are stored as salted PBKDF2-HMAC-SHA256 verifiers; legacy unsalted
  SHA-256 records are rejected and must be recreated/rotated. Generated
  secrets are shown once.
- OIDC verifies signature, issuer, audience and required timestamps and accepts asymmetric signing algorithms only.
- SAML should terminate at a mature IdP/proxy; zWorkforce verifies the proxy identity with an HMAC timestamped boundary rather than implementing its own SAML parser.
- Tenant context is resolved from authenticated identity; only superadmin may switch tenant using `X-Tenant-ID`.
- Four-eyes approvals prevent a task requester from satisfying their own approval requirement.
- Policy-as-code can deny task classes or tools in addition to agent grants.
- Mutating tools require explicit mutating task intent and completed approvals where configured.
- Shell execution is disabled by default, uses `shell=False`, an executable allowlist, bounded arguments/output/time and sanitized environment variables.
- Workspace paths are rooted; writes are atomic.
- HTTP tools use hostname allowlists, DNS/IP validation, redirect revalidation and private/non-routable address denial by default.
- Artifacts are SHA-256 content addressed and verified on read.
- Remote MCP/skill/embedding/Qdrant endpoints require HTTPS except explicit localhost development endpoints.
- Per-tenant audit events are SHA-256 chained for tamper evidence.
- Request/auth rate limits, request-size caps, CSP, no-frame and no-sniff headers are enabled.
- Containers run non-root, drop Linux capabilities and support read-only root filesystems.
- Kubernetes manifests start with default-deny ingress and egress.

## Secrets

Use long random bootstrap API keys. Prefer mounted files, Vault or AWS Secrets Manager references rather than plain Compose environment values where supported.

Reference schemes:

```text
env://NAME
file:///run/secrets/name#field
aws-sm://secret-id#field
vault://mount/path#field
```

Never commit `.env`, provider tokens, database passwords, OIDC client secrets or signing keys.

## PostgreSQL

Require TLS for remote database connections, private network placement, least-privilege credentials, encrypted backups and PITR. zWorkforce handles distributed task locking; it does not replace database HA controls.

## Egress

Application DNS checks reduce SSRF risk but do not prevent all DNS rebinding/network-path attacks. High-assurance deployments must enforce egress at network/firewall/service-mesh level.

## MCP and integrations

Treat remote MCP servers and webhook destinations as third-party execution boundaries. Use scoped tokens, HTTPS, network allowlists and tenant-specific policy. The webhook outbox signs payloads when a signing secret is configured; consumers should validate the delivery ID and signature and make handlers idempotent.

## Reporting vulnerabilities

Do not publish secrets or exploit details in a public issue. Use the repository's private security-reporting channel when enabled, or contact the repository owner privately.
