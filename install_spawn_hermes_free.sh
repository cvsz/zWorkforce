#!/usr/bin/env bash
# ==============================================================================
# Full Stack Automated Installer for Spawn Hermes Local (100% Free Model Ready)
# ==============================================================================
set -euo pipefail

# Default free OpenRouter model (change via FREE_MODEL or --model flag if desired)
# Examples:
#   - meta-llama/llama-3.3-70b-instruct:free
#   - deepseek/deepseek-r1:free
#   - qwen/qwen-2.5-coder-32b-instruct:free
#   - google/gemini-2.0-flash-exp:free
DEFAULT_FREE_MODEL="${FREE_MODEL:-meta-llama/llama-3.3-70b-instruct:free}"

log() {
  echo -e "\033[1;32m[+] $1\033[0m"
}

warn() {
  echo -e "\033[1;33m[!] $1\033[0m"
}

info() {
  echo -e "\033[1;34m[*] $1\033[0m"
}

# 1. System packages & dependencies
log "Step 1/5: Checking system dependencies..."
for cmd in curl bash git jq; do
  if ! command -v "$cmd" &>/dev/null; then
    warn "Dependency '$cmd' not found. If needed, install via: sudo apt-get install -y $cmd"
  fi
done

# 2. Setup PATH & environment
log "Step 2/5: Setting up PATH and shell environment..."
export BUN_INSTALL="${BUN_INSTALL:-$HOME/.bun}"
export PATH="$HOME/.local/bin:$BUN_INSTALL/bin:$PATH"

if ! grep -qs 'export BUN_INSTALL=' "$HOME/.bashrc"; then
  cat << 'EOF' >> "$HOME/.bashrc"
# Bun & Spawn environment
export BUN_INSTALL="$HOME/.bun"
export PATH="$HOME/.local/bin:$BUN_INSTALL/bin:$PATH"
EOF
fi

# 3. Install Bun
log "Step 3/5: Verifying / Installing Bun runtime..."
if ! command -v bun &>/dev/null; then
  log "Installing Bun..."
  curl -fsSL https://bun.sh/install | bash
  export PATH="$BUN_INSTALL/bin:$PATH"
else
  info "Bun detected: $(bun --version)"
fi

# 4. Install Spawn CLI
log "Step 4/5: Verifying / Installing Spawn CLI..."
if ! command -v spawn &>/dev/null; then
  log "Installing Spawn..."
  curl -fsSL https://openrouter.ai/labs/spawn/cli/install.sh | bash
else
  info "Spawn detected: $(spawn --version | head -n 1)"
fi

# 5. OpenRouter Configuration
log "Step 5/5: Configuring OpenRouter & Free Model..."
info "Configured Free Model: ${DEFAULT_FREE_MODEL}"

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  warn "OPENROUTER_API_KEY environment variable is not set."
  echo "OpenRouter allows free model usage with a valid free API key."
  echo "Get yours at: https://openrouter.ai/settings/keys"
  if [ -t 0 ]; then
    read -rp "Enter OpenRouter API Key (or press enter to skip if already saved): " input_key
    if [ -n "$input_key" ]; then
      export OPENROUTER_API_KEY="$input_key"
    fi
  fi
fi

# 6. Execute Spawn Hermes Local with Free Model
log "Launching Hermes Local with model: ${DEFAULT_FREE_MODEL}..."
exec spawn hermes local --model "${DEFAULT_FREE_MODEL}" "$@"
