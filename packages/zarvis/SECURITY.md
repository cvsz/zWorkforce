# Security Policy

## Non-negotiable boundaries

- Never commit secrets, API keys, wallet seeds, private keys, MPC shares, payment credentials, or production identifiers.
- Provider keys remain server-side; browser and IDE clients receive scoped, short-lived credentials only.
- Financial operations must be idempotent, auditable, and isolated from AI execution.
- AI agents cannot access signing, payment, or card-data boundaries.
- Infrastructure changes require explicit operator approval; automated workflows must validate and plan only.

## Reporting

Report suspected vulnerabilities privately to the repository owner. Do not disclose exploitable details in public issues.
