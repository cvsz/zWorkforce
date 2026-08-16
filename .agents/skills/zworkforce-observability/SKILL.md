---
name: zworkforce-observability
description: Configure and validate zWorkforce OTLP/HTTP JSON tracing, Prometheus metrics, and the Grafana dashboard so operations reflect real task, agent, and provider activity.
---

# zWorkforce Observability

Make platform behavior debuggable and SLOs enforceable.

## Workflow

1. Identify the domain under review (task runtime, scheduler/outbox
   leadership, provider pool, workflow execution, or API layer) and its
   expected trace spans and metric names.
2. Verify OTLP/HTTP JSON trace export is enabled and spans cover the full
   task lifecycle: submission, lease, tool execution, and completion.
3. Confirm Prometheus metrics exist for the SLOs being enforced (latency,
   error rate, queue age, provider circuit state) and that the Grafana
   dashboard panels are wired to those exact metric names.
4. Flag any area with dashboard panels but no underlying metric, or metrics
   with no alerting/SLO tied to them, before declaring it observable.
5. Reproduce a real failure or slow path and confirm it is visible in traces
   and metrics before closing out the review.

## References

- `zworkforce/telemetry.py`
- `zworkforce/metrics.py`
- `docs/OBSERVABILITY.md`
- `deploy/observability`

## Output

Report instrumented spans/metrics, dashboard coverage, SLO alignment, and any
blind spots that need additional instrumentation.
