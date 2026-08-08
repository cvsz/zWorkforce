# Deployment

For production set `ZWORKFORCE_ENV=production`, strong API keys, provider credentials/model mappings, budgets and tool allowlists. Run `docker compose up -d --build` behind TLS/private ingress. Persist and back up `zworkforce-data`. Do not run multiple active replicas against the same SQLite file.
