# Repository Agent Instructions

- Preserve server-side provider credentials; never place credentials in static assets or model-visible configuration.
- Keep model/tool execution bounded by iterations, attempts, delegation depth, output size and budget.
- Every mutating capability must be deny-by-default and have an explicit policy/approval boundary.
- Every tenant-scoped query must include `tenant_id` or derive it from a stored tenant-scoped task.
- Queue claims and idempotency changes require transactions.
- Add tests for security, state-machine and migration behavior with every runtime change.
- Do not weaken SSRF/path/shell controls for convenience; add explicit configuration gates instead.
- Runtime code supports Python 3.12+ and avoids mandatory external dependencies unless architectural value justifies them.
