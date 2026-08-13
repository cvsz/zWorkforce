# Operations

## Health

```text
GET /health  process liveness
GET /ready   DB + provider readiness
GET /metrics operational metrics
```

## Routine checks

```bash
zworkforce doctor
zworkforce audit-verify --tenant default
zworkforce slo-status --tenant default
zworkforce capacity --tenant default
zworkforce chargeback --tenant default
```

## Worker incidents
- Check queued/dead-letter counts.
- Check provider circuits and credentials.
- Inspect task events and tool events.
- Expired leases are recoverable; do not manually force the same task from two workers.
- Retry dead-letter tasks only after correcting the underlying cause.

## Scheduler incidents
Multiple scheduler instances are safe; a DB lease elects the active instance. Check `service_leases3` if no schedules/events progress.

## Outbox incidents
Outbox payloads remain durable until delivered. Destination handlers should deduplicate on `X-ZWorkforce-Delivery-ID`. Repeated failures back off exponentially.

## PostgreSQL
Monitor connections, storage, locks and backup/PITR status. The application does not replace DB operational controls.

## GitHub operations

Repository branch protection, pull-request gates, dependency maintenance,
release workflows, GHCR packages, and incident triage are documented in
[GITHUB-OPERATIONS.md](GITHUB-OPERATIONS.md). Keep that document current when
adding workflows, required checks, package publishing paths, or GitHub security
features.
