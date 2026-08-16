---
name: zworkforce-secret-management
description: Configure and audit zWorkforce secret references sourced from environment variables, mounted files, AWS Secrets Manager, and Vault KV v2, without ever exposing plaintext secret values.
---

# zWorkforce Secret Management

Keep provider, storage, and signing secrets resolvable and rotatable without
ever printing them.

## Workflow

1. Identify which secret (provider API key, database credential, signing
   key, webhook HMAC key, etc.) is being configured and which backend it
   should resolve from: environment, mounted file, AWS Secrets Manager, or
   Vault KV v2.
2. Verify the secret reference syntax resolves to the correct backend and
   path without requiring a code change to rotate the underlying value.
3. Confirm the secret never crosses into browser/static code, logs, audit
   records, error messages, or skill/agent prompt output.
4. Check that rotation and revocation work without downtime for the affected
   provider, database, or signing boundary.
5. Never print, echo, or reconstruct secret plaintext while doing this work;
   report presence, source, and validity only.

## References

- `zworkforce/secret_store.py`
- `docs/SECRET-MANAGEMENT.md`
- `docs/THREAT-MODEL.md`
- `tests/test_v3_secret_store.py`

## Output

Report which secrets were reviewed, their configured backend, rotation
readiness, and any exposure risk found — never the secret values themselves.
