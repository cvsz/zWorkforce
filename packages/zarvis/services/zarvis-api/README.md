# ZARVIS API

FastAPI service for the consolidated Z.A.R.V.I.S. runtime. The canonical service
identity is `zarvis-api`; runtime consumers use `ZARVIS_API_URL` and
`ZARVIS_API_TOKEN`.

## Local validation

```bash
python -m pip install -r requirements.txt pytest pip-audit
python -m pytest tests -q
pip-audit -r requirements.txt
```

Provider, GitHub, Supabase, and infrastructure credentials remain server-side.
Never place real tokens in tests, Compose defaults, logs, or browser code.

## Release gate

The root `ZARVIS` workflow installs this manifest and runs the complete route and
dependency-security test suite. Production promotion additionally requires the
repository security, release-governance, and operator-approval gates.
