# zWorkforce Skywork-Inspired Workspace Upgrade Execution Plan

**Updated:** 2026-08-17  
**Status:** active implementation plan  
**Scope:** workspace UX, conversations/context, artifacts/review, skill lifecycle, sandbox/worktrees, browser automation, notifications, web-product flows and FinOps  
**References:** `docs/SKYWORK-CHANGELOG-REVERSE-ENGINEERING.md`, official Skywork Help changelog surfaces, and the official Skywork Desktop changelog

## 1. Mission

Adopt the strongest publicly documented Skywork workspace-agent product patterns where they improve zWorkforce, without copying proprietary code or weakening zWorkforce security and governance.

The target is not a clone. The target is a stronger zWorkforce operator/workspace experience built on existing durable tasks, workflows, artifacts, memory, approvals, MCP, Z.A.R.V.I.S., Zider, Zeto and FinOps.

## 2. Definition of complete

The upgrade is complete only when all applicable criteria pass:

- project/conversation state is durable and tenant scoped;
- context status and compaction are explicit and auditable;
- artifacts and subagent/tool execution are reviewable from durable evidence;
- local workspace access is sandboxed, allowlisted and bounded;
- git worktree/branch operations are isolated and reviewable;
- browser mutations remain explicit approval-gated actions;
- skill install/update/enable/disable/rollback obey policy and preserve prior versions;
- repeated workflows produce reviewable candidates, never silently activated production skills;
- notifications are tenant scoped and connector delivery is opt-in/policy controlled;
- FinOps preflight and actual usage are backed by durable ledger data;
- social publishing continues through durable approval/outbox/provider boundaries;
- design guidelines are versioned, attributable and enforced by generation/QA policy rather than UI hints only;
- memory imports are previewable, provenance-preserving, consent-based and tenant scoped;
- tests cover auth, tenancy, traversal, SSRF, skill authority expansion, idempotency, cancellation, retry and rollback;
- required CI/security/package/Windows/release gates are green on the exact candidate SHA.

## 3. Delivery phases

### Phase SW0 — Capability mapping and lifecycle foundation

**Status:** IMPLEMENTED / CI GREEN / REVIEW PENDING

Deliverables:

- `docs/SKYWORK-CHANGELOG-REVERSE-ENGINEERING.md` with chronological public feature mapping.
- `ROADMAPS.md` and master execution plan references.
- governed skill lifecycle in Z.A.R.V.I.S. runtime:
  - immediate active resolution after installation;
  - enable/disable;
  - active semantic version selection;
  - safe system-skill automatic update;
  - explicit rollback;
  - no silent tool-capability expansion;
  - no read→write escalation;
  - no approval weakening.
- orchestrator execution must resolve only enabled skill versions; lifecycle state is not presentation-only.

Primary implementation:

- `packages/zarvis/services/zarvis-orchestrator/src/skill-catalog.mjs`
- `packages/zarvis/services/zarvis-orchestrator/src/orchestrator.mjs`
- `packages/zarvis/services/zarvis-orchestrator/test/skill-catalog.test.mjs`
- `packages/zarvis/services/zarvis-orchestrator/test/orchestrator-skill-execution.test.mjs`

Exit criteria:

- existing catalog behavior remains compatible;
- lifecycle tests pass;
- disabled versions cannot execute;
- auto-update fails closed on authority expansion;
- prior versions remain resolvable for rollback;
- affected Z.A.R.V.I.S., root CI, CodeQL, dependency and Windows gates pass on the exact PR head;
- required review/governance approval remains a separate merge gate.

### Phase SW1 — Durable projects and conversations

**Status:** IMPLEMENTED ON STACKED PR / ROOT + POSTGRESQL CI GREEN / WINDOWS + REVIEW PENDING

Use the repository's existing database composition instead of introducing a parallel store. The implemented data layer composes `WorkspaceMixin` with the existing automation/task/FinOps/governance/migration mixins over `DatabaseBase`, with additive schema initialization through `db_base.py`.

Implemented files:

