# Deployment

## Local development

Use the mock provider and embedded worker:

```bash
python -m zworkforce serve
```

## Single-host production

Recommended topology:

```text
reverse proxy / TLS
       |
       v
 zworkforce api ---- SQLite WAL on local durable volume
                         ^
                         |
                  zworkforce worker(s)
```

Run API with `ZWORKFORCE_EMBEDDED_WORKERS=0` and one or more worker processes that share the same reliable local durable volume.

## Reverse proxy

Terminate TLS at a hardened reverse proxy and forward only the application port internally. Preserve `X-Request-ID` when possible. Do not trust identity headers unless `ZWORKFORCE_TRUST_PROXY_IDENTITY=true` and the proxy generates the required HMAC signature.

## Persistent storage

Back up SQLite consistently with WAL state. Prefer a filesystem/storage snapshot while processes are quiesced or SQLite's backup API. Do not copy only the main DB file while WAL writes are active.

## Scaling boundary

Multiple workers on one host/local filesystem are supported. Cross-host SQLite on NFS/SMB is not a supported HA architecture. Use a future PostgreSQL/managed queue adapter for multi-host fleets.

## Secrets

Inject API/provider/signing/proxy secrets from the deployment secret store. Never place real secrets in `.env.example`, image layers, Compose source or Git history.
