# Security Policy

## Controls
- Production requires explicit API keys; keys are hashed in memory and compared in constant time.
- Roles: viewer < operator < admin.
- Provider credentials remain server-side.
- Shell is disabled by default, uses `shell=False`, separated args and a command allowlist.
- HTTP tool access requires a hostname allowlist.
- Workspace paths are canonicalized and cannot escape the configured root.
- Mutating tasks can require approval before agent execution.
- Request bodies are size-limited.
- Docker runs non-root, drops capabilities and sets `no-new-privileges`.

## Production checklist
Use long random secrets, TLS/private ingress, egress firewalling, narrow workspace permissions, explicit budgets, backups, external metrics/audit export and provider data-governance review.

Do not publish exploitable vulnerability details in public issues; use a private GitHub security channel when available.
