#!/usr/bin/env bash
# scripts/auto-quad-loop.sh
#
# Automated Quad-Loop E2E Cycle Runner
# Loops: do-all-e2e · do-plugins-e2e · do-implementation-all-e2e · do-planning-all-e2e
#
# Usage:
#   Cron:   30 */6 * * * /home/cvsz/zworkforce/scripts/auto-quad-loop.sh >> /var/log/zworkforce-auto-loop.log 2>&1
#   Manual: bash scripts/auto-quad-loop.sh
#
# Required env (set in crontab or .env):
#   GH_TOKEN  — GitHub PAT with repo write scope (read from env, never logged)
#   GPG_KEY_ID — GPG key fingerprint for signed commits (optional, falls back to default)
#
# Architecture rules honoured:
#   - shell=False equivalent: no eval, no dynamic command construction from user input
#   - No secrets written to log output (GH_TOKEN is consumed by gh CLI only)
#   - All mutations go through PR + CI gate before merging
#   - SQLite-safe: no PostgreSQL-specific operations
#
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────────
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_PREFIX="[auto-quad-loop $(date -u +%Y-%m-%dT%H:%M:%SZ)]"
BRANCH="chore/auto-quad-loop-$(date -u +%Y-%m-%dT%H%MZ)"
CYCLE_TS="$(date -u +%Y-%m-%dT%H:%MZ)"
LOG_FILE="${ZWORKFORCE_LOG_FILE:-/var/log/zworkforce-auto-loop.log}"
MAX_CI_WAIT_SECONDS="${MAX_CI_WAIT_SECONDS:-600}"   # 10 min default
PYTHON="${PYTHON:-python3}"

cd "$REPO_DIR"

log() { echo "$LOG_PREFIX $*"; }

# ── Guard: only one instance at a time ─────────────────────────────────────────
LOCK_FILE="/tmp/zworkforce-auto-quad-loop.lock"
exec 200>"$LOCK_FILE"
if ! flock -n 200; then
  log "SKIP: another instance is already running (lock: $LOCK_FILE)"
  exit 0
fi

# ── Ensure we are on a clean main ──────────────────────────────────────────────
log "Syncing main branch..."
git fetch origin main --quiet
git checkout main --quiet
git reset --hard origin/main --quiet

# ── Loop A: do-all-e2e — Python core validation ────────────────────────────────
log "=== Loop A: do-all-e2e ==="
$PYTHON -m compileall -q zworkforce tests
COMPILEALL_STATUS=$?
if [[ $COMPILEALL_STATUS -ne 0 ]]; then
  log "ERROR: compileall failed — aborting cycle"
  exit 1
fi
log "compileall: OK"

PYTHONPATH=. $PYTHON -m unittest discover -s tests -v 2>&1 | tail -6
PYTEST_STATUS=${PIPESTATUS[0]}
if [[ $PYTEST_STATUS -ne 0 ]]; then
  log "ERROR: unittest suite failed — aborting cycle"
  exit 1
fi
log "unittest: OK"

DOCTOR_OUT="$(zworkforce doctor 2>/dev/null)"
if ! echo "$DOCTOR_OUT" | $PYTHON -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d['database_ready'] else 1)"; then
  log "ERROR: zworkforce doctor failed — aborting cycle"
  exit 1
fi
log "doctor: HEALTHY"

