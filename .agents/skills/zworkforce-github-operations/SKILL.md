---
name: zworkforce-github-operations
description: Operate zWorkforce GitHub pull requests, review threads, branches, checks, releases, GHCR packages, repository settings, Dependabot, CodeQL, and workflow failures. Use when inspecting or changing GitHub state for cvsz/zWorkforce.
---

# zWorkforce GitHub Operations

Prefer GitHub API or `gh` with the configured `GH_CONFIG_DIR` when local shell
access is available.

## Local Defaults

```powershell
$env:GH_CONFIG_DIR='C:\Users\cvsz\.config\gh'
C:\Users\cvsz\tools\bin\gh.exe auth setup-git
```

Use HTTPS/API operations when SSH to `github.com:22` is blocked.

## Workflow

1. Inspect PR state, review threads, check suites, mergeability, branch, and
   latest commit before acting.
2. Resolve review threads only after the underlying issue is fixed and pushed.
3. Merge only when required checks are green and the target branch is correct.
4. Delete remote branches only after merge or explicit owner direction.
5. For releases/packages, verify exact tag, asset, image digest, and package
   owner before deletion or mutation.

## Safety

Never delete branches, releases, packages, or assets based only on names in a
conversation. Re-read current GitHub state immediately before mutation and
report the exact object acted on.
