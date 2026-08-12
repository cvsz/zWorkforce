# ZC Services

Python service and enterprise dependency surfaces used by the Z.A.R.V.I.S.
coding/runtime stack.

## Dependency sets

- `app/requirements.txt`: application runtime integrations.
- `requirements-dev.txt`: local quality and test tooling.
- `requirements-enterprise.txt`: optional enterprise integrations.
- `requirements.txt` and `pyproject.toml`: package runtime metadata.

Dependency floors may be updated independently, but the combined installation
must remain resolvable and pass the root ZARVIS workflow. Major tool upgrades are
not accepted when their installed plugin ecosystem declares incompatible peer or
version constraints.