- `zworkforce/db_schema_workspace.py` — additive workspace schema with composite tenant ownership.
- `zworkforce/db_workspace.py` — `WorkspaceMixin` with tenant-scoped project/conversation/message operations.
- `zworkforce/db_base.py` — initializes workspace schema and advances schema version to 5.
- `zworkforce/db.py` — composes `WorkspaceMixin` into the canonical `Database` class.
- `zworkforce/workspace_api.py` — `WorkspaceApp(CoreApp)` routes workspace requests through the existing core auth/security/rate-limit handler without rewriting `api.py`.
- `zworkforce/workspace_cli.py`, `pyproject.toml`, `zworkforce/__main__.py` — route public CLI/module serve entrypoints through `WorkspaceApp` while preserving existing CLI commands.
- `tests/test_workspace.py` — SQLite/data-layer contract.
- `tests/test_workspace_api.py` — API/RBAC/tenant/audit contract.
- `tests/test_v3_postgres.py` — PostgreSQL schema-v5/concurrent-init/workspace round-trip evidence.
- `docs/API.md` — public workspace API and scope contract.

Repository-backed entities:

```text
workspace_projects5
workspace_conversations5
workspace_messages5
```

Messages use a durable per-conversation ordinal because repository timestamps use second precision and therefore cannot by themselves guarantee deterministic replay ordering.

Future SW2 entities may add:

```text
workspace_context_snapshots
workspace_context_members
```

Pin/archive state is stored on project/conversation rows instead of adding a redundant pin table. Foreign keys involving project/conversation ownership include `tenant_id`, so cross-tenant attachment is rejected structurally as well as by repository queries.

Implemented APIs:

```text
POST /api/v1/workspaces/projects
GET  /api/v1/workspaces/projects
GET  /api/v1/workspaces/projects/{id}
POST /api/v1/workspaces/projects/{id}/rename
POST /api/v1/workspaces/projects/{id}/pin
POST /api/v1/workspaces/projects/{id}/archive

POST /api/v1/workspaces/conversations
GET  /api/v1/workspaces/conversations/{id}
GET  /api/v1/workspaces/conversations?q=&project_id=&status=&limit=&offset=
POST /api/v1/workspaces/conversations/{id}/rename
POST /api/v1/workspaces/conversations/{id}/pin
POST /api/v1/workspaces/conversations/{id}/archive
POST /api/v1/workspaces/conversations/{id}/move
POST /api/v1/workspaces/conversations/{id}/messages
GET  /api/v1/workspaces/conversations/{id}/messages
POST /api/v1/workspaces/conversations/{id}/delete
```

Deletion intentionally follows the repository's existing POST-action convention instead of adding a new CORS method. It requires `workspace:delete` plus the admin role. Normal reads require `workspace:read`; normal mutations require `workspace:write`. The external message endpoint accepts only `role=user`; assistant/system/tool history remains an internal runtime authority.

Verified security/reliability properties:

- every query is tenant scoped;
- composite tenant ownership is enforced for project→conversation→message relationships;
- conversation/project IDs are opaque UUIDs and cannot switch tenant ownership;
- creation happens only after authentication/authorization;
- deletion/forget is audited and refused under `compliance_hold`;
- message/artifact references are bounded and validated; raw host paths are not accepted;
- parent message links cannot cross conversations;
- archived conversations remain readable but cannot receive new messages;
- literal search escapes SQL wildcard characters;
- workspace mutation audit records exclude raw message content;
- SQLite restart persistence and PostgreSQL concurrent schema initialization/round trips are covered by CI tests.

### Phase SW2 — Context budget and compaction

**Status:** NEXT IMPLEMENTATION SLICE

Add explicit context accounting per conversation:

- estimated/actual token budget;
- model-specific context ceiling;
- included message/artifact/memory references;
- compaction threshold and reason;
- compaction artifact hash/version.

`/compact` creates a new attributable summary artifact and context snapshot. It does not overwrite durable conversation history or automatically write long-term memory.

Implementation boundary:

- use existing provider usage objects for measured token evidence where available;
- use a clearly labeled deterministic estimate when exact tokenizer usage is unavailable;
- bound chunk count, provider calls, input bytes, retries and total compaction rounds;
- persist provider/model/usage evidence on the snapshot;
- store summary text through the existing artifact store and record artifact hash/ID;
- preserve the original message history for inspect/rollback;
- require explicit `workspace:compact` authorization because compaction incurs model cost and writes durable state.

