# Security Policy

Security fixes target the latest `2.x` release line.

## Trust boundaries

- Browser/UI is untrusted and never receives provider secrets.
- API keys authenticate at the control-plane boundary and are stored as SHA-256 digests.
- Tenant comes from authenticated identity; cross-tenant switching is restricted to `superadmin`.
- Model output and provider responses are untrusted.
- Tool arguments are validated again at execution.

## Mutation controls

A mutating tool requires the server capability to be enabled, an agent grant, a task explicitly marked mutating, completed distinct approvals where required, and a task that is not canceled or over budget. The requester cannot approve/reject their own mutating task.

## Shell

Shell is disabled by default. When enabled it uses `shell=False`, a command allowlist, bounded arguments/time/output, fixed workspace cwd and a sanitized environment containing only explicitly allowed variable names. Provider/API secrets are not inherited unless an operator deliberately allowlists them.

## HTTP / SSRF

HTTP tools are deny-by-default and require a hostname allowlist. URL credentials are rejected. DNS answers resolving to private, loopback, link-local, multicast, unspecified or reserved addresses are rejected unless private access is explicitly enabled. Automatic redirects are disabled and allowed redirects are revalidated hop-by-hop.

DNS preflight materially reduces SSRF risk but is not equivalent to a dedicated egress proxy that pins destination IPs. High-assurance environments should add network egress policy.

## Skills

Skill manifests can be HMAC signed. In production, configured signing keys enable signature enforcement. Rotate signing keys by re-signing trusted manifests.

## Audit

Audit events are per-tenant hash chained and can be verified with `zworkforce audit-verify --tenant <id>`. For resistance to host compromise, forward audit/log events to immutable external storage.

## Reporting

Do not open a public issue for an exploitable vulnerability. Use the repository owner's private security reporting channel when available and include version, impact, reproduction and mitigation details.
