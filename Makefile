.PHONY: run test check doctor docker-build
run:
	python -m zworkforce serve
test:
	python -m unittest discover -s tests -v
check:
	python -m compileall -q zworkforce tests
	python -m unittest discover -s tests -v
doctor:
	python -m zworkforce doctor
docker-build:
	docker build -t zworkforce:local .
