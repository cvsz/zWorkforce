# Security Policy

## Supported Versions

Only the latest release on `main` receives security fixes while Zeto is pre-1.0 production migration software.

## Supported Security Posture

Zeto treats publishing credentials, AI provider credentials, sessions, generated media, approval decisions and audit records as sensitive production data.

## Mandatory Controls

- Secrets are server-side only and must never be committed or embedded in frontend bundles.
- Provider credentials use least privilege and are rotated when exposure is suspected.
- Mutating endpoints require authentication, authorization and audit records.
- Publishing and generation side effects must support idempotency.
- Uploads require MIME/type and size validation; remote media fetches must defend against SSRF.
- Autonomous publishing requires QA/policy approval, budget and frequency limits, plus a kill switch.
- Production traffic uses TLS and sensitive persisted data uses encryption appropriate to the deployment environment.

## Operational Requirements

- Set a unique `SECRET_ENCRYPTION_KEY` in every production environment.
- Set `ADMIN_INITIAL_PASSWORD` through the secret manager before the first production start; never retain the development default.
- Use least-privilege, separately rotatable credentials for each provider and environment.
- Terminate TLS at the trusted ingress and encrypt database and object-storage traffic.
- Never put secrets in browser storage, URLs, logs, error responses, fixtures, or repository files.
- Rotate any credential suspected of exposure and retain the corresponding audit record.
- Run dependency, secret, and container scanning before release.

## Reporting

Report vulnerabilities privately through GitHub Security Advisories for `cvsz/zeto` (or GitHub private vulnerability reporting when enabled). Do not open a public issue containing credentials, tokens, exploit payloads against live systems, personal data, or provider tokens.

## Release Gates

A release is blocked by known critical/high vulnerabilities that affect the deployed configuration, credential leakage, approval bypass, or publication duplication defects.
