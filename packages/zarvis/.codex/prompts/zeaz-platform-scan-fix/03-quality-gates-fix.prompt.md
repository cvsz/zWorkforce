# ZEAZ Quality Gates Fix

## Language and Coding Standards
- **Communication**: Always talk in Thai when interacting with users.
- **Code & Technical Assets**: All code, comments, documentation, and technical definitions must be in English.

Goal:
Make these pass without bypassing:
- pnpm -r run lint
- pnpm -r run test
- pnpm -r run build

Rules:
- Fix root causes.
- Do not delete tests.
- Do not no-op build scripts.
- Do not disable lint globally.
- Do not change unrelated application behavior.
- Keep changes minimal and scoped.

Process:
1. Run `pnpm -r run lint`.
2. If it fails:
   - Identify package.
   - Fix exact package config/source.
   - Re-run package lint.
   - Re-run full lint.
3. Run `pnpm -r run test`.
4. If it fails:
   - Identify stale assertion vs real regression.
   - If UI changed intentionally, align test to stable accessible text/roles.
   - If real bug, fix component.
   - Re-run single failing test.
   - Re-run full tests.
5. Run `pnpm -r run build`.
6. If it fails:
   - Identify exact app.
   - Fix config/source/dependency issue.
   - Re-run package build.
   - Re-run full build.

Commit strategy:
- One commit per logical fix.
- Use explicit git add paths only.
- Suggested commit messages:
  - fix(zcloud): make eslint config compatible with ESLint 9
  - test(zdash): align app routing assertions with current UI
  - fix(ztrader): configure Next workspace build root

Final output:
- Commands run
- Files changed
- Pass/fail table
- Remaining risks
