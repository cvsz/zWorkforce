# Durable browser side effects

Approved browser mutations use the server-authoritative `browser_effects3` ledger.

Lifecycle:

`not_started -> executing -> succeeded | failed | unknown | canceled`

Authenticated endpoints:

- `POST /api/v1/browser-effects` prepares or reuses an idempotent effect bound to an approved mutation task and action SHA-256.
- `GET /api/v1/browser-effects/{id}` reads tenant-scoped state.
- `POST /api/v1/browser-effects/{id}/claim` atomically claims execution after revalidating approval state.
- `POST /api/v1/browser-effects/{id}/finish` records a terminal execution outcome.
- `POST /api/v1/browser-effects/{id}/reconcile` is admin-only and may resolve only `unknown` to `succeeded` or `failed`.

Zider begins and claims an effect before invoking Playwright. A confirmed result is stored as `succeeded` with a SHA-256 digest. Exceptions after claim are treated conservatively as `unknown`; `unknown` and `executing` effects are never automatically replayed. Browser action values, credentials, cookies, and raw form data are not stored in the effect ledger.