Tests:

- deterministic snapshot membership;
- no cross-tenant memory inclusion;
- compaction rollback/read-old-context;
- oversized attachment/content handling;
- sensitive-data redaction hooks;
- provider failure/cancel does not replace the previous active snapshot;
- bounded multi-pass behavior.

### Phase SW3 — Slash command and task-composer registry

Commands:

```text
/plan
/review
/compact
/goal
/status
/artifacts
/cost
/skill
/workflow
/feedback
```

Implementation rules:

- parser is presentation-independent;
- server resolves command authorization and capabilities;
- commands cannot bypass normal API/RBAC/policy checks;
- attachment references are artifact IDs, not arbitrary host paths;
- unknown commands fail safely with discoverable help;
- mutating/cost-incurring commands declare scopes and approval requirements explicitly.

### Phase SW4 — Task summary, artifact manifest and execution sidecar

For every task/workflow run expose:

- summary;
- artifacts created/changed;
- review state;
- tool calls with sanitized parameters;
- delegated subagents and parent/child relationships;
- retries/failures/cancellations;
- approvals requested/resolved;
- cost/latency/model route;
- recommended next actions.

The UI can render main chat + review + file preview + side discussion without duplicating authoritative execution state.

### Phase SW5 — Scoped local workspace sandbox

New workspace grant contract:

```json
{
  "tenant_id": "...",
  "workspace_id": "...",
  "root": "operator-approved canonical path",
  "read": true,
  "write": false,
  "commands": ["git", "python", "npm"],
  "network_policy": "deny|allowlisted",
  "expires_at": "ISO-8601"
}
```

Requirements:

- canonicalize before authorization;
- block `..`, symlink/junction escape and device paths;
- subprocesses use argument arrays, no `shell=True`;
- time/memory/output/process limits;
- sanitized environment;
- write/command mutation requires policy/approval as configured;
- audit start/end/exit code without leaking secrets.

### Phase SW6 — Git branch/worktree isolation

Provide an adapter over approved repositories:

- create named feature worktree;
- inspect diff/status;
- run allowlisted checks;
- commit only with explicit mutation authorization;
- open PR through GitHub boundary;
- cleanup expired worktrees safely.

Never allow a task to rewrite protected/default branches directly.

### Phase SW7 — Zider browser-use contract

Browser tools are split into classes:

**Read-only:** navigate, inspect DOM/text, screenshot, extract structured fields.

**Mutating:** click action controls, submit forms, uploads, purchases, account settings, send/publish actions.

Mutating tools require explicit declared intent plus approval/policy where configured. Add domain/URL allowlists, SSRF protections, timeout/cancel, dedupe for external side effects, evidence screenshots/receipts where appropriate and secret-safe logging.

### Phase SW8 — Skill marketplace, discovery and reusable workflow compiler

Build on Phase SW0:

- signed remote skill package install using existing registry trust controls;
- source metadata and publisher/signature evidence;
- immediate activation only inside existing capability envelope;
- safe automatic updates for approved `system` skills;
- manual review for capability expansion;
- discovery score based on task intent, domain, capability fit, outcome quality, latency and cost;
- repeated-workflow detector creates a draft workflow/skill candidate;
- generated candidates require schema validation, policy review and tests before enablement.

### Phase SW8A — Skywork Web changelog integrations

The current Skywork Help landing page exposes three recent web-product changes that map cleanly onto existing zWorkforce subsystems. Treat them as capability references, not implementation dependencies.

#### Social Publishing Flow → Zeto

- extend Zeto's existing content lifecycle rather than create a second publisher;
- composition/approval/scheduling/publish remains `draft → review → approved → scheduled → publishing → live|failed`;
- use existing durable queue/outbox, provider adapters, idempotency keys, audit trail and retry/dead-letter semantics;
- provide social-format templates and platform previews as presentation features only; provider side effects still go through approval/policy.

#### Design Guidelines in Knowledge Base → Brand/Design policy

