#!/usr/bin/env bash
# ==============================================================================
# Full-Stack Automated Installer & Launcher for Spawn Hermes Local
# Automatically fetches and uses the LATEST available FREE models from OpenRouter
# ==============================================================================
set -euo pipefail

# ANSI Colors
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
CYAN="\033[1;36m"
RED="\033[1;31m"
RESET="\033[0m"

log()   { echo -e "${GREEN}[+] $1${RESET}"; }
warn()  { echo -e "${YELLOW}[!] $1${RESET}"; }
info()  { echo -e "${CYAN}[*] $1${RESET}"; }
error() { echo -e "${RED}[ERROR] $1${RESET}" >&2; exit 1; }

echo -e "${CYAN}"
echo "================================================================"
echo "    Spawn Hermes Local - Automated Full Stack Installer         "
echo "            (Dynamic Latest Free Models Edition)                "
echo "================================================================"
echo -e "${RESET}"

# 1. System prerequisites check
log "1/6. Verifying system dependencies..."
for pkg in curl jq bash git; do
  if ! command -v "$pkg" &>/dev/null; then
    warn "'$pkg' is missing. Attempting best-effort setup or please run: sudo apt-get install -y $pkg"
  fi
done

# 2. Environment & PATH setup
log "2/6. Setting up environment variables and persistent PATH..."
export BUN_INSTALL="${BUN_INSTALL:-$HOME/.bun}"
export PATH="$HOME/.local/bin:$BUN_INSTALL/bin:$PATH"

if ! grep -qs 'export BUN_INSTALL=' "$HOME/.bashrc"; then
  cat << 'EOF' >> "$HOME/.bashrc"
# Bun & Spawn CLI paths
export BUN_INSTALL="$HOME/.bun"
export PATH="$HOME/.local/bin:$BUN_INSTALL/bin:$PATH"
EOF
fi

# 3. Install/Update Bun Runtime
log "3/6. Checking Bun JavaScript/TypeScript runtime..."
if ! command -v bun &>/dev/null; then
  log "Installing Bun..."
  curl -fsSL https://bun.sh/install | bash
  export PATH="$BUN_INSTALL/bin:$PATH"
else
  info "Bun installed: $(bun --version)"
fi

# 4. Install/Update OpenRouter Spawn CLI
log "4/6. Checking Spawn CLI..."
if ! command -v spawn &>/dev/null; then
  log "Installing Spawn CLI..."
  curl -fsSL https://openrouter.ai/labs/spawn/cli/install.sh | bash
else
  info "Spawn CLI installed: $(spawn --version | head -n 1)"
fi

# 5. Dynamic Free Model Resolution
log "5/6. Resolving the latest available free model from OpenRouter..."

SELECTED_MODEL=""

if [ -n "${FREE_MODEL:-}" ]; then
  SELECTED_MODEL="$FREE_MODEL"
  info "Using user-specified model override: $SELECTED_MODEL"
else
  # Query OpenRouter models API for live active free models
  AVAILABLE_FREE_MODELS=()
  if command -v jq &>/dev/null && command -v curl &>/dev/null; then
    info "Fetching live free models list from OpenRouter API..."
    LIVE_MODELS=$(curl -s "https://openrouter.ai/api/v1/models" 2>/dev/null | jq -r '.data[] | select(.id | endswith(":free")) | .id' 2>/dev/null || true)
    if [ -n "$LIVE_MODELS" ]; then
      while IFS= read -r m; do
        [ -n "$m" ] && AVAILABLE_FREE_MODELS+=("$m")
      done <<< "$LIVE_MODELS"
    fi
  fi

  # Fallback priority list if API query fails or is empty
  FALLBACK_FREE_MODELS=(
    "meta-llama/llama-3.3-70b-instruct:free"
    "deepseek/deepseek-r1:free"
    "qwen/qwen-2.5-coder-32b-instruct:free"
    "google/gemini-2.0-flash-exp:free"
    "google/gemini-2.0-flash-thinking-exp:free"
    "meta-llama/llama-3.2-3b-instruct:free"
    "mistralai/mistral-7b-instruct:free"
  )

  if [ ${#AVAILABLE_FREE_MODELS[@]} -gt 0 ]; then
    info "Found ${#AVAILABLE_FREE_MODELS[@]} live active free models on OpenRouter."
    SELECTED_MODEL="${AVAILABLE_FREE_MODELS[0]}"
  else
    warn "Could not fetch live list directly. Defaulting to top verified free model."
    SELECTED_MODEL="${FALLBACK_FREE_MODELS[0]}"
  fi
fi

info "Selected Target Model: ${SELECTED_MODEL}"

# 6. API Key Check
log "6/6. Checking OpenRouter authentication..."
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  warn "OPENROUTER_API_KEY environment variable is empty."
  echo "OpenRouter free models only require a free API key (zero credit cost)."
  echo "Get yours at: https://openrouter.ai/settings/keys"
  if [ -t 0 ]; then
    read -rp "Enter OpenRouter API Key (press Enter if already cached): " entered_key
    if [ -n "$entered_key" ]; then
      export OPENROUTER_API_KEY="$entered_key"
    fi
  fi
fi

# 7. Launch Spawn Hermes Local
echo ""
log "Launching Hermes Local with Model: [${SELECTED_MODEL}]"
echo "----------------------------------------------------------------"
exec spawn hermes local --model "${SELECTED_MODEL}" "$@"
