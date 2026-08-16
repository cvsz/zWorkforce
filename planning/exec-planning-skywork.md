# zWorkforce Skywork-Inspired Workspace Upgrade Execution Plan

**Updated:** 2026-08-17  
**Status:** active implementation plan  
**Scope:** workspace UX, durable conversations/context, review/artifacts, governed skills, sandbox/worktrees, browser automation, notifications, Zeto web-product mappings and FinOps  
**Evidence:** `docs/SKYWORK-CHANGELOG-REVERSE-ENGINEERING.md`

## 1. Mission

Adopt the strongest **verified public** Skywork product patterns where they improve zWorkforce, while preserving zWorkforce's existing tenant isolation, durable state, approvals, idempotency, audit/provenance and server-side secret boundaries. This is a zWorkforce-native implementation plan, not a clone.

## 2. Global completion criteria

The upgrade is complete only when all applicable requirements are durable, tenant scoped, authorization-safe, bounded, observable, rollback-capable and tested end-to-end. Documentation or visual similarity alone is not completion.

Mandatory invariants:

- no parallel task scheduler, approval system, tenant model, artifact store, memory store or publishing control plane;
- local workspace access is an explicit canonical-root grant;
- browser/file/shell/publishing mutations remain policy/approval governed;
- skill installation/update cannot silently expand authority;
- context compaction preserves source history and writes attributable artifacts/snapshots;
- imported memory remains untrusted data;
- production claims remain governed by `docs/PRODUCTION-EVIDENCE.md`.

## 3. Delivery phases

### SW0 — Governed skill lifecycle

**Status:** IMPLEMENTED IN PR #83; CI/review gates still control merge.

Implementation:

- immediate resolution of installed enabled skills;
- semantic-version-aware active version selection;
- enable/disable;
- explicit rollback;
- safe automatic update only for approved `source=system` + `update_policy=auto` skills;
- fail closed on tool-capability expansion, read→write escalation or approval weakening;
- `ZarvisOrchestrator.executeSkill()` resolves only enabled versions.

Primary files:

- `packages/zarvis/services/zarvis-orchestrator/src/skill-catalog.mjs`
- `packages/zarvis/services/zarvis-orchestrator/src/orchestrator.mjs`
- corresponding skill-catalog/orchestrator tests.

### SW1 — Durable projects and conversations

**Status:** IMPLEMENTED ON STACKED PR #84; exact-head CI/review gates still control merge.

Architecture:

- additive schema v5 through existing `DatabaseBase` initialization;
- `WorkspaceMixin` composed into canonical `Database`;
- no parallel datastore;
- project → conversation → message ownership uses `(tenant_id,id)` composite keys/FKs;
- messages use per-conversation ordinal ordering rather than wall-clock timestamp alone.

Implemented files:

- `zworkforce/db_schema_workspace.py`
- `zworkforce/db_workspace.py`
- `zworkforce/db_base.py`
- `zworkforce/db.py`
- `zworkforce/workspace_api.py`
- `zworkforce/workspace_cli.py`
- `pyproject.toml`
- `zworkforce/__main__.py`
- `tests/test_workspace.py`
- `tests/test_workspace_api.py`
- PostgreSQL coverage in `tests/test_v3_postgres.py`
- API contract in `docs/API.md`.

API contract:

```text
GET/POST /api/v1/workspaces/projects
GET      /api/v1/workspaces/projects/{id}
POST     /api/v1/workspaces/projects/{id}/rename|pin|archive
GET/POST /api/v1/workspaces/conversations
GET      /api/v1/workspaces/conversations/{id}
POST     /api/v1/workspaces/conversations/{id}/rename|pin|archive|move
GET/POST /api/v1/workspaces/conversations/{id}/messages
POST     /api/v1/workspaces/conversations/{id}/delete
```

Scopes:

- read: `viewer + workspace:read`;
- normal mutation: `operator + workspace:write`;
- deletion: `admin + workspace:delete`;
- external message creation accepts only `role=user`;
- `compliance_hold` blocks deletion;
- audit excludes raw message bodies.

### SW2 — Context status, compaction and slash commands

**NEXT IMPLEMENTATION SLICE.**

Deliver:

- `workspace_context_snapshots` and membership records;
- measured provider token usage where available; deterministic estimates clearly labeled when exact tokenization is unavailable;
- model-specific context ceiling/configuration;
- explicit `/compact` creating a versioned content-addressed summary artifact + context snapshot;
- source conversation history remains intact;
- previous active snapshot remains valid on provider failure/cancel;
- bounded input bytes, chunks, provider calls, retries and compaction rounds;
- new `workspace:compact` authorization for durable/cost-incurring compaction;
- slash-command registry for `/plan`, `/review`, `/compact`, `/goal`, `/status`, `/artifacts`, `/cost`, `/skill`, `/workflow`, `/feedback`.

Tests: tenant isolation, deterministic membership, rollback/history, provider failure, cancellation, oversized content, sensitive-data redaction hooks and hard resource bounds.

### SW3 — Task summary / artifact / subagent sidecar

Project existing durable execution evidence into:

- task/workflow summary;
- artifacts created/changed;
- review/approval state;
- sanitized tool calls;
- delegated subagent hierarchy;
- retries/failures/cancellation;
- cost/latency/model route;
- evidence-based next actions.

Do not duplicate authoritative execution state in the UI.

### SW4 — Scoped local workspace sandbox

Contract includes tenant/workspace ID, operator-approved canonical root, read/write flags, command allowlist, network policy and expiry.

Required controls:

- path canonicalization before authorization;
- deny `..`, symlink/junction/device escape;
- subprocess argv arrays only; no `shell=True`;
- sanitized environment;
- time/memory/output/process limits;
- cancellation and cleanup;
- explicit approval/policy for write/command mutations;
- secret-safe audit evidence.

### SW5 — Git branch/worktree isolation

- isolated feature worktree from an approved repository;
- status/diff/check execution;
- commits only with mutation authorization;
- protected/default branches never rewritten directly;
- PR delivery through GitHub boundary;
- expired worktree cleanup with lease/evidence.

### SW6 — Zider browser-use contract

Split tools into read-only versus mutating classes. Mutating form submissions, uploads, purchases, account changes and publishing require explicit intent plus policy/approval. Add URL/domain allowlists, SSRF controls, timeouts/cancel, idempotency for external side effects and evidence capture.

### SW7 — Signed skill marketplace + reusable workflow candidates

- existing signed skill-registry trust boundary;
- publisher/source/signature metadata;
- immediate activation only inside existing capability envelope;
- capability expansion requires explicit review;
- discovery scoring from intent/capability/outcomes/cost/latency;
- repeated workflow detection creates **draft candidates** only;
- validation, tests and approval required before activation.

### SW8 — Notifications and proactive operator center

Durable events for completion, approval required, question required, failure, budget risk, scheduled run, stalled agent and policy denial. In-app first; external delivery remains opt-in through approved connectors.

### SW9 — Skywork Web capability mappings

#### Zeto social publishing

Improve compose/preview/approve/schedule/publish UX using the existing Zeto workflow, provider adapters, queue/outbox, idempotency, retry/dead-letter and audit controls.

#### Design guidelines

Versioned tenant artifacts/knowledge with owner/source/hash/effective version; project/brand bindings; server-side generation constraints; QA evidence; controlled activation/rollback.

#### Portable AI-memory import

Operator-supplied export files only; preview/dry-run, source label, artifact hash, import batch, dedupe/conflicts, policy redaction, explicit commit and batch rollback/delete where retention permits. Imported instructions never become system policy or permissions.

### SW10 — FinOps preflight

Estimate model/tool/artifact spend ranges, compare against tenant/task budgets, warn/deny through policy, record actual usage, and expose drilldown by tenant/project/task/agent/model. Do not invent balances.

### SW11 — Web/WinUI operator UX

- projects/conversation navigation, search, pin/archive;
- task quick start and next-action suggestions;
- context gauge + explicit compact control;
- review/artifact/subagent sidecar;
- safe HTML/artifact preview;
- theme profiles;
- notifications;
- skill manager/version rollback;
- cost/budget panel;
- keyboard, screen-reader, high-contrast and reduced-motion accessibility.

### SW12 — Hardening and release evidence

Run affected Python/PostgreSQL, Z.A.R.V.I.S., Zider, Windows, security, dependency, CodeQL, SBOM/provenance, sandbox escape, approval, tenant isolation, import provenance, Zeto publishing/idempotency and staging E2E tests. Record rollback/evidence; do not substitute CI simulations for external production evidence.

## 4. PR sequence

1. `feat/skywork-inspired-workspace-upgrade` — research/roadmap + governed skill lifecycle. **Implemented.**
2. `feat/workspace-project-conversations` — durable project/conversation/message store + API. **Implemented as stacked PR.**
3. `feat/workspace-context-commands` — context snapshots/compaction + slash commands. **Next.**
4. `feat/workspace-task-sidecar` — review/artifact/subagent projection.
5. `feat/workspace-local-sandbox` — scoped local executor.
6. `feat/workspace-git-worktrees` — isolated coding workspaces.
7. `feat/zider-browser-use-contract` — browser read/mutate boundary.
8. `feat/skill-marketplace-reusable-workflows` — signed install/discovery/candidate compiler.
9. `feat/zeto-design-memory-portability` — social publishing/design policy/memory imports.
10. `feat/workspace-notifications-finops` — notifications + budget/usage UX.
11. `feat/workspace-ux-hardening` — Web/WinUI parity, accessibility, E2E and release evidence.

## 5. Validation baseline

```bash
python -m compileall -q zworkforce tests scripts
PYTHONPATH=. python -m unittest discover -s tests -v
zworkforce doctor
pnpm --dir packages/zarvis install --frozen-lockfile
pnpm --dir packages/zarvis peers check
pnpm --dir packages/zarvis test
pnpm --dir packages/zarvis audit --audit-level high
python scripts/verify_release.py --expected 3.0.3
```

PostgreSQL behavior changes must run the real CI PostgreSQL service tests. Production readiness remains subject to `docs/PRODUCTION-EVIDENCE.md`.