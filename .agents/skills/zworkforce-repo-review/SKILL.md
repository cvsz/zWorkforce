---
name: zworkforce-repo-review
description: Review zWorkforce repository changes for correctness, security, regressions, missing tests, documentation drift, release risk, and production-readiness gaps. Use for PR review, broad repo health checks, Markdown/API/doc coverage review, Python service changes, Windows client changes, and packages/zarvis changes.
---

# zWorkforce Repo Review

Review like an owner. Lead with concrete findings and cite file paths, symbols,
commands, or docs that support each finding.

## Scope

1. Identify the changed surface with `git status`, `git diff --stat`, and
   targeted `rg` searches.
2. Read the nearest operational docs before judging behavior:
   `README.md`, `docs/PROMETA-MASTER.md`, `docs/API.md`,
   `docs/PRODUCTION-READINESS.md`, `docs/SECURITY.md` when present, and nested
   `packages/zarvis/AGENTS.md` for Z.A.R.V.I.S. work.
3. Inspect implementation and tests together. Treat untested security,
   migration, workflow, provider, approval, or release behavior as a finding.
4. Separate confirmed bugs from residual risk and missing evidence.

## Review Priorities

- Tenant isolation, RBAC/scopes, approval gates, policy-as-code, audit chain,
  SSRF, shell allowlists, secret handling, and remote skill trust.
- Durable execution: idempotency keys, retries, leases, dead letters, scheduler
  dedupe, outbox behavior, and rollback boundaries.
- Release integrity: version metadata, changelog, SBOM/checksum/provenance,
  GHCR/package assumptions, Windows artifacts, and GitHub Actions coverage.
- Documentation drift: public docs, examples, roadmap, upgrade notes, and API
  endpoints must match current behavior.

## Output

Return findings first, ordered by severity. For each finding include:

- path and tight line reference when available;
- observed behavior;
- expected behavior from code, tests, or docs;
- why it matters;
- suggested fix or missing test.

If there are no findings, say that clearly and list any validation that was not
run.
