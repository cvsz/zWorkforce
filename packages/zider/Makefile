.PHONY: install dev run test lint clean docker-build docker-up

VENV ?= .venv
PYTHON ?= python3

install:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install -U pip setuptools wheel
	$(VENV)/bin/pip install -r server/requirements.txt

dev:
	$(VENV)/bin/uvicorn server.app.main:app --host 0.0.0.0 --port 8085 --reload

run:
	$(VENV)/bin/uvicorn server.app.main:app --host 0.0.0.0 --port 8085

test:
	PYTHONPATH=. $(VENV)/bin/python -m unittest discover -s server/tests -v

docker-build:
	docker compose build

docker-up:
	docker compose up -d

clean:
	rm -rf __pycache__ .pytest_cache $(VENV)
