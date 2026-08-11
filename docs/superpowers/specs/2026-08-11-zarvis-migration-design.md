# Z.A.R.V.I.S. Migration Design

## Goal

Make `cvsz/zWorkforce` the new source of truth for the complete Z.A.R.V.I.S. system under `packages/zarvis/`, without deleting the existing implementation from `cvsz/z-platform`.

## Architecture

Z.A.R.V.I.S. remains a self-contained pnpm monorepo nested inside the Python-based zWorkforce repository. Its internal application, service, contract, deployment, documentation, and test paths remain stable relative to `packages/zarvis/`. zWorkforce does not import Node modules directly; integration occurs through Z.A.R.V.I.S. HTTP and event contracts.

The migrated workspace contains the complete z-platform source snapshot needed to build and operate Z.A.R.V.I.S., excluding Git metadata and repository-only generated state. This avoids hidden dependencies on files left in z-platform. A provenance document records the final source commit and declares zWorkforce authoritative.

## Repository Integration

- Destination: `packages/zarvis/`
- Source of truth after merge: `cvsz/zWorkforce`
- Former source: retained unchanged as a rollback reference
- Root CI: a path-filtered workflow validates the nested pnpm workspace
- Existing Python, Docker, and Windows zWorkforce workflows remain unchanged
- Z.A.R.V.I.S. release workflows are retained as documentation/templates inside the nested workspace; repository-level execution is handled by the new root workflow

## Validation

The migration must prove that the nested workspace installs with its lockfile, runs its full test suite, and does not contain source-repository Git metadata. Existing zWorkforce checks must continue to pass. A manifest test verifies the required Z.A.R.V.I.S. applications, services, contracts, deployment files, and operations scripts exist at the destination.

## Rollback

The migration is additive. Reverting the migration commit removes `packages/zarvis/` and its root workflow without modifying existing zWorkforce runtime behavior. The retained z-platform copy remains available during production validation.
