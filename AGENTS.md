# AGENTS.md

Maintain zWorkforce as a secure, bounded AI workforce runtime.

- Run `make check` before merge.
- Never expose provider secrets to browser clients.
- Agent loops must have explicit iteration/spend/sub-agent ceilings.
- New file/network/process tools must be deny-by-default where appropriate and have boundary tests.
- State-changing API routes require authorization and audit.
- Preserve task idempotency.
- Keep model IDs configurable.
- Update security/architecture docs for material behavior changes.
