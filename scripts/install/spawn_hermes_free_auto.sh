#!/usr/bin/env bash
# ==============================================================================
# 100% Zero-Touch Automated Full-Stack Installer & Runner for Spawn Hermes Local
# - Automatically installs Bun runtime & OpenRouter Spawn CLI
# - Automatically discovers all latest FREE models from OpenRouter API
# - Offers auto-selection or interactive picker of latest active free models
# - Runs non-interactively or with custom prompt/headless flags
# ==============================================================================
set -euo pipefail

# UI Styling
C_CYAN="\033[1;36m"
C_GREEN="\033[1;32m"
C_YELLOW="\033[1;33m"
C_MAGENTA="\033[1;35m"
C_RED="\033[1;31m"
C_RESET="\033[0m"

log()   { echo -e "${C_GREEN}[+]${C_RESET} $1"; }
info()  { echo -e "${C_CYAN}[*]${C_RESET} $1"; }
warn()  { echo -e "${C_YELLOW}[!]${C_RESET} $1"; }
err()   { echo -e "${C_RED}[ERROR]${C_RESET} $1" >&2; exit 1; }

echo -e "${C_MAGENTA}"
echo "===================================================================="
echo "    🚀 SPAWN HERMES LOCAL — ALL-IN-ONE AUTOMATED INSTALLER          "
echo "           (Auto-Fetch Latest 100% Free AI Models)                 "
echo "===================================================================="
echo -e "${C_RESET}"

# ------------------------------------------------------------------------------
# 1. System dependencies check (curl, jq, git)
# ------------------------------------------------------------------------------
log "Step 1/5: Checking system packages..."
for tool in curl jq git bash; do
  if ! command -v "$tool" &>/dev/null; then
    warn "Missing '$tool'. Installing dependencies if sudo is available..."
    if command -v apt-get &>/dev/null && [ "$EUID" -eq 0 ]; then
      apt-get update -qq && apt-get install -y -qq "$tool" || true
    elif command -v sudo &>/dev/null; then
      sudo apt-get update -qq && sudo apt-get install -y -qq "$tool" || true
    fi
  fi
done

# ------------------------------------------------------------------------------
# 2. Environment & PATH setup
# ------------------------------------------------------------------------------
log "Step 2/5: Configuring environment paths..."
export BUN_INSTALL="${BUN_INSTALL:-$HOME/.bun}"
export PATH="$HOME/.local/bin:$BUN_INSTALL/bin:$PATH"

if ! grep -qs 'export BUN_INSTALL=' "$HOME/.bashrc" 2>/dev/null; then
  cat << 'EOF' >> "$HOME/.bashrc"
# Bun & Spawn Paths
export BUN_INSTALL="$HOME/.bun"
export PATH="$HOME/.local/bin:$BUN_INSTALL/bin:$PATH"
EOF
fi

# ------------------------------------------------------------------------------
# 3. Bun Runtime & Spawn CLI installation
# ------------------------------------------------------------------------------
log "Step 3/5: Installing / Verifying Bun runtime & Spawn CLI..."

if ! command -v bun &>/dev/null; then
  info "Downloading and installing Bun..."
  curl -fsSL https://bun.sh/install | bash
  export PATH="$BUN_INSTALL/bin:$PATH"
fi
info "Bun Runtime: $(bun --version) at $(command -v bun)"

if ! command -v spawn &>/dev/null; then
  info "Downloading and installing OpenRouter Spawn CLI..."
  curl -fsSL https://openrouter.ai/labs/spawn/cli/install.sh | bash
fi
info "Spawn CLI: $(spawn --version | head -n 1) at $(command -v spawn)"

# ------------------------------------------------------------------------------
# 4. Fetch All Latest Free Models from OpenRouter
# ------------------------------------------------------------------------------
log "Step 4/5: Fetching latest active FREE models from OpenRouter API..."

FREE_MODELS=()

# Fetch latest models dynamically
RAW_MODELS=$(curl -s --connect-timeout 8 "https://openrouter.ai/api/v1/models" 2>/dev/null || true)

if [ -n "$RAW_MODELS" ] && command -v jq &>/dev/null; then
  while IFS= read -r model_name; do
    if [ -n "$model_name" ] && [ "$model_name" != "null" ]; then
      FREE_MODELS+=("$model_name")
    fi
  done < <(echo "$RAW_MODELS" | jq -r '.data[] | select(.id | endswith(":free")) | .id' 2>/dev/null || true)
fi

# Fallback verified free models list if API is unreachable
if [ ${#FREE_MODELS[@]} -eq 0 ]; then
  warn "Unable to query live API. Using top latest verified free models list."
  FREE_MODELS=(
    "meta-llama/llama-3.3-70b-instruct:free"
    "deepseek/deepseek-r1:free"
    "qwen/qwen-2.5-coder-32b-instruct:free"
    "google/gemini-2.0-flash-exp:free"
    "google/gemini-2.0-flash-thinking-exp:free"
    "meta-llama/llama-3.2-3b-instruct:free"
    "mistralai/mistral-7b-instruct:free"
  )
fi

echo -e "\n${C_CYAN}--- Available Latest Free Models (${#FREE_MODELS[@]} found) ---${C_RESET}"
for i in "${!FREE_MODELS[@]}"; do
  printf " [%2d] %s\n" "$((i + 1))" "${FREE_MODELS[$i]}"
done
echo "----------------------------------------------------"

# Selection logic
SELECTED_MODEL=""
if [ -n "${FREE_MODEL:-}" ]; then
  SELECTED_MODEL="$FREE_MODEL"
  info "Using user-specified model from environment: ${SELECTED_MODEL}"
elif [ -n "${MODEL_INDEX:-}" ] && [ "$MODEL_INDEX" -ge 1 ] && [ "$MODEL_INDEX" -le "${#FREE_MODELS[@]}" ]; then
  SELECTED_MODEL="${FREE_MODELS[$((MODEL_INDEX - 1))]}"
  info "Selected model by index [${MODEL_INDEX}]: ${SELECTED_MODEL}"
elif [ "${AUTO_SELECT_FIRST:-1}" = "1" ] || [ ! -t 0 ]; then
  SELECTED_MODEL="${FREE_MODELS[0]}"
  info "Auto-selected highest ranked latest free model: ${SELECTED_MODEL}"
else
  read -rp "Select model number [1-${#FREE_MODELS[@]}] (Default 1): " choice
  choice="${choice:-1}"
  if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le "${#FREE_MODELS[@]}" ]; then
    SELECTED_MODEL="${FREE_MODELS[$((choice - 1))]}"
  else
    SELECTED_MODEL="${FREE_MODELS[0]}"
  fi
fi

# ------------------------------------------------------------------------------
# 5. OpenRouter Key & Execution
# ------------------------------------------------------------------------------
log "Step 5/5: Launching Hermes Local with Free Model [${SELECTED_MODEL}]..."

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  warn "OPENROUTER_API_KEY is not set."
  echo "You can generate a free API key at: https://openrouter.ai/settings/keys"
  if [ -t 0 ]; then
    read -rp "Enter OpenRouter API Key (leave blank to skip if previously configured): " user_key
    if [ -n "$user_key" ]; then
      export OPENROUTER_API_KEY="$user_key"
    fi
  fi
fi

echo -e "\n${C_GREEN}>>> Running: spawn hermes local --model ${SELECTED_MODEL} $*${C_RESET}\n"
exec spawn hermes local --model "${SELECTED_MODEL}" "$@"
