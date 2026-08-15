# Operations Skills

Health, status, and incident workflows for Z.A.R.V.I.S.

- All mutating steps (`restart`, `rollback`, `incident_escalate`) are `approval_rule: human_required`.
- Read-only health/status checks are `mutability: read`.
