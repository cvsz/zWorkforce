# Deployment

## Local development
Use SQLite and embedded workers.

## Single host production
Use Docker Compose with PostgreSQL, API, worker and scheduler. Optional outbox runs under the `integrations` profile.

## Kubernetes
`deploy/kubernetes` provides:
- namespace/config/secret example;
- two API replicas;
- two worker replicas + HPA;
- leader-elected scheduler replicas;
- PDBs;
- non-root/read-only/capability-drop security contexts;
- workspace/artifact PVCs;
- default-deny network policy.

Supply `ZWORKFORCE_DATABASE_URL`, API keys and provider credentials through a real secret manager/injector. Replace example secret manifests before deployment.

### Required network work
The supplied NetworkPolicy denies all egress. Add explicit egress for:
- PostgreSQL;
- model providers;
- OIDC discovery/JWKS;
- OTLP collector;
- S3/Qdrant/embedding endpoints;
- approved tool destinations.

## External HA boundary
zWorkforce application processes are horizontally scalable. PostgreSQL, ingress, object/vector stores and observability backends require their own HA/backup design.
