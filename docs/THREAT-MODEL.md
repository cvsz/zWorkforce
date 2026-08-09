# Threat model

## Assets
Provider credentials, tenant data, prompts/results, workspace files, artifacts, memory, audit history, API keys, OIDC identity and execution capabilities.

## Trust boundaries
- client -> API/MCP;
- API/worker -> database;
- runtime -> model providers;
- runtime -> tool/network destinations;
- runtime -> secret/object/vector stores;
- identity -> OIDC/JWKS or signed proxy;
- telemetry/outbox -> external collectors/consumers.

## Principal threats and controls

| Threat | Controls |
|---|---|
| Cross-tenant data access | authenticated tenant context, tenant predicates, superadmin-only switching |
| Credential disclosure | server-side secrets, salted PBKDF2 API-key verifiers, secret refs, static asset scans |
| Prompt-triggered mutation | agent grants, mutation declaration, approvals, policy-as-code, capability flags |
| Shell injection | `shell=False`, executable allowlist, bounded args/env/time/output |
| SSRF | host allowlist, DNS/IP validation, redirect checks, network egress policy |
| Duplicate distributed execution | DB transactions, task leases, idempotency keys, `SKIP LOCKED` |
| Duplicate schedules/webhooks | service leader leases, event dedupe, delivery IDs |
| Audit tampering | per-tenant hash chain and verification |
| JWT algorithm/key confusion | OIDC discovery/JWKS, issuer/audience checks, asymmetric algorithms only |
| Artifact tampering | SHA-256 content addressing and read verification |
| Malicious remote skill/MCP | HTTPS, signatures/scoped auth, host allowlist, policy/RBAC |
| Resource exhaustion | rate limits, request/tool/output/iteration/retry/delegation/spend bounds |

## Residual risks
Application-level DNS validation cannot fully defeat network rebinding; enforce egress externally. External model/MCP/storage/IdP services are separate trust domains. PostgreSQL availability/backup and multi-region consistency depend on deployment infrastructure.
