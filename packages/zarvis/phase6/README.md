# Z Platform Phase 6 Server Installer

Deploys a real staging verification stack:

- Caddy with automatic public HTTPS
- Alert trigger and delivery-status API
- AI file upload API
- AI provider failover verification using two or more real providers
- SSE streaming endpoint
- Redis-backed external session verification
- Prometheus and Grafana
- Jaeger UI
- Script to populate GitHub `staging` Environment secrets

## Requirements

1. Ubuntu/Linux server with public ports 80 and 443.
2. Docker Engine and Docker Compose v2.
3. A real DNS A/AAAA record pointing `PHASE6_DOMAIN` to the server.
4. At least two enabled external AI provider accounts and real API keys.
5. GitHub CLI authenticated when running `scripts/configure-github.sh`.

## Install

```bash
cp .env.phase6.server.template .env.phase6.server
chmod 600 .env.phase6.server
nano .env.phase6.server

sudo ENV_FILE="$PWD/.env.phase6.server" ./server-installer.sh
```

Generated URL values are written to:

```text
$HOME/z-platform/phase6/phase6-generated.env
```

## Configure GitHub

```bash
chmod 750 scripts/configure-github.sh
REPO=cvsz/z-platform ./scripts/configure-github.sh
```

To create or update the GitHub Environments used by the phase 6 workflows:

```bash
chmod 750 scripts/configure-github-environments.sh
REPO=cvsz/z-platform \
  ./scripts/configure-github-environments.sh \
  --staging-reviewer user:LOGIN \
  --production-reviewer user:LOGIN
```

Replace the reviewer selectors with the actual user or team slugs authorized to approve `staging` and `production`.

The server-generated values are real deployed HTTPS endpoints. They do not replace the remaining requirements:

- real external backup create/restore/verify commands;
- deployed browser bundle and HAR;
- substantive human keyboard, screen-reader and responsive QA evidence;
- protected production approval.

## Security

- Never commit `.env.phase6.server`.
- Rotate any credential previously pasted into chat, logs, issues, or commits.
- Restrict server SSH and firewall access.
- Back up `phase6` volumes using the operator-approved external target.