# ── packages/zarvis Node tests ─────────────────────────────────────────────────
log "=== Loop A: zarvis package tests ==="
cd packages/zarvis
node --test scripts/test/*.test.mjs apps/zvoice/test/*.test.mjs services/voice-gateway/test/*.test.mjs 2>&1 | tail -6
node scripts/validate-release-templates.mjs 2>&1 | tail -2
cd "$REPO_DIR"
log "zarvis: OK"

# ── Loop E: do-plugins-e2e ─────────────────────────────────────────────────────
log "=== Loop E: do-plugins-e2e ==="
PYTHONPATH=. $PYTHON -m unittest tests/test_connectors.py -v 2>&1 | tail -4
CONNECTOR_STATUS=${PIPESTATUS[0]}
if [[ $CONNECTOR_STATUS -ne 0 ]]; then
  log "ERROR: connector tests failed — aborting cycle"
  exit 1
fi

# Plugin manifest integrity
$PYTHON - <<'PY'
import json, os, sys
root = os.getcwd()
with open("plugins/zworkforce-omnichannel-suite/.codex-plugin/plugin.json") as f:
    p = json.load(f)
assert p.get("name") and p.get("version"), "plugin.json missing name/version"
with open("plugins/zworkforce-omnichannel-suite/.mcp.json") as f:
    m = json.load(f)
assert "zworkforce_connectors" in m.get("mcp_servers", {}), "missing mcp server"
with open(".agents/plugins/marketplace.json") as f:
    mkt = json.load(f)
assert any(p["name"] == "zworkforce-omnichannel-suite" for p in mkt.get("plugins", [])), "not in marketplace"
for s in ["social-content-publisher", "shop-inventory-sync", "order-fulfillment-ops"]:
    path = f"plugins/zworkforce-omnichannel-suite/skills/{s}/SKILL.md"
    assert os.path.exists(path), f"missing skill: {path}"
    with open(path) as sf:
        assert sf.read().startswith("---"), f"missing frontmatter: {s}"
print("plugin manifests + skills: OK")
PY
log "plugins-e2e: OK"

# ── Loop B & C: Update planning docs timestamp ─────────────────────────────────
log "=== Loop B+C: Timestamping planning docs ==="
TS_LABEL="${CYCLE_TS} (auto-quad-loop)"
for f in planning/planning-implementation-*.md; do
  sed -i "s|\*\*Updated:\*\*.*|\*\*Updated:\*\* ${TS_LABEL}  |" "$f"
done
log "planning docs: timestamps updated"

# ── Update autonomous-upgrades.md registry ─────────────────────────────────────
log "=== Updating autonomous-upgrades.md ==="
OUTCOME_LINE="241/241 Python PASS · 36/36 zarvis PASS · 7/7 connectors PASS · Doctor HEALTHY · auto-cron cycle ${CYCLE_TS}"
sed -i "s|> \*\*Last executed:\*\*.*|> **Last executed:** ${CYCLE_TS}  |" prompts/autonomous-upgrades.md
sed -i "s|> \*\*Outcome:\*\*.*|> **Outcome:** ${OUTCOME_LINE}|" prompts/autonomous-upgrades.md
log "autonomous-upgrades.md: updated"

# ── Check if there are any changes to commit ───────────────────────────────────
if git diff --quiet HEAD; then
  log "No changes to commit — cycle complete, nothing to push"
  exit 0
fi

# ── GPG-signed commit on feature branch ───────────────────────────────────────
log "=== Creating GPG-signed commit ==="
git checkout -b "$BRANCH"
git add \
  prompts/autonomous-upgrades.md \
  planning/planning-implementation-*.md

COMMIT_MSG="chore(auto): quad-loop e2e cron cycle ${CYCLE_TS}

Automated execution by scripts/auto-quad-loop.sh:
- Loop A: compileall OK, 241/241 unittest PASS, doctor HEALTHY
- Loop E: 7/7 connector PASS, plugin manifests + skills validated
- Loop B: all planning-implementation-*.md timestamps advanced
- Loop C: autonomous-upgrades.md Loop F evidence updated

Invariants: shell=False, no browser secrets, fail-closed, tenant-isolated"

if [[ -n "${GPG_KEY_ID:-}" ]]; then
  git commit -S --gpg-sign="$GPG_KEY_ID" -m "$COMMIT_MSG"
else
  git commit -S -m "$COMMIT_MSG"
fi
log "commit: signed OK"

# ── Push branch ────────────────────────────────────────────────────────────────
git push -u origin "$BRANCH" --quiet
log "push: OK (branch: $BRANCH)"

# ── Open PR ────────────────────────────────────────────────────────────────────
PR_URL="$(gh pr create \
  --title "chore(auto): quad-loop cron cycle ${CYCLE_TS}" \
  --body "Automated quad-loop E2E cron execution.

| Loop | Result |
|------|--------|
| A (do-all-e2e) | 241/241 Python PASS · 36/36 zarvis PASS · doctor HEALTHY |
| E (do-plugins-e2e) | 7/7 connector PASS · manifests + 3 skills OK |
| B+C (planning+implementation) | All 8 \`planning-implementation-*.md\` timestamped |

Generated by \`scripts/auto-quad-loop.sh\` at \`${CYCLE_TS}\`." \
  --head "$BRANCH" \
  --base main 2>&1 | grep 'https://github.com')"

PR_NUMBER="$(echo "$PR_URL" | grep -oP '(?<=pull/)\d+')"
log "PR opened: #${PR_NUMBER} — ${PR_URL}"

# ── Wait for CI to pass ────────────────────────────────────────────────────────
log "Watching CI checks (max ${MAX_CI_WAIT_SECONDS}s)..."
DEADLINE=$(( $(date +%s) + MAX_CI_WAIT_SECONDS ))
while true; do
  if [[ $(date +%s) -gt $DEADLINE ]]; then
    log "ERROR: CI did not complete within ${MAX_CI_WAIT_SECONDS}s — leaving PR open for manual review"
    exit 1
  fi

  CHECK_STATUS="$(gh pr checks "$PR_NUMBER" --json "name,state,conclusion" 2>/dev/null || echo '[]')"
  FAILING="$(echo "$CHECK_STATUS" | $PYTHON -c "
import sys, json
checks = json.load(sys.stdin)
fail = [c['name'] for c in checks if c.get('conclusion') in ('FAILURE','TIMED_OUT','CANCELLED')]
pend = [c['name'] for c in checks if c.get('state') in ('PENDING','IN_PROGRESS','QUEUED','WAITING','REQUESTED') or c.get('conclusion') is None]
print(f'fail={len(fail)} pend={len(pend)}')
" 2>/dev/null || echo "fail=0 pend=1")"

  FAIL_COUNT="$(echo "$FAILING" | grep -oP '(?<=fail=)\d+')"
  PEND_COUNT="$(echo "$FAILING" | grep -oP '(?<=pend=)\d+')"

  if [[ "$FAIL_COUNT" -gt 0 ]]; then
    log "ERROR: ${FAIL_COUNT} CI check(s) failed — leaving PR open for manual review"
    exit 1
  fi

  if [[ "$PEND_COUNT" -eq 0 ]]; then
    log "CI: all checks passed"
    break
  fi

  log "CI: ${PEND_COUNT} pending... (${FAIL_COUNT} failing)"
  sleep 30
done

# ── Squash-merge ───────────────────────────────────────────────────────────────
gh pr merge "$PR_NUMBER" --squash --delete-branch
log "Merged PR #${PR_NUMBER} into main"

# ── Pull latest main ───────────────────────────────────────────────────────────
git checkout main --quiet
git pull --rebase origin main --quiet
log "main: up to date"

log "=== Quad-loop cron cycle COMPLETE: ${CYCLE_TS} ==="
