---
name: zworkforce-scheduler-events
description: Configure and operate zWorkforce cron/interval schedules and durable event triggers, including dedupe keys, filters, agent/workflow targets, and active/passive leader-elected scheduler HA across replicas.
---

# zWorkforce Scheduler & Event Automation

Turn recurring and reactive work into safe, non-duplicated dispatch.

## Workflow

1. Identify the trigger type (cron expression, fixed interval, or durable
   event) and the target agent or workflow.
2. Define an explicit dedupe key and filter so repeated or overlapping
   triggers cannot double-dispatch the same logical occurrence.
3. Verify which scheduler replica currently holds the leader lease before
   assuming a schedule or event trigger is actively firing.
4. Confirm timezone/interval semantics, catch-up behavior after downtime, and
   backoff for failed dispatch attempts.
5. Trace a full trigger-to-task lifecycle (fire, lease, dispatch, task
   creation) before declaring a schedule or event rule production-ready.

## References

- `zworkforce/scheduler.py`
- `zworkforce/outbox.py`
- `zworkforce/workflow.py`
- `tests/test_v3_scheduler_eval.py`
- `README.md` scheduler/event and leader lease sections

## Output

Report trigger type, dedupe/filter design, leader lease state, dispatch
evidence, and any duplicate-dispatch or missed-occurrence risk.
