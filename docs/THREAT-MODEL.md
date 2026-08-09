# Threat Model

## Assets

Provider credentials, API keys, tenant data, workspace content, memory, task/audit history, compute budgets and mutating tool authority.

## Prompt/tool injection

Model output cannot directly execute arbitrary capabilities. The worker exposes only granted tool schemas and re-validates tool name, mutating flag, approval state, filesystem root, host allowlist and command allowlist at execution.

## Cross-tenant access

Tenant derives from authenticated identity and v2 data queries are tenant-scoped. Only superadmin can explicitly switch tenant context. Worker/tool execution uses the tenant persisted on the claimed task.

## SSRF

Outbound HTTP is disabled until hosts are allowlisted. URL credentials are rejected, redirects are revalidated and DNS answers to private/non-routable ranges are rejected by default. DNS rebinding cannot be fully eliminated by application preflight alone, so high-assurance deployments should enforce network egress through a policy proxy/firewall.

## Command injection and secret theft

No shell command string is evaluated. `subprocess.run` receives an argv list with `shell=False`; executable names are allowlisted and child processes receive a sanitized environment instead of inherited provider/API credentials.

## Runaway compute

Iterations, attempts, sub-agents, delegation depth, tool time/output, request sizes and credits are bounded. Provider circuits reduce retry storms.

## Approval bypass

Mutating tasks enter `waiting_approval` when policy requires it. Requesters cannot approve themselves, approvers are unique and the worker rechecks mutation policy before tool execution.

## Audit modification

Per-tenant audit events form a SHA-256 chain. This detects ordinary database edits but cannot stop a fully privileged attacker from rewriting the entire chain. Export to immutable storage for stronger assurance.

## Worker crash

Claims have leases and heartbeats. Stale work is transactionally requeued and eventually dead-lettered rather than silently disappearing.