- store design guideline documents as versioned tenant artifacts/knowledge records with owner, source, hash and effective version;
- project/brand contexts reference guideline versions explicitly;
- generation tools receive derived non-secret design constraints;
- Zeto QA/brand-safety evaluates outputs against the active guideline version;
- zsp-aitool/Zider can preview guidelines but cannot silently modify active production policy.

#### SkyClaw memory import → portable zWorkforce memory import

- add import adapters for operator-supplied AI memory/export files rather than scraping private accounts;
- support preview/dry-run, source/provider label, import batch ID, hash/dedupe, conflict handling and explicit commit;
- imported memory is tenant scoped and records provenance, actor, timestamp and source artifact hash;
- do not treat imported model instructions as trusted system policy;
- redact/reject secrets and unsupported sensitive fields according to tenant policy;
- allow batch rollback/delete through the recorded import batch where retention rules permit.

### Phase SW9 — Notification center and proactive delivery

Durable notifications:

```text
task_completed
approval_required
question_required
task_failed
budget_risk
scheduled_run_completed
agent_stalled
security_policy_denied
```

Support in-app first. External IM/email/connector delivery remains opt-in and uses approved connector boundaries.

### Phase SW10 — FinOps preflight and detailed ledger

Before expensive work:

- estimate model/tool/artifact cost range;
- compare with tenant/task budget;
- warn or deny according to policy;
- record actual provider/model/tool cost events;
- expose chargeback/showback drilldown by tenant/project/task/agent/model.

Do not invent credit balances. Subscription/purchase integration is a separate payment-provider boundary and must not be embedded into agent runtime authorization.

### Phase SW11 — Operator UX parity

Web and Windows surfaces:

- project/conversation navigation;
- pin/archive/search;
- task quick start;
- next-step suggestions;
- context gauge + compact control;
- review/artifact/subagent sidecar;
- Markdown source/rendered toggle;
- safe HTML preview sandbox;
- theme profiles;
- notification center;
- skill manager and version rollback;
- cost/budget panel.

Accessibility requirements include keyboard navigation, screen reader labels, high contrast, reduced motion and non-color status indicators.

### Phase SW12 — Hardening and release evidence

Required suites:

- Python unit/integration/PostgreSQL;
- Node/Z.A.R.V.I.S. package tests;
- Zider extension/server tests;
- Windows build/test/package;
- sandbox path/symlink escape tests;
- command allowlist and cancellation tests;
- browser mutation approval tests;
- skill authority-expansion tests;
- context/tenant negative tests;
- social publish idempotency/provider-fake tests;
- design guideline version/tenant enforcement tests;
- memory import provenance/dedupe/rollback tests;
- CodeQL, dependency review, SBOM/provenance;
- staging E2E for workspace → plan → execute → review → approve → artifact → PR/publish.

## 4. PR sequence

1. `feat/skywork-inspired-workspace-upgrade` — research map, plans and governed skill lifecycle foundation. **Implemented; CI green; review pending.**
2. `feat/workspace-project-conversations` — additive workspace schema/mixin + durable project/conversation/message API. **Implemented; root/PostgreSQL CI green; Windows/review pending.**
3. `feat/workspace-context-commands` — context budget/compaction + slash command registry. **Next implementation slice.**
4. `feat/workspace-task-sidecar` — summaries, artifacts, subagent/tool trace projection.
5. `feat/workspace-local-sandbox` — scoped local workspace executor.
6. `feat/workspace-git-worktrees` — branch/worktree adapter and diff/PR workflow.
7. `feat/zider-browser-use-contract` — read/mutate browser tool boundary.
8. `feat/skill-marketplace-reusable-workflows` — signed install/discovery/candidate compiler.
9. `feat/zeto-design-memory-portability` — social publishing UX alignment, design guideline policy, memory import batches.
10. `feat/workspace-notifications-finops` — notification center + cost preflight/ledger UX.
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

Changed packages must also execute their package-native type/build/test/security gates. PostgreSQL behavior changes must run the real CI PostgreSQL service tests. Production claims remain subject to `docs/PRODUCTION-EVIDENCE.md`.