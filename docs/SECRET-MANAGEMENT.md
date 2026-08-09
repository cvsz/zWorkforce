# Secret Management

zWorkforce supports direct values for development, but production should resolve sensitive values through an external secret boundary wherever possible.

## Secret classes

Treat the following as secrets:

- PostgreSQL credentials;
- bootstrap/API keys;
- provider API keys;
- OIDC client/private credentials where applicable;
- signed-proxy HMAC keys;
- remote skill signing/verification keys when private material is used;
- webhook/outbox HMAC secrets;
- Qdrant/S3 credentials;
- embedding-provider keys;
- Vault/AWS authentication material.

Never put these values in Git, Docker image layers, frontend assets, release notes or issue/PR text.

## Supported references

Runtime secret references can use:

- `env://NAME` — value comes from a server process environment variable;
- `file:///path/to/secret` — mounted secret file;
- `file:///path/to/object.json#field` — JSON field from a mounted secret file;
- Vault KV v2 references when Vault integration is configured;
- AWS Secrets Manager references when the AWS optional dependency and workload identity are configured.

Prefer workload identity and short-lived credentials over static cloud access keys.

## CLI-generated API keys

Create a persistent API key with:

```bash
zworkforce key-create --name automation --role operator --scopes workforce:read
```

The command writes the one-time plaintext secret to a newly created mode-0600 file under
`$ZWORKFORCE_DATA_DIR/api-keys/` and prints only non-sensitive metadata, including the file path.
Use `--secret-file PATH` to choose a different destination; existing files are never overwritten.
The database stores a salted PBKDF2-HMAC-SHA256 verifier, not the plaintext secret. Move the file
into the approved secret-management boundary and remove local copies after registration.

## Kubernetes

`deploy/kubernetes/secret.example.yaml` is a schema/example only. Do not commit a populated copy.

Recommended production patterns:

1. External Secrets/Secrets Store CSI/another approved controller reads from the organization secret manager.
2. Secrets are mounted as files or injected as environment variables only into the workloads that require them.
3. Kubernetes service accounts use cloud workload identity rather than embedded cloud keys.
4. Network policy restricts workloads from reaching secret backends they do not require.

## Docker Compose

Keep `.env` outside source control and restrict file permissions. For higher assurance, use Docker secrets or an external secret injector and point zWorkforce at mounted files.

## Rotation

Define rotation owners and cadence for every secret class. Rotation procedure should:

1. create the replacement secret;
2. deploy/configure consumers to accept/use the replacement;
3. verify health and authentication;
4. revoke the old secret;
5. confirm the old credential no longer works;
6. record the rotation in the operational audit/change system.

API key rotation is supported without reusing the same plaintext secret. Provider/signing secret rotation must account for in-flight calls/signatures.

## Incident response

If secret exposure is suspected:

1. revoke/rotate the credential first;
2. preserve logs/audit evidence;
3. identify every system where the credential was accepted;
4. inspect task/tool/integration activity during the exposure window;
5. rotate related signing credentials if authenticity may be compromised;
6. invalidate leaked build/deployment artifacts if they contained the secret.

Repository history cleanup alone does not revoke a credential.
