---
name: zworkforce-policy-audit
description: Audit zWorkforce tenant policy, RBAC, scopes, API keys, proxy identity, approval gates, agent tool grants, signed skills, MCP allowlists, SSRF defenses, shell execution limits, memory isolation, and audit-chain integrity.
---

# zWorkforce Policy Audit

Assume policy errors are production blockers until proven otherwise.

## Audit Path

1. Identify tenant, actor, roles, scopes, agent, skill IDs, mutating intent, and
   requested tools.
2. Trace enforcement across API, database, engine, tools, policy, identity,
   secret store, and audit code.
3. Verify deny precedence and fail-closed behavior.
4. Confirm approval behavior distinguishes `requires_approval_for_mutations`,
   `required_approvals`, and `approval_tools`.
5. Check signed remote skill behavior and registry allowlists.
6. Validate that audit events capture enough evidence without leaking secrets.

## Evidence Files

Start with:

- `docs/THREAT-MODEL.md`
- `docs/IDENTITY.md`
- `docs/SECRET-MANAGEMENT.md`
- `docs/MCP.md`
- `zworkforce/policy.py`
- `zworkforce/tools.py`
- `zworkforce/identity.py`
- `zworkforce/skills.py`
- related tests under `tests/`

## Output

Classify issues as blocking, high, medium, or low. Include a concrete exploit or
failure mode for blocking and high findings.
