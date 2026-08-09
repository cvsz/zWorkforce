# Providers

zWorkforce supports OpenAI-compatible `/chat/completions` providers and a deterministic built-in mock provider.

Each provider can define `name`, `kind`, `base_url`, `api_key` or `api_key_env`, `priority`, `timeout_seconds`, `retries`, `models.luna|terra|sol`, and `enabled`.

At runtime the pool tries healthy providers in ascending priority. Providers without a model for the requested tier are skipped. Consecutive failures open a temporary circuit; a healthy fallback can serve the turn. Health derives from real calls rather than synthetic requests that could consume quota.

Provider pricing is intentionally not fetched automatically in v2. Credit rates are explicit configuration so accounting remains deterministic and auditable when external prices change.
