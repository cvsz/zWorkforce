.PHONY: all setup install build test lint typecheck clean start stop restart update upgrade updgrade status logs k8s-validate k3s-validate cilium-preflight cilium-prepare cilium-install \
	phase6-start phase6-stop phase6-restart phase6-update token-verify token-rotate-dry token-rotate token-clean-dry token-clean token-bootstrap-roll token-legacy-scrub gpg-commit gpg-push gpg-pull gpg-finalize

STACK ?= compose.yml
COMPOSE = docker compose -f $(STACK)
TOKEN_ROTATE_TYPES ?= dns,zt,workers,pages,tunnel
TOKEN_ROTATE_OUT ?= .env.cloudflare

# Default to running the full validation pipeline
all: install lint typecheck build test

setup: install
	@echo "==> Validating compose configuration..."
	$(COMPOSE) config --quiet

# ==========================================
# Full-Stack Orchestration
# ==========================================

install:
	@echo "==> Installing Node dependencies (pnpm workspace)..."
	pnpm install --ignore-scripts
	@echo "==> Installing Go dependencies (zctl)..."
	cd tools/zctl && go mod download

build:
	@echo "==> Building Next.js, AI Gateway, and Workspace packages..."
	pnpm run build
	@echo "==> Building Go CLI (zctl)..."
	$(MAKE) -C tools/zctl build
	@echo "==> Building service images..."
	$(COMPOSE) build

test:
	@echo "==> Testing Workspace (Node)..."
	pnpm run test
	@echo "==> Testing Go CLI (zctl)..."
	$(MAKE) -C tools/zctl test

lint:
	@echo "==> Linting Workspace (Node)..."
	pnpm run lint
	@echo "==> Linting Go CLI (zctl)..."
	$(MAKE) -C tools/zctl lint

typecheck:
	@echo "==> Typechecking Workspace (Node)..."
	pnpm run typecheck
	@echo "==> Vetting Go CLI (zctl)..."
	$(MAKE) -C tools/zctl vet

clean:
	@echo "==> Cleaning Workspace..."
	rm -rf node_modules
	find . -name 'node_modules' -type d -prune -exec rm -rf '{}' +
	@echo "==> Cleaning Go CLI (zctl)..."
	$(MAKE) -C tools/zctl clean

start:
	@test -f .env || { echo "ERROR: .env is required; copy .env.example and fill secrets"; exit 1; }
	$(COMPOSE) up -d

stop:
	$(COMPOSE) stop

restart:
	$(COMPOSE) up -d --remove-orphans

update:
	@echo "==> Refreshing dependencies and rebuilding images..."
	pnpm install --frozen-lockfile
	cd tools/zctl && go mod download
	$(COMPOSE) build --pull

upgrade: update restart

# Backward-compatible spelling retained for existing operator runbooks.
updgrade: upgrade

k8s-validate:
	node scripts/validate-kubernetes-manifests.mjs

k3s-validate:
	bash scripts/validate-k3s-cilium.sh

cilium-preflight:
	bash scripts/cilium-migration-preflight.sh

cilium-prepare:
	bash scripts/prepare-k3s-cilium-migration.sh

cilium-install:
	bash scripts/install-cilium-k3s.sh

status:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f --tail=200

phase6-start:
	$(MAKE) start STACK=docker-compose.phase6.yml

phase6-stop:
	$(MAKE) stop STACK=docker-compose.phase6.yml

phase6-restart:
	$(MAKE) restart STACK=docker-compose.phase6.yml

phase6-update:
	$(MAKE) update STACK=docker-compose.phase6.yml

# ==========================================
# Cloudflare Scoped Token Lifecycle
# ==========================================

token-verify:
	bash scripts/cloudflare/verify-token-env.sh

token-rotate-dry:
	bash scripts/cloudflare/rotate-tokens-with-permission-preflight.sh \
		--regenerate --types "$(TOKEN_ROTATE_TYPES)" --write "$(TOKEN_ROTATE_OUT)" \
		--backup --dry-run

token-rotate:
	@test "$(TOKEN_ROTATE_CONFIRM)" = "YES" || { echo "ERROR: set TOKEN_ROTATE_CONFIRM=YES after reviewing token-rotate-dry"; exit 2; }
	bash scripts/cloudflare/rotate-tokens-with-permission-preflight.sh \
		--regenerate --types "$(TOKEN_ROTATE_TYPES)" --write "$(TOKEN_ROTATE_OUT)" \
		--backup --yes

token-clean-dry:
	bash scripts/cloudflare/run-token-rotation.sh --keep-most 1 --unused-days 30 --backup --dry-run

token-clean:
	@test "$(TOKEN_CLEAN_CONFIRM)" = "YES" || { echo "ERROR: set TOKEN_CLEAN_CONFIRM=YES after reviewing token-clean-dry"; exit 2; }
	bash scripts/cloudflare/run-token-rotation.sh --keep-most 1 --unused-days 30 --backup --yes

token-bootstrap-roll:
	@test "$(TOKEN_BOOTSTRAP_ROLL_CONFIRM)" = "YES" || { echo "ERROR: set TOKEN_BOOTSTRAP_ROLL_CONFIRM=YES to roll the active bootstrap token"; exit 2; }
	CONFIRM_BOOTSTRAP_ROLL=YES bash scripts/cloudflare/roll-bootstrap-token.sh

token-legacy-scrub:
	@test "$(TOKEN_LEGACY_SCRUB_CONFIRM)" = "YES" || { echo "ERROR: set TOKEN_LEGACY_SCRUB_CONFIRM=YES to remove deprecated local credentials"; exit 2; }
	CONFIRM_LEGACY_SCRUB=YES bash scripts/cloudflare/scrub-legacy-credentials.sh

# ==========================================
# Git GPG Workflows
# ==========================================

gpg-commit:
	@test -n "$(COMMIT_MSG)" || (echo "ERROR: COMMIT_MSG is required. Usage: make gpg-commit COMMIT_MSG='your message'" && exit 1)
	git commit -S -m "$(COMMIT_MSG)"

gpg-push:
	git push

gpg-pull:
	git pull

gpg-finalize:
	@test -n "$(COMMIT_MSG)" || (echo "ERROR: COMMIT_MSG is required. Usage: make gpg-finalize COMMIT_MSG='your message'" && exit 1)
	git add .
	$(MAKE) gpg-commit COMMIT_MSG="$(COMMIT_MSG)"
	$(MAKE) gpg-push
