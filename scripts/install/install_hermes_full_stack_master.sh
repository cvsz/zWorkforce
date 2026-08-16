#!/usr/bin/env bash
# ==============================================================================
# 🚀 ULTRA ALL-IN-ONE AUTOMATED INSTALLER & SKILLS LINKER
# - Installs Bun runtime & OpenRouter Spawn CLI
# - Installs Hermes Agent (NousResearch) & links ~/.hermes/bin into PATH
# - Fetches & sets up Community Hermes Skills (awesome-hermes-skills)
# - Symlinks all local project skills (zWorkforce) + global skills into Hermes
# - Auto-queries OpenRouter API for 100% FREE latest models
# - Zero-touch launch of Hermes Local
# ==============================================================================
set -euo pipefail

# ANSI Palette
C_CYAN="\033[1;36m"
C_GREEN="\033[1;32m"
C_YELLOW="\033[1;33m"
C_MAGENTA="\033[1;35m"
C_BLUE="\033[1;34m"
C_RED="\033[1;31m"
C_RESET="\033[0m"

log()   { echo -e "${C_GREEN}[+]${C_RESET} $1"; }
info()  { echo -e "${C_CYAN}[*]${C_RESET} $1"; }
warn()  { echo -e "${C_YELLOW}[!]${C_RESET} $1"; }
err()   { echo -e "${C_RED}[ERROR]${C_RESET} $1" >&2; exit 1; }

echo -e "${C_MAGENTA}"
echo "===================================================================="
echo "    🚀 FULL STACK AUTOMATED SPAWN + HERMES + SKILLS SUITE          "
echo "        (zWorkforce + Community Skills + Latest Free Models)        "
echo "===================================================================="
echo -e "${C_RESET}"

PROJECT_DIR="/home/cvsz/zworkforce"
HERMES_DIR="$HOME/.hermes"
HERMES_SKILLS_DIR="$HERMES_DIR/skills"
GLOBAL_SKILLS_DIR="$HOME/.agents/skills"
COMMUNITY_SKILLS_DIR="$HERMES_DIR/community-skills"

mkdir -p "$HERMES_SKILLS_DIR" "$HOME/.local/bin"

# ------------------------------------------------------------------------------
# 1. Environment & PATH configuration
# ------------------------------------------------------------------------------
log "Step 1/6: Configuring PATH and environment in ~/.bashrc..."
export BUN_INSTALL="${BUN_INSTALL:-$HOME/.bun}"
export PATH="$HOME/.local/bin:$BUN_INSTALL/bin:$HERMES_DIR/bin:$PATH"

if ! grep -qs 'export BUN_INSTALL=' "$HOME/.bashrc" 2>/dev/null; then
  cat << 'EOF' >> "$HOME/.bashrc"
# Bun, Spawn CLI, and Hermes Agent paths
export BUN_INSTALL="$HOME/.bun"
export PATH="$HOME/.local/bin:$BUN_INSTALL/bin:$HOME/.hermes/bin:$PATH"
EOF
  info "Added Bun and Hermes paths to ~/.bashrc"
fi

# ------------------------------------------------------------------------------
# 2. Install Bun Runtime & Spawn CLI
# ------------------------------------------------------------------------------
log "Step 2/6: Verifying / Installing Bun runtime and Spawn CLI..."

if ! command -v bun &>/dev/null; then
  info "Installing Bun runtime..."
  curl -fsSL https://bun.sh/install | bash
  export PATH="$BUN_INSTALL/bin:$PATH"
fi
info "Bun Runtime: $(bun --version) at $(command -v bun)"

if ! command -v spawn &>/dev/null; then
  info "Installing OpenRouter Spawn CLI..."
  curl -fsSL https://openrouter.ai/labs/spawn/cli/install.sh | bash
fi
info "Spawn CLI: $(spawn --version | head -n 1) at $(command -v spawn)"

# ------------------------------------------------------------------------------
# 3. Hermes Agent Core & uv Runtime Setup
# ------------------------------------------------------------------------------
log "Step 3/6: Setting up Hermes Agent core..."

# Download standalone uv/uvx if missing in ~/.hermes/bin
if [ ! -f "$HERMES_DIR/bin/uv" ]; then
  info "Installing fast uv package manager to $HERMES_DIR/bin..."
  curl -LsSf https://astral.sh/uv/install.sh | env CARGO_HOME="$HERMES_DIR" UV_INSTALL_DIR="$HERMES_DIR/bin" sh || true
fi

