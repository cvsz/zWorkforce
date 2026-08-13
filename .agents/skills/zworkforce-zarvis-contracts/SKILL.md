---
name: zworkforce-zarvis-contracts
description: Validate and update the packages/zarvis Z.A.R.V.I.S. boundary, contracts, local assistant services, voice/session/task gateways, memory/perception/action services, zctl, Docker Compose files, release docs, and Windows client compatibility.
---

# zWorkforce Z.A.R.V.I.S. Contracts

Treat `packages/zarvis/` as an independently packaged product boundary inside
zWorkforce.

## Workflow

1. Read `packages/zarvis/AGENTS.md` before making changes.
2. Identify whether the change touches contracts, services, apps, zctl, local
   operations, release evidence, or Windows client compatibility.
3. Validate schemas and contract tests before changing service behavior.
4. Keep owner-domain, voice, memory, perception, task runtime, proactive, and
   action-gateway boundaries explicit.
5. Update package-local docs and root zWorkforce docs only when cross-boundary
   behavior changes.

## Evidence

Prefer package-local tests and scripts. For contract changes inspect:

- `packages/zarvis/packages/contracts/`
- `packages/zarvis/services/`
- `packages/zarvis/apps/`
- `packages/zarvis/docs/`
- `packages/zarvis/scripts/`
- `tests/test_zarvis_package.py`

## Output

Report changed package boundary, validation run, compatibility impact, and any
operator action needed for local Z.A.R.V.I.S. deployments.
