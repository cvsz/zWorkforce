# Z.A.R.V.I.S. Runtime Skills

Runtime skills (this directory) are **product/runtime capabilities** that
Z.A.R.V.I.S. can invoke at runtime. They are distinct from repository coding-agent
skills in `.agents/skills`.

Every skill manifest must declare:
- `id`: stable reverse-domain skill ID
- `version`: semantic version
- `input_schema` / `output_schema`: typed contracts
- `capability_allowlist`: permitted tool/service names
- `mutability`: `read` | `write`; write requires `approval_rule`
- `approval_rule`: `none` | `human_required` | `policy_gate`
- `timeout_seconds` / `max_concurrency` / `retry_policy`
- `idempotency_strategy`: how durable/external effects are deduplicated
- `audit_events`: list of emitted event names
- `owner` / `rollback_policy`

See `packages/contracts/schemas/` for JSON Schema definitions.
