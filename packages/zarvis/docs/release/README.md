# Release Governance

Phase A establishes the human-readable governance records and machine-readable YAML templates used to move a release from pending staging verification to an explicitly approved production deployment. Phase B adds JSON Schemas and automated repository validation for those records.

## Records

- [Staging environment inventory](staging-environment-inventory.md)
- [External verification checklist](external-verification-checklist.md)
- [Staging review record](staging-review-record.md)
- [Operational ownership](operational-ownership.md)
- [Production release record](production-release-record.md)
- [Release state machine](release-state-machine.md)

## YAML templates

Templates are stored under `.github/release-templates/`:

- `staging-inventory.yaml`
- `external-verification.yaml`
- `staging-review.yaml`
- `operational-ownership.yaml`
- `production-release-record.yaml`
- `scripts/phase-6-operator-inputs.json`

These templates are governance records, not Kubernetes Custom Resources. Their JSON Schemas are stored under `schemas/release/`. Validation runs through `pnpm release:validate` and is also exercised by the repository test suite.

The validator enforces template-to-schema mappings, API version and kind consistency, required governance sections, JSON Schema draft selection, immutable-revision definitions, and rejection of explicit floating image references. Placeholder-bearing templates remain valid until instantiated; populated release records must replace placeholders before approval.

## Current gates

- `PENDING_EXTERNAL` remains until real external staging infrastructure is deployed and verified.
- `PENDING_OPERATOR` remains until reviewer, incident, rollback, release, and approval ownership is recorded.
- `READY_FOR_RELEASE` requires both `VERIFIED_EXTERNAL` and `APPROVED_OPERATOR` for the same immutable candidate.
- Production deployment additionally requires an explicit `GO` decision bound to the approved commit and image digests.
- Root repository CI, ZARVIS, Dependency Review, CodeQL, and Windows client checks must pass on the same commit.
- Node releases must pass `pnpm install --frozen-lockfile`, `pnpm peers check`, and `pnpm test`.
- ZARVIS API releases must pass route tests and a zero-vulnerability dependency audit.
- Windows-targeted projects must restore on Ubuntu and pass the native Windows packaging/smoke workflow.

## Current maintenance record

The current integrated dependency and verification summary is tracked in the
root [`CHANGELOG.md`](../../../../CHANGELOG.md) and the root
[`docs/GITHUB-OPERATIONS.md`](../../../../docs/GITHUB-OPERATIONS.md). Package-level
release records remain in this directory until an operator binds them to a
specific immutable candidate.
