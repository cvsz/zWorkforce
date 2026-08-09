# AGENTS.md

## Repository intent
zWorkforce is a production AI Workforce control plane. Changes must preserve tenant isolation, server-side secrets, bounded execution, explicit mutation authorization and durable state transitions.

## Required validation

```bash
python -m compileall -q zworkforce tests
PYTHONPATH=. python -m unittest discover -s tests -v
zworkforce doctor
```

PostgreSQL changes must also run `tests/test_v3_postgres.py` against a real PostgreSQL service. Runtime changes must not introduce `shell=True` or expose provider secrets in static assets.

## Architecture rules
- Browser/static code never receives provider/storage/database credentials.
- Durable state changes go through repository methods.
- Mutating tools stay deny-by-default and bounded.
- Preserve SQLite compatibility unless a change is explicitly PostgreSQL-only.
- Distributed queue code must be transactional and idempotent.
- Do not claim external infrastructure is provisioned merely because an adapter exists.
