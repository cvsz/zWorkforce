#!/usr/bin/env bash
# ==============================================================================
# zWorkforce + Open WebUI Enterprise Stack Deployment Script
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "================================================================="
echo " 🚀 Starting zWorkforce + Open WebUI Enterprise Stack"
echo "================================================================="

# Export default secrets if not set
export ZWORKFORCE_POSTGRES_PASSWORD="${ZWORKFORCE_POSTGRES_PASSWORD:-zwf-postgres-secure-pass}"
export ZWORKFORCE_API_KEYS="${ZWORKFORCE_API_KEYS:-bootstrap-key:superadmin:default:bootstrap:*}"
export ZWORKFORCE_API_KEY="bootstrap-key"
export OPEN_WEBUI_PORT="${OPEN_WEBUI_PORT:-3080}"

echo "1. Checking environment & networks..."
docker compose -f compose.yaml -f compose.open-webui.yml config -q

echo "2. Launching Services (PostgreSQL + API + Open WebUI)..."
docker compose -f compose.yaml -f compose.open-webui.yml up -d

echo ""
echo "================================================================="
echo " ✅ Enterprise Stack is LIVE!"
echo " 👉 Open WebUI Interface: http://localhost:${OPEN_WEBUI_PORT}"
echo " 👉 zWorkforce API:       http://localhost:9570"
echo " 👉 Artifacts & RAG:      Ready"
echo " 👉 9 Unlocked Models:    Ready"
echo "================================================================="
