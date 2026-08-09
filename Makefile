.PHONY: test check doctor serve worker docker-build

test:
	PYTHONPATH=. python -m unittest discover -s tests -v

check:
	python -m compileall -q zworkforce tests
	PYTHONPATH=. python -m unittest discover -s tests -v

doctor:
	PYTHONPATH=. python -m zworkforce doctor

serve:
	PYTHONPATH=. python -m zworkforce serve

worker:
	PYTHONPATH=. python -m zworkforce worker

docker-build:
	docker build -t zworkforce:2.0.0 .
