# Z.A.R.V.I.S. Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the complete Z.A.R.V.I.S. system into `packages/zarvis/` and make zWorkforce its source of truth.

**Architecture:** Preserve Z.A.R.V.I.S. as a self-contained pnpm monorepo nested in zWorkforce. Add a root path-filtered CI workflow and a migration manifest test so the boundary is independently buildable and verifiable.

**Tech Stack:** Node.js 22, pnpm 11, .NET 10, Docker Compose, GitHub Actions, Python 3.12+

## Global Constraints

- All migrated source lives below `packages/zarvis/`.
- No runtime dependency on a checkout of `cvsz/z-platform`.
- Do not delete or modify the original z-platform repository.
- Preserve existing zWorkforce Python runtime behavior.
- zWorkforce becomes the authoritative source after merge.

---

### Task 1: Migration Boundary Contract

**Files:**
- Create: `tests/test_zarvis_package.py`
- Create: `packages/zarvis/MIGRATION.md`

- [ ] Write a failing Python test asserting all required destination paths and provenance metadata.
- [ ] Run `python -m unittest tests.test_zarvis_package -v` and confirm it fails because `packages/zarvis` is absent.
- [ ] Add the migration provenance document and nested source tree.
- [ ] Re-run the test and confirm it passes.

### Task 2: Self-Contained Nested Workspace

**Files:**
- Create: `packages/zarvis/package.json`
- Create: `packages/zarvis/pnpm-workspace.yaml`
- Create: `packages/zarvis/pnpm-lock.yaml`
- Create: `packages/zarvis/apps/**`
- Create: `packages/zarvis/services/**`
- Create: `packages/zarvis/packages/**`
- Create: `packages/zarvis/scripts/**`
- Create: `packages/zarvis/docs/**`
- Create: `packages/zarvis/ops/**`
- Create: `packages/zarvis/compose*.yml`

- [ ] Copy the source snapshot without `.git`, generated artifacts, dependencies, secrets, or local runtime data.
- [ ] Run `corepack pnpm --dir packages/zarvis install --frozen-lockfile`.
- [ ] Run `corepack pnpm --dir packages/zarvis test`.

### Task 3: Repository CI Integration

**Files:**
- Create: `.github/workflows/zarvis.yml`

- [ ] Add a path-filtered workflow for `packages/zarvis/**`.
- [ ] Validate YAML parsing and action versions.
- [ ] Run the migration contract test and existing `make check`.
- [ ] Commit the complete migration and open a PR targeting `main`.
