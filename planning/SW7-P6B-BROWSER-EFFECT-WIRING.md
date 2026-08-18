# SW7-P6B — Browser effect API and Zider execution wiring

Status: implementation candidate on PR branch.

This slice exposes the schema-v8 browser effect ledger through authenticated tenant-scoped API endpoints and wires approved Zider mutations through `begin -> claim -> execute -> finish`.

Safety rules:
- the durable zWorkforce approval task remains the authority;
- claim revalidates approval state before external execution;
- `succeeded` retries are deduplicated without re-execution;
- `executing` and `unknown` are never automatically replayed;
- exceptions after claim are conservatively marked `unknown` where the control plane is reachable;
- manual reconciliation is admin-only;
- the ledger stores digests and bounded codes, not raw form values or credentials.

Remaining SW7 work after merge: governed artifact retrieval/upload, cancellation/crash cleanup, browser evidence/audit receipts, and full browser E2E/security regression coverage.
