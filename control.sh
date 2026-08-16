#!/usr/bin/env bash
# ==============================================================================
# zWorkforce Unified Control Panel & Master Orchestrator (control.sh)
# ==============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

cmd_status() {
    echo -e "\n${CYAN}=== zWorkforce System Status ===${NC}"
    
    # 1. zWorkforce Core API
    echo -n "zWorkforce Control Plane (Port 9569 / 9570): "
    if curl -s --connect-timeout 2 http://127.0.0.1:9569/health >/dev/null 2>&1; then
        echo -e "${GREEN}ONLINE${NC}"
    elif curl -s --connect-timeout 2 http://127.0.0.1:9570/health >/dev/null 2>&1; then
        echo -e "${GREEN}ONLINE (:9570)${NC}"
    else
        echo -e "${RED}OFFLINE${NC}"
    fi

    # 2. OpenWebUI Gateway
    echo -n "OpenWebUI Gateway (Port 3080 / chat.zeaz.dev): "
    if curl -s --connect-timeout 2 http://127.0.0.1:3080 >/dev/null 2>&1; then
        echo -e "${GREEN}ONLINE${NC}"
    else
        echo -e "${YELLOW}STANDBY${NC}"
    fi

    # 3. ZSP-AITool Studio
    echo -n "ZSP Studio & HyperFrames (Port 3005 / studio.zeaz.dev): "
    if curl -s --connect-timeout 2 http://127.0.0.1:3005 >/dev/null 2>&1; then
        echo -e "${GREEN}ONLINE${NC}"
    else
        echo -e "${YELLOW}STANDBY${NC}"
    fi

    # 4. Hermes Agent Engine
    echo -n "Hermes Agent CLI: "
    if command -v ~/.hermes/bin/hermes >/dev/null 2>&1 || command -v hermes >/dev/null 2>&1; then
        echo -e "${GREEN}INSTALLED${NC}"
    else
        echo -e "${RED}MISSING${NC}"
    fi

    # 5. Spawn CLI
    echo -n "OpenRouter Spawn CLI: "
    if command -v ~/.local/bin/spawn >/dev/null 2>&1 || command -v spawn >/dev/null 2>&1; then
        echo -e "${GREEN}INSTALLED${NC}"
    else
        echo -e "${RED}MISSING${NC}"
    fi

    echo ""
    zworkforce doctor || true
}

cmd_verify() {
    log_info "Executing Full Repository Verification Protocol..."
    python3 -m compileall -q zworkforce tests
    PYTHONPATH=. python3 -m unittest discover -s tests -v
    zworkforce doctor
    log_success "All unit tests and doctor checks PASSED!"
}

cmd_install() {
    log_info "Installing dependencies across full monorepo..."
    
    # 1. Root python & setup
    ./setup.sh
    
    # 2. Zarvis packages
    if [ -d "packages/zarvis" ]; then
        log_info "Setting up packages/zarvis..."
        (cd packages/zarvis && pnpm install --frozen-lockfile || npm install)
    fi

    # 3. ZSP-AITool studio
    if [ -d "packages/zsp-aitool" ]; then
        log_info "Setting up packages/zsp-aitool..."
        (cd packages/zsp-aitool && npm run prisma:generate && npm run build)
    fi

    # 4. Zider companion
    if [ -d "packages/zider" ]; then
        log_info "Setting up packages/zider..."
        (cd packages/zider && npm install && npm run build || true)
    fi

    log_success "Monorepo installation complete!"
}

cmd_start() {
    log_info "Starting zWorkforce Services..."
    docker compose up -d
    if [ -f "compose.open-webui.yml" ]; then
        docker compose -f compose.open-webui.yml up -d
    fi
    log_success "Services started!"
}

cmd_stop() {
    log_info "Stopping zWorkforce Services..."
    docker compose down || true
    if [ -f "compose.open-webui.yml" ]; then
        docker compose -f compose.open-webui.yml down || true
    fi
    log_success "Services stopped!"
}

cmd_restart() {
    cmd_stop
    sleep 2
    cmd_start
}

case "${1:-status}" in
    status)
        cmd_status
        ;;
    verify|test)
        cmd_verify
        ;;
    install)
        cmd_install
        ;;
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    help|--help|-h)
        echo "Usage: ./control.sh [status|verify|install|start|stop|restart]"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Usage: ./control.sh [status|verify|install|start|stop|restart]"
        exit 1
        ;;
esac
