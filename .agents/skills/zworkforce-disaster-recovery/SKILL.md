---
name: zworkforce-disaster-recovery
description: Plan and execute zWorkforce backup/restore drills, RPO/RTO validation, and disaster recovery runbooks across PostgreSQL, artifacts, and secrets.
---

# zWorkforce Disaster Recovery

Prove the platform can recover, not just that a backup exists.

## Workflow

1. Identify the failure scenario being planned or drilled: database loss,
   artifact storage loss, secret backend outage, or full-region loss.
2. Confirm backup coverage for PostgreSQL, content-addressed artifacts, and
   any locally mounted secret material relevant to the scenario.
3. Run or review a restore drill end-to-end and verify the restored state is
   actually usable, not merely present on disk or in object storage.
4. Validate RPO/RTO targets against the drill's measured data loss window
   and recovery time, and confirm tenant isolation holds after restore.
5. Document every drill step, command, and timestamp as evidence; do not
   report a drill as passed without captured evidence.

## References

- `scripts/backup-postgres.sh`
- `scripts/restore-postgres.sh`
- `docs/DISASTER-RECOVERY.md`
- `docs/POSTGRESQL.md`

## Output

Report the scenario drilled, backup coverage, restore evidence, measured
RPO/RTO versus target, and any gap that would block a real recovery.
