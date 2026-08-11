# PR #232 Mergeability Repair

## Language and Coding Standards
- **Communication**: Always talk in Thai when interacting with users.
- **Code & Technical Assets**: All code, comments, documentation, and technical definitions must be in English.

Repository:
cvsz/zeaz-platform

Local path:
/home/zeazdev/zeaz-platform

Target PR:
#232 Fix/cloudflare multi environment separation

Branch:
fix/cloudflare-multi-environment-separation

Goal:
Make PR #232 mergeable against current main and safe to merge.

Workflow:
1. Ensure main is current:
   git checkout main
   git fetch origin main
   git pull --ff-only origin main

2. Checkout PR branch:
   git checkout fix/cloudflare-multi-environment-separation

3. Check branch state:
   git status -sb
   git log --oneline --left-right --graph origin/fix/cloudflare-multi-environment-separation...HEAD

4. If not rebased:
   git fetch origin main
   git rebase origin/main

5. Resolve conflicts safely:
   - For Cloudflare environment docs/config add/add conflicts, prefer the PR branch version only when it preserves intended multi-environment separation work.
   - For validate-cloudflare-config.sh conflict, inspect both sides and preserve both risk scoring and environment validation behavior if possible.
   - Do not blindly discard main changes if they contain newer validation logic.
   - If manual merge is needed, create a combined version.

6. Validate:
   - bash -n infra/cloudflare/scripts/*.sh
   - run infra/cloudflare/scripts/validate-cloudflare-config.sh if safe/offline
   - run any scan-cloudflare scripts in dry-run/read-only mode

7. Run full gates:
   pnpm -r run lint
   pnpm -r run test
   pnpm -r run build

8. Commit any additional fixes with explicit paths.

9. Push:
   git push --force-with-lease origin fix/cloudflare-multi-environment-separation

10. Output:
   - final head SHA
   - commands passed
   - exact PR status recommendation

Never use git add .
Never force push without --force-with-lease.
Never bypass ECC.
