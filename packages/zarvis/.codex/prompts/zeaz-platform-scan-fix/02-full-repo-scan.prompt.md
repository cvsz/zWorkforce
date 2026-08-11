# ZEAZ Platform Full Repo Scan

## Language and Coding Standards
- **Communication**: Always talk in Thai when interacting with users.
- **Code & Technical Assets**: All code, comments, documentation, and technical definitions must be in English.

Working directory:
/home/zeazdev/zeaz-platform

Run a full repository health scan and produce a concise report.

Scan categories:
1. Git state
   - branch
   - upstream
   - ahead/behind
   - unmerged files
   - untracked files
   - ignored sensitive files

2. Workspace/package health
   - root package.json
   - pnpm-workspace.yaml
   - all workspace packages
   - missing scripts
   - recursive lint/test/build behavior

3. Node/Next/React health
   - Next apps
   - next.config files
   - package versions
   - Turbopack root settings
   - ESLint 9 compatibility
   - TypeScript config

4. Python health
   - requirements files
   - compile checks
   - pytest if configured

5. Go health
   - go.mod packages
   - go test ./...
   - go vet ./...

6. Cloudflare infra health
   - infra/cloudflare/config
   - infra/cloudflare/environments
   - infra/cloudflare/scripts
   - tunnel/dns/worker docs
   - no real credentials

7. Security hygiene
   - no .env committed
   - no secrets/
   - no key files
   - no tfstate/tfvars
   - no creds.json
   - no generated logs staged

8. Build artifacts
   - reports/platform/build-logs
   - .next
   - dist
   - build
   - coverage
   - node_modules

Output:
- Write report to reports/agent/omega-scan-fix/full-repo-scan.md
- Do not commit report unless it is intentionally useful documentation.
- List all blockers with exact fix plan.
- Do not change files in this scan phase unless a trivial non-risky metadata correction is necessary.