# Clone Hermes repo if missing
if [ ! -d "$HERMES_DIR/hermes-agent/.git" ]; then
  info "Cloning official NousResearch hermes-agent..."
  git clone --depth 1 https://github.com/NousResearch/hermes-agent.git "$HERMES_DIR/hermes-agent" 2>/dev/null || true
fi

# ------------------------------------------------------------------------------
# 4. Integrate & Symlink All Skills (Project + Community + Global)
# ------------------------------------------------------------------------------
log "Step 4/6: Integrating and Linking All Agent Skills..."

# A. Clone/Update Awesome Hermes Skills community repo
if [ ! -d "$COMMUNITY_SKILLS_DIR" ]; then
  info "Fetching community skills from ZeroPointRepo/awesome-hermes-skills..."
  git clone --depth 1 https://github.com/ZeroPointRepo/awesome-hermes-skills.git "$COMMUNITY_SKILLS_DIR" 2>/dev/null || true
fi

# B. Link zWorkforce project skills
if [ -d "$PROJECT_DIR/.agents/skills" ]; then
  info "Linking zWorkforce production skills into Hermes..."
  for skill_path in "$PROJECT_DIR/.agents/skills"/*; do
    if [ -d "$skill_path" ]; then
      skill_name=$(basename "$skill_path")
      ln -sfn "$skill_path" "$HERMES_SKILLS_DIR/$skill_name"
    fi
  done
fi

# C. Link Global Skills
if [ -d "$GLOBAL_SKILLS_DIR" ]; then
  info "Linking global developer skills into Hermes..."
  for skill_path in "$GLOBAL_SKILLS_DIR"/*; do
    if [ -d "$skill_path" ]; then
      skill_name=$(basename "$skill_path")
      ln -sfn "$skill_path" "$HERMES_SKILLS_DIR/$skill_name"
    fi
  done
fi

# Count linked skills
TOTAL_SKILLS=$(find -L "$HERMES_SKILLS_DIR" -mindepth 1 -maxdepth 1 \( -type d -o -type l \) | wc -l)
info "Total active skills integrated in Hermes: ${TOTAL_SKILLS}"

# ------------------------------------------------------------------------------
# 5. Fetch Live Free Models from OpenRouter API
# ------------------------------------------------------------------------------
log "Step 5/6: Querying OpenRouter for latest live active FREE models..."

FREE_MODELS=()
RAW_MODELS=$(curl -s --connect-timeout 8 "https://openrouter.ai/api/v1/models" 2>/dev/null || true)

if [ -n "$RAW_MODELS" ] && command -v jq &>/dev/null; then
  while IFS= read -r model_name; do
    if [ -n "$model_name" ] && [ "$model_name" != "null" ]; then
      FREE_MODELS+=("$model_name")
    fi
  done < <(echo "$RAW_MODELS" | jq -r '.data[] | select(.id | endswith(":free")) | .id' 2>/dev/null || true)
fi

# Fallback verified models
if [ ${#FREE_MODELS[@]} -eq 0 ]; then
  FREE_MODELS=(
    "meta-llama/llama-3.3-70b-instruct:free"
    "deepseek/deepseek-r1:free"
    "qwen/qwen-2.5-coder-32b-instruct:free"
    "google/gemini-2.0-flash-exp:free"
    "google/gemma-4-31b-it:free"
    "nvidia/nemotron-3-nano-30b-a3b:free"
  )
fi

SELECTED_MODEL=""
if [ -n "${FREE_MODEL:-}" ]; then
  SELECTED_MODEL="$FREE_MODEL"
  info "Using overridden model: ${SELECTED_MODEL}"
else
  SELECTED_MODEL="${FREE_MODELS[0]}"
  info "Default latest active free model: ${SELECTED_MODEL}"
fi

# ------------------------------------------------------------------------------
# 6. Check Authentication & Execute
# ------------------------------------------------------------------------------
log "Step 6/6: Preparing launch environment..."

export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"

echo -e "\n${C_CYAN}--- Active Linked Skills in Hermes (${TOTAL_SKILLS}) ---${C_RESET}"
for skill in "$HERMES_SKILLS_DIR"/*; do
  [ -e "$skill" ] && echo "  ✔ $(basename "$skill")"
done
echo "--------------------------------------------------------"

echo -e "\n${C_GREEN}>>> Launching: spawn hermes local --model ${SELECTED_MODEL} $*${C_RESET}\n"
exec spawn hermes local --model "${SELECTED_MODEL}" "$@"
