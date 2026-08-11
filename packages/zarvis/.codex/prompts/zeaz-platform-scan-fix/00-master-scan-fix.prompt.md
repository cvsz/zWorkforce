# ZEAZ Platform — Omega Scan & Fix Master Prompt

## Language and Coding Standards
- **Communication**: Always talk in Thai when interacting with users.
- **Code & Technical Assets**: All code, comments, documentation, and technical definitions must be in English.

You are operating inside the repository:

/home/zeazdev/zeaz-platform

Goal:
Scan, diagnose, and fix all blocking issues that prevent this repository and the current working branch from passing local quality gates and becoming safe to push/merge.

Current high-priority context:
- The repo is cvsz/zeaz-platform.
- The active branch may be fix/cloudflare-multi-environment-separation.
- Recent work rebased PR #232 onto current main.
- Lint passed.
- Tests passed.
- The remaining known blocker is build failure in apps/ztrader/frontend.
- The build failure is caused by Next.js / Turbopack inferring the project root incorrectly and treating apps/ztrader/frontend/src/app as the project directory.
- Do not bypass ECC, tests, lint, or build gates.
- Do not disable security scanners.
- Do not use git add .
- Do not commit secrets, .env files, credentials, tokens, key files, tfstate, or tfvars.
- Do not force push except `git push --force-with-lease` after a confirmed rebase.
- Fix root causes, not symptoms.
- Keep changes minimal, focused, and reviewable.

Hard safety rules:
1. Never run `git add .`.
2. Never use `git reset --hard` unless a backup branch and explicit backup archive are created first.
3. Never delete large app directories to make builds pass.
4. Never replace real tests with empty/no-op tests.
5. Never change production domains, Cloudflare tunnel IDs, secrets, or credentials unless using documented placeholders.
6. Never commit generated build logs.
7. If a file looks sensitive, leave it untracked and update .gitignore only if appropriate.
8. Prefer fixing package/config/test expectations over bypassing scripts.

Required workflow:

Phase A — Preflight
- Print current branch.
- Print git status.
- Confirm no unmerged files.
- Confirm upstream tracking.
- Save a preflight report under reports/agent/omega-scan-fix/.
- Save command outputs but do not commit logs unless explicitly safe markdown/json reports.

Phase B — Inventory
- Inspect package.json, pnpm-workspace.yaml, workspace package scripts.
- Identify all apps and services with lint/test/build scripts.
- Detect Next.js apps and their next.config files.
- Detect ESLint 9 configs.
- Detect TypeScript configs.
- Detect Cloudflare config scripts and validation scripts.
- Detect build logs, generated reports, cache dirs, and sensitive paths.

Phase C — Quality Gate Reproduction
Run, in order:
- pnpm -r run lint
- pnpm -r run test
- pnpm -r run build

If a command fails:
- Capture the exact failing package, script, command, and root error.
- Fix the root cause.
- Re-run the smallest failing command first.
- Re-run the full gate after targeted fix passes.

Phase D — Known ztrader Next/Turbopack Build Fix
Investigate apps/ztrader/frontend:
- package.json
- next.config.mjs/js/ts
- tsconfig.json
- src/app layout/page structure
- node_modules visibility from package root
- whether Next is invoked from repo root or package root
- whether Next 16 requires explicit turbopack.root
- whether multiple lockfiles cause wrong workspace inference

Fix requirements:
- Add or update apps/ztrader/frontend/next.config.mjs.
- Set turbopack.root to the actual frontend package directory unless repo root is demonstrably required.
- Set outputFileTracingRoot appropriately.
- Keep build script explicit if needed.
- Do not make build a no-op.
- Verify `pnpm --filter ztrader-frontend run build` passes.

Phase E — zcloud ESLint Guard
Confirm apps/zcloud:
- package.json lint script uses eslint, not next lint.
- eslint.config.mjs does not use FlatCompat with next/core-web-vitals if it triggers circular config.
- `pnpm --filter @zeaz/zcloud run lint` passes.

Phase F — zdash Tests Guard
Confirm apps/zdash/frontend:
- App routing tests match current UI.
- Do not remove route coverage.
- Verify `pnpm --filter zdash-frontend exec vitest --run src/tests/App.test.tsx --passWithNoTests`.
- Verify full `pnpm --filter zdash-frontend run test`.

Phase G — Cloudflare PR #232 Validation
For Cloudflare docs/config changes:
- Run shell syntax checks on infra/cloudflare/scripts/*.sh.
- Run existing Cloudflare validation scripts if present.
- Validate YAML files in infra/cloudflare/environments if tooling exists.
- Ensure no real tokens or credentials are introduced.
- Keep docs and scripts consistent.

Phase H — Final Gate
Run:
- pnpm -r run lint
- pnpm -r run test
- pnpm -r run build

Then run:
- git status -sb
- git diff --stat
- git diff --name-only
- git diff --check

Phase I — Commit
Stage explicit files only.
Do not use git add .
Use focused commits:
- fix(ztrader): configure Next workspace build root
- fix(zcloud): align ESLint 9 config
- test(zdash): align routing assertions with current UI
- docs/cloudflare: validate multi-environment config

If files are unrelated, split commits.
If only one cohesive fix remains, use one commit.

Phase J — Push Readiness
Before push:
- Confirm no untracked build logs.
- Confirm no sensitive files.
- Confirm branch relation to upstream.
- If branch was rebased, use:
  git push --force-with-lease origin <branch>
- Otherwise use:
  git push origin <branch>

Output required:
- Summary of root causes found.
- Files changed.
- Commands run and pass/fail result.
- Remaining risks.
- Exact next command for user.
