# Workflows, schedules and events

## Workflow DAG

A workflow contains 1–64 steps. Each step names an agent, prompt and optional dependencies.

```json
{
  "id":"release-review",
  "definition":{"steps":[
    {"id":"review","agent_id":"software-engineer","prompt":"Review {{input.repository}}"},
    {"id":"summary","agent_id":"management","depends_on":["review"],"prompt":"Summarize {{steps.review.result}}"}
  ]}
}
```

Cycles, unknown dependencies, duplicate IDs and empty prompts are rejected before persistence.

## Scheduling

Supported schedule types:
- `interval` with `interval_seconds >= 1`
- standard 5-field cron with IANA timezone

Day-of-month/day-of-week follows Vixie/POSIX cron behavior: when both are restricted, either may match.

Scheduler processes use a renewable database leader lease. Multiple replicas may be deployed; only the current leader dispatches.

## Events

Events contain `event_type`, `source`, `payload` and optional `dedupe_key`. A non-empty dedupe key is unique per tenant/source. Event rules can filter payload subsets and target an agent or workflow.

Agent-target payload templates must produce `prompt`. Template substitution supports `{{event.key}}`.
