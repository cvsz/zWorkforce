---
name: zworkforce-skill-registry-governance
description: Govern the zWorkforce signed remote skill registry, including manifest validation, HMAC signature verification, HTTPS host allowlisting, redirect handling, and install audit trail.
---

# zWorkforce Skill Registry Governance

Only let trusted, verifiable skills into a tenant's agent runtime.

## Workflow

1. Verify the skill manifest validates against the schema (DNS-like id,
   bounded version string, well-formed `allowed_tools`, bounded
   `system_prompt_append`) before considering installation.
2. Verify the manifest's HMAC signature against the configured signing key
   when signature enforcement is required; reject unsigned or invalid
   signatures rather than installing with a warning.
3. Confirm the registry URL is HTTPS, has no embedded userinfo, and resolves
   to an allowlisted host and a public (non-private, non-loopback,
   non-link-local) address.
4. Re-validate host allowlisting and public-address checks on every redirect
   hop, and cap redirect depth.
5. Confirm every install is recorded in the audit trail with source URL,
   version, and actor before treating a skill as active for a tenant.

## References

- `zworkforce/skill_registry.py`
- `zworkforce/skills.py`
- `docs/SECRET-MANAGEMENT.md`
- `docs/THREAT-MODEL.md`

## Output

Report manifest validation result, signature verification status, host/redirect
checks performed, and audit trail confirmation for each install reviewed.
