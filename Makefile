PYTHON ?= python3
VERSION ?= 3.0.3

.PHONY: check test compile doctor postgres-test release-check shell-check run worker scheduler lint-security docker-build

check: test doctor release-check shell-check lint-security

compile:
	$(PYTHON) -m compileall -q zworkforce tests scripts

test: compile
	PYTHONPATH=. $(PYTHON) -m unittest discover -s tests -v

doctor:
	PYTHONPATH=. $(PYTHON) -m zworkforce doctor

postgres-test:
	@test -n "$${ZWORKFORCE_TEST_POSTGRES_URL:-}" || (echo "set ZWORKFORCE_TEST_POSTGRES_URL to a real PostgreSQL service" >&2; exit 2)
	PYTHONPATH=. $(PYTHON) -m unittest tests.test_v3_postgres -v

release-check:
	$(PYTHON) scripts/verify_release.py --expected $(VERSION)

shell-check:
	bash -n scripts/*.sh
	node --check zworkforce/static/app.js

run:
	python -m zworkforce serve

worker:
	python -m zworkforce worker

scheduler:
	python -m zworkforce scheduler --once

lint-security:
	! grep -R --line-number --include="*.py" "shell=True" zworkforce
	! grep -R --line-number -E "API_KEY|provider_api_key|Authorization: Bearer" zworkforce/static

docker-build:
	docker build --build-arg VERSION=$(VERSION) -t zworkforce:$(VERSION) .
