---
name: zworkforce-workflow-design
description: Design, review, and document zWorkforce durable workflows, schedules, event rules, DAG steps, occurrence keys, idempotency, retries, approvals, and evaluation criteria for production automation.
---

# zWorkforce Workflow Design

Design workflows that can be retried safely and audited after failure.

## Workflow Model

1. Define trigger: manual task, workflow, schedule, or event rule.
2. Define agent ownership for each step and keep mutating steps isolated.
3. Use explicit dependencies; reject cycles and hidden ordering assumptions.
4. Add occurrence/dedupe keys for schedules and events.
5. Add success criteria, timeout/retry posture, approval gates, and rollback
   evidence for every mutating step.
6. Add evaluation criteria when model/provider strategy can change outcomes.

## Required Fields

For each step specify:

- `id`
- `agent_id`
- `prompt`
- `depends_on`
- `mutating`
- `success_criteria`
- `max_attempts`
- required artifacts or memory writes

## Validation

Use `docs/WORKFLOWS.md`, `tests/test_v3_workflow.py`,
`tests/test_v3_scheduler_eval.py`, and `tests/test_production_fixes.py` as the
minimum reference set before changing workflow semantics.
