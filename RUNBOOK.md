# Z.A.R.V.I.S. Production Runbook

This runbook provides concise operational procedures for managing Z.A.R.V.I.S. in production. For comprehensive details, please refer to the primary documentation in the `docs/` directory:

- [Disaster Recovery](docs/DISASTER-RECOVERY.md)
- [Operations](docs/OPERATIONS.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Secret Management](docs/SECRET-MANAGEMENT.md)
- [Observability](docs/OBSERVABILITY.md)

## Incident Response
1. Assess the scope and impact of the incident.
2. Check observability dashboards (`docs/OBSERVABILITY.md`) to identify failing components.
3. If critical infrastructure is down, consult `docs/DISASTER-RECOVERY.md`.
4. Escalate as necessary based on severity.

## Rollback / Deployment Rollback
If a recent deployment has caused instability:
1. Identify the stable version or commit prior to the incident.
2. Follow the rollback procedures detailed in `docs/DEPLOYMENT.md`.
3. Verify system health post-rollback.

## Database Recovery
In the event of database corruption or data loss:
1. Identify the most recent healthy backup.
2. Follow the recovery steps outlined in `docs/DISASTER-RECOVERY.md`.
3. Verify data integrity and application functionality post-recovery.

## Scheduler/Queue Recovery
If background tasks or message queues are stalled:
1. Check the queue status metrics (`docs/OBSERVABILITY.md`).
2. Restart the scheduler/queue worker processes as per `docs/OPERATIONS.md`.
3. Monitor for queue drain and error rates.

## Provider Circuit Reset
When a third-party provider experiences prolonged outages:
1. Verify the provider's status page.
2. If the provider is back online but circuits remain open, follow the reset procedure in `docs/OPERATIONS.md`.
3. If necessary, configure a fallback provider as documented.

## Backup Restore
To perform a routine or emergency backup restore:
1. Ensure the destination environment is prepared.
2. Execute the restore script according to `docs/DISASTER-RECOVERY.md`.
3. Validate the restored data against expected metrics.
