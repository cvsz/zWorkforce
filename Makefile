.PHONY: test compile doctor run worker scheduler lint-security docker-build

compile:
	python -m compileall -q zworkforce tests

test: compile
	PYTHONPATH=. python -m unittest discover -s tests -v

doctor:
	python -m zworkforce doctor

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
	docker build -t zworkforce:3.0.0 .
