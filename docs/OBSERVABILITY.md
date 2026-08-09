# Observability

## Prometheus
`GET /metrics` exposes queue, task, outcome, cost, model/provider, workflow, evaluation, outbox and SLO metrics. The endpoint requires authenticated viewer access.

A scrape example is under `deploy/observability/prometheus.yml` and reads the bearer token from a mounted secret.

## Grafana
`deploy/observability/grafana-dashboard.json` provides a starter dashboard for runtime health, outcomes and AI FinOps.

## OTLP traces

```env
ZWORKFORCE_OTLP_TRACES_ENDPOINT=https://otel.example.com/v1/traces
ZWORKFORCE_OTLP_HEADERS_JSON={"Authorization":"Bearer ..."}
ZWORKFORCE_SERVICE_NAME=zworkforce
ZWORKFORCE_TRACE_SAMPLE_RATE=1
```

v3 wraps provider calls and exports compact OTLP/HTTP JSON spans. A collector remains responsible for batching, retention, sampling policy and backend export.
