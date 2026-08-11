# Fix ztrader Next.js / Turbopack Build Failure

## Language and Coding Standards
- **Communication**: Always talk in Thai when interacting with users.
- **Code & Technical Assets**: All code, comments, documentation, and technical definitions must be in English.

Repository:
/home/zeazdev/zeaz-platform

Known failure:
`pnpm --filter ztrader-frontend run build` fails with:

Next.js / Turbopack cannot find next/package.json because it infers project directory as:
apps/ztrader/frontend/src/app

Expected:
It must treat apps/ztrader/frontend as the Next.js project root.

Task:
1. Inspect:
   - apps/ztrader/frontend/package.json
   - apps/ztrader/frontend/next.config.*
   - apps/ztrader/frontend/tsconfig.json
   - apps/ztrader/frontend/src/app
   - pnpm-workspace.yaml
   - root package.json
2. Determine why Next is inferring src/app as project directory.
3. Fix without bypassing build.
4. Prefer a correct next.config.mjs using:
   - turbopack.root
   - outputFileTracingRoot
5. Adjust build script only if required.
6. Do not make build `exit 0`.
7. Verify:
   pnpm --filter ztrader-frontend run build
8. Run full pre-push gates:
   pnpm -r run lint
   pnpm -r run test
   pnpm -r run build
9. Stage explicit files only.
10. Commit with:
   fix(ztrader): configure Next workspace build root

Never use git add .
Never bypass ECC.
Never commit logs or secrets.
