#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${CLOUDFLARE_ENV_FILE:-$ROOT/.env.cloudflare}"
CF_BIN="${CLOUDFLARED_BIN:-$ROOT/tools/bin/cloudflared}"

[[ -f "$ENV_FILE" ]] || { echo "Missing $ENV_FILE; copy .env.cloudflare.example first." >&2; exit 1; }
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

[[ -n "${CLOUDFLARE_TUNNEL_TOKEN:-}" ]] || { echo "Missing CLOUDFLARE_TUNNEL_TOKEN in $ENV_FILE" >&2; exit 1; }
[[ -x "$CF_BIN" ]] || { echo "cloudflared not found at $CF_BIN" >&2; exit 1; }

export TUNNEL_TOKEN="$CLOUDFLARE_TUNNEL_TOKEN"
unset CLOUDFLARE_TUNNEL_TOKEN
exec "$CF_BIN" tunnel --no-autoupdate run
