# SW7 — Governed Browser Mutation Completion Ledger

Status: **repository-side completion candidate on PR #153**.

SW7 establishes the production browser automation boundary between Zider and the durable zWorkforce control plane. Mutating browser actions are never authorized by local Zider state alone: the durable zWorkforce approval task remains the authority, external side effects are fenced by a tenant-scoped idempotency ledger, ambiguous outcomes are non-replayable, and network destinations are revalidated and pinned.

## Delivered slices

- **SW7-P3 / PR #142 — Durable mutation approval adapter**
  - binds the exact browser action to a durable zWorkforce approval task;
  - rejects expired, canceled, rejected, mismatched, malformed, or insufficient approvals;
  - keeps sensitive selector/value/query material out of approval evidence.
- **SW7-P4 / PR #143 — Approved browser mutation execution**
  - executes approved `click` and `submit` only through the governed runtime;
  - keeps mutation-capable Playwright disabled unless zWorkforce approval mode is configured.
- **SW7-P5 / PRs #144 and #149 — Redirect-hop revalidation / repinning**
  - disables implicit redirect following;
  - re-runs allowlist, DNS and public-address policy on each read-only redirect hop;
  - recomputes Host/TLS authority, bounds redirects, canonicalizes destinations, and rejects HTTPS downgrade;
  - mutation-triggered redirects remain fail-closed when side-effect outcome is ambiguous.
- **SW7-P6 / PRs #145, #146 and #150 — Durable per-action idempotency and reconciliation**
  - schema-v8 tenant-scoped browser-effect ledger;
  - lifecycle `not_started -> executing -> succeeded|failed|unknown|canceled`;
  - atomic exactly-once claim, deterministic replay dedupe for succeeded effects, no automatic replay for `executing`/`unknown`, and admin-only reconciliation.
- **SW7-P7 / PRs #147, #151 and #148 — Governed uploads and cancellation/crash cleanup**
  - tenant-scoped artifact retrieval using dedicated `artifact:read`, digest/size verification and in-memory Playwright uploads only;
  - no host filesystem upload paths;
  - cancellation before/during/after external execution is conservatively classified so ambiguous mutations become `unknown` and are never replayed automatically;
  - browser/page/context teardown remains deterministic on abort, timeout and crash.
- **SW7-P8 / PR #152 — Sanitized browser evidence**
  - whitelisted per-action evidence envelope with sanitized destination, effect reference, result digest, redirect count, timestamps and runtime metadata;
  - optional mutation screenshot provenance is digest-only and excludes raw image payloads;
  - credentials, cookies, authorization headers, form values and secret query/fragment material are excluded by construction and regression tests.
- **SW7-P9 / PR #153 — Full browser E2E/security regression matrix**
  - composes `AgentRunner -> DurableBrowserEffectExecutor -> PinnedBrowserExecutor`;
  - covers approved mutation, DNS rebinding/pin enforcement, private destination denial, approval replay denial, redirect revalidation/repinning, mutation redirect ambiguity, cancellation, crash, timeout, evidence redaction and unknown-effect no-replay.

## Safety invariants

- Durable zWorkforce approval is the sole mutation authority.
- Tenant and actor boundaries are enforced by the authenticated control plane.
- Every mutation is bound to an action digest, approval task and bounded idempotency key.
- `succeeded` retries deduplicate without external re-execution.
- `executing` and `unknown` are never automatically replayed.
- Cancellation, timeout, crash and post-invocation completion ambiguity fail closed toward a non-replayable state.
- Browser destinations must remain allowlisted, public, freshly resolved and pinned; redirects never bypass policy.
- Uploads use governed artifact bytes, never arbitrary host paths.
- Durable evidence stores bounded metadata/digests rather than raw secrets, form values or mutation screenshots.

## Completion gate

SW7 is repository-side complete only when PR #153 is merged after all required exact-head GitHub checks pass on a branch synchronized with current `main`. Production deployment evidence is tracked separately in `docs/PRODUCTION-EVIDENCE.md`; repository completion does not imply that external staging/production drills have passed.
