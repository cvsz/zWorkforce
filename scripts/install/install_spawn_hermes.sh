#!/usr/bin/env bash
# ==============================================================================
# Full Stack Automated Installer & Launcher for Spawn Hermes (Local)
# ==============================================================================
set -euo pipefail

log() {
  echo -e "\033[1;32m[+] $1\033[0m"
}

warn() {
  echo -e "\033[1;33m[!] $1\033[0m"
}

# 1. Check prerequisites
log "Checking base dependencies..."
for cmd in curl bash git; do
  if ! command -v "$cmd" &>/dev/null; then
    warn "Missing '$cmd'. Please install it using your system package manager (e.g. sudo apt-get install -y $cmd)."
  fi
done

# 2. Setup Environment Paths
export BUN_INSTALL="${BUN_INSTALL:-$HOME/.bun}"
export PATH="$HOME/.local/bin:$BUN_INSTALL/bin:$PATH"

# Persist PATH in ~/.bashrc if not already present
if ! grep -qs 'export BUN_INSTALL=' "$HOME/.bashrc"; then
  log "Configuring Bun environment in ~/.bashrc..."
  cat << 'EOF' >> "$HOME/.bashrc"
# Bun & Local bin
export BUN_INSTALL="$HOME/.bun"
export PATH="$HOME/.local/bin:$BUN_INSTALL/bin:$PATH"
EOF
fi

# 3. Install Bun if missing
if ! command -v bun &>/dev/null; then
  log "Installing Bun..."
  curl -fsSL https://bun.sh/install | bash
  export PATH="$BUN_INSTALL/bin:$PATH"
else
  log "Bun is already installed: $(bun --version)"
fi

# 4. Install Spawn CLI if missing
if ! command -v spawn &>/dev/null; then
  log "Installing Spawn CLI..."
  curl -fsSL https://openrouter.ai/labs/spawn/cli/install.sh | bash
else
  log "Spawn CLI is already installed: $(spawn --version | head -n 1)"
fi

# 5. OpenRouter API Key check (for headless / non-interactive automation)
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  warn "OPENROUTER_API_KEY is not set."
  echo "You can get an API key at: https://openrouter.ai/settings/keys"
  if [ -t 0 ]; then
    read -rp "Enter your OpenRouter API Key (or press Enter to skip if already set): " user_key
    if [ -n "$user_key" ]; then
      export OPENROUTER_API_KEY="$user_key"
    fi
  fi
fi

# 6. Execute Spawn Hermes Local
log "Starting Hermes Local via Spawn..."
exec spawn hermes local "$@"
