# Contributing to Zeto

## Setup

Use Node.js 22.22 or newer within the supported major range.

```bash
npm ci
cp .env.example .env
npm run check
```

## Development workflow

1. Create a focused branch from `main`.
2. Keep changes aligned with one execution-plan vertical slice.
3. Add or update tests for changed behavior; add a failing test before the change where practical.
4. Keep provider calls behind interfaces; document schema or contract changes.
5. Add a changelog entry for user-visible behavior.
6. Run `npm run lint`, `npm test`, `npm audit --audit-level=high`, and container build checks.

## Pull request requirements

- Explain the execution-plan phase and exit criteria addressed.
- Include verification evidence.
- Call out security, data migration and backward-compatibility risks.
- Do not merge known failing required checks.
- Do not commit credentials, `.env` files, tokens, generated private data or production exports.
- Database changes must include forward migration tests and a documented rollback strategy.
- Release claims must distinguish local checks from staging and live-provider evidence.

## Coding boundaries

Keep HTTP concerns, domain/application logic, repositories, providers, workflows and observability separated as described in `ARCHITECTURE.md` and `AGENTS.md`.

## Pull Request Gate

```bash
npm run check
npm audit --omit=dev --audit-level=high
docker build -t zeto:local .
```
