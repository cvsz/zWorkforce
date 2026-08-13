---
name: zworkforce-incident-response
description: Coordinate zWorkforce production incident triage, containment, rollback, health checks, queue and scheduler diagnosis, provider circuit review, database recovery, security review, communications, and evidence capture.
---

# zWorkforce Incident Response

Prioritize containment and evidence. Avoid speculative fixes until the blast
radius and rollback path are known.

## Incident Loop

1. State severity, affected tenant/domain, start time, customer impact, and
   current mitigation.
2. Check API readiness, worker leases, queue age, scheduler leadership, outbox
   delivery, provider health, PostgreSQL, storage, and recent deploys.
3. Freeze or disable risky automation when mutation safety is uncertain.
4. Decide rollback, hotfix, or hold based on evidence.
5. Record timeline, commands, dashboards, logs, approvals, and residual risk.
6. Close only after validation, monitoring window, and follow-up tasks exist.

## Useful References

- `docs/OPERATIONS.md`
- `docs/OBSERVABILITY.md`
- `docs/DISASTER-RECOVERY.md`
- `docs/PRODUCTION-READINESS.md`
- `deploy/observability/`
- `deploy/kubernetes/`

## Output

Return incident status, confirmed facts, active hypotheses, next action, owner,
rollback decision, and evidence links or file paths.
