.PHONY: all setup install build test lint typecheck clean start stop restart update upgrade status logs gpg-commit gpg-push gpg-pull gpg-finalize

STACK ?= compose.zarvis-local.yml
COMPOSE = docker compose -f $(STACK)

all: install lint typecheck build test

setup: install
	@echo "==> Validating Z.A.R.V.I.S. compose configuration..."
	$(COMPOSE) config --quiet

install:
	@echo "==> Installing Node dependencies..."
	pnpm install --ignore-scripts
	@echo "==> Installing Go dependencies (zctl)..."
	cd tools/zctl && go mod download

build:
	@echo "==> Building Z.A.R.V.I.S. workspace packages..."
	pnpm run build
	@echo "==> Building Go CLI (zctl)..."
	$(MAKE) -C tools/zctl build
	@echo "==> Building local service images..."
	$(COMPOSE) build

test:
	@echo "==> Testing Z.A.R.V.I.S. workspace..."
	pnpm run test
	@echo "==> Testing Go CLI (zctl)..."
	$(MAKE) -C tools/zctl test

lint:
	@echo "==> Linting Z.A.R.V.I.S. workspace..."
	pnpm run lint
	@echo "==> Linting Go CLI (zctl)..."
	$(MAKE) -C tools/zctl lint

typecheck:
	@echo "==> Typechecking Z.A.R.V.I.S. workspace..."
	pnpm run typecheck
	@echo "==> Vetting Go CLI (zctl)..."
	$(MAKE) -C tools/zctl vet

clean:
	@echo "==> Cleaning Z.A.R.V.I.S. workspace..."
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
	@echo "==> Refreshing dependencies and rebuilding Z.A.R.V.I.S. images..."
	pnpm install --frozen-lockfile
	cd tools/zctl && go mod download
	$(COMPOSE) build --pull

upgrade: update restart

status:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f --tail=200

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
