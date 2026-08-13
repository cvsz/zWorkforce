# GitHub Operations

This document is the repository-facing operations runbook for
`github.com/cvsz/zWorkforce`. It covers GitHub controls and automation only;
runtime deployment and disaster recovery are covered by the other operations
documents.

## Branches and pull requests

- `main` is the only long-lived branch.
- Feature, fix, and maintenance branches must be short-lived and deleted after
  merge.
- Use reviewed pull requests for all production-impacting changes.
- Prefer signed commits for local work. Squash merges from GitHub are accepted
  when the merge commit is produced by GitHub and all required checks pass.
- Do not force-push `main` or reuse a release tag.

Before merging a pull request, verify:

1. CI, CodeQL, Dependency Review, and affected package workflows are green.
2. Review threads are resolved.
3. Documentation, release notes, and runbooks are updated when behavior,
   operations, workflows, packages, or security posture changed.
4. No credentials, private keys, customer data, generated secret files, or
   local environment files are committed.

## Required checks

The repository uses these GitHub Actions as release and merge evidence:

| Workflow | Purpose |
| --- | --- |
| `CI` | Python 3.12/3.13/3.14 tests, PostgreSQL integration, release integrity, container build, security invariants. |
| `ZARVIS` | Z.A.R.V.I.S. package migration contract, Node workspace tests, API tests/audit, Windows restore checks. |
| `Windows client` | Native client restore, build, core tests, MSIX package, launch smoke check, artifact upload. |
| `CodeQL Advanced` | Static analysis for Actions and Python surfaces. |
| `Dependency Review` | Blocks vulnerable or disallowed dependency changes in pull requests. |
| `Automatic Dependency Submission` | Submits dependency graph data for NuGet and related ecosystems. |

If a workflow is added, renamed, or removed, update this table and the pull
request template.

## Dependency maintenance

Dependabot coverage is declared in `.github/dependabot.yml` for:

- root Python package;
- GitHub Actions;
- root Docker build;
- `ZWorkforceClient` NuGet dependencies;
- `packages/zarvis` Node workspace;
- `packages/zarvis/services/zarvis-api` Python API dependencies;
- `packages/zarvis/tools/zctl` Go module;
- `packages/zarvis/apps/zarvis-windows` NuGet dependencies.

For dependency pull requests:

1. Read the upstream changelog/security advisory before merging major updates.
2. Keep peer dependency ranges compatible with accepted major versions.
3. Regenerate lockfiles only with the repository package manager.
4. Run the package-specific tests and audits named in the pull request
   template.
5. Close or supersede duplicate Dependabot PRs after a consolidated update
   lands.

## Security alerts

Triage GitHub security signals in this order:

1. Secret scanning alerts: rotate the exposed secret first, then remove the
   source and document the incident.
2. Code scanning alerts: reproduce the path locally, add a regression test
   when practical, and keep the alert open until the fix is merged.
3. Dependabot alerts: patch directly or merge the generated PR after CI passes.
4. Dependency Review failures: inspect the blocked package and decide whether
   to update, pin, replace, or explicitly reject the dependency.

Do not dismiss alerts as false positives without a short justification tied to
the exact code path or package version.

## Releases and packages

Stable release tags are `vX.Y.Z` and trigger `.github/workflows/release.yml`.
The release workflow verifies tag/version consistency, builds Python
distributions, produces checksums and a CycloneDX SBOM, attests provenance,
publishes the GHCR image, and creates or updates the GitHub Release.

The Windows MSIX release artifact is optional and requires trusted signing
secrets:

- `WINDOWS_MSIX_PFX_BASE64`
- `WINDOWS_MSIX_PFX_PASSWORD`
- optional `WINDOWS_MSIX_PUBLISHER`

If those secrets are absent, the Windows artifact job is skipped and the
release still publishes Python artifacts, checksums, SBOM, provenance, GHCR
images, and release notes. Invalid signing secrets fail the release instead of
publishing an untrusted package.

GHCR packages should be kept to immutable semantic tags and active operational
tags. Remove obsolete experimental images only after confirming no deployment,
release note, or rollback record references their digest.

## Repository cleanup

After merges:

```bash
git fetch --prune origin
git switch main
git pull --ff-only origin main
git branch --merged main
```

Delete local and remote branches that are merged and no longer needed. Keep
only `origin/main` as the default remote branch unless an active release,
hotfix, or incident branch is intentionally open.

## Incident evidence

When GitHub automation is part of an incident or release decision, record:

- pull request or workflow run URL;
- commit SHA and tag, if any;
- relevant check names and conclusions;
- artifact names and checksums;
- package image tag and digest;
- alert number, advisory ID, or CodeQL rule ID when applicable.
