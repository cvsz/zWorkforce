# zWorkforce Skywork-Inspired Workspace Upgrade Execution Plan

**Updated:** 2026-08-17  
**Status:** active implementation plan  
**Scope:** workspace UX, conversations/context, artifacts/review, skill lifecycle, sandbox/worktrees, browser automation, notifications and FinOps  
**Reference:** `docs/SKYWORK-CHANGELOG-REVERSE-ENGINEERING.md`

## 1. Mission

Adopt the strongest publicly documented Skywork workspace-agent product patterns where they improve zWorkforce, without copying proprietary code or weakening zWorkforce security and governance.

The target is not a clone. The target is a stronger zWorkforce operator/workspace experience built on existing durable tasks, workflows, artifacts, memory, approvals, MCP, Z.A.R.V.I.S., Zider and FinOps.

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
- tests cover auth, tenancy, traversal, SSRF, skill authority expansion, idempotency, cancellation, retry and rollback;
- required CI/security/package/Windows/release gates are green on the exact candidate SHA.

## 3. Delivery phases

### Phase SW0 — Capability mapping and lifecycle foundation

**Status:** IN PROGRESS

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

Primary implementation:

- `packages/zarvis/services/zarvis-orchestrator/src/skill-catalog.mjs`
- `packages/zarvis/services/zarvis-orchestrator/test/skill-catalog.test.mjs`

Exit criteria:

- existing catalog behavior remains compatible;
- lifecycle tests pass;
- auto-update fails closed on authority expansion;
- prior versions remain resolvable for rollback.

### Phase SW1 — Durable projects and conversations

Add repository-backed entities:

```text
workspace_projects
workspace_conversations
workspace_messages
workspace_message_anchors
workspace_pins
workspace_context_snapshots
```

Required fields include tenant ID, owner/actor, project ID, timestamps, status, title, source task/workflow references and retention policy.

APIs:

```text
POST   /api/v1/workspaces/projects
GET    /api/v1/workspaces/projects
PATCH  /api/v1/workspaces/projects/{id}
POST   /api/v1/workspaces/conversations
GET    /api/v1/workspaces/conversations/{id}
GET    /api/v1/workspaces/conversations?query=
POST   /api/v1/workspaces/conversations/{id}/pin
POST   /api/v1/workspaces/conversations/{id}/archive
DELETE /api/v1/workspaces/conversations/{id}
```

Security:

- every query is tenant scoped;
- conversation IDs are opaque and cannot switch tenant ownership;
- creation happens only after authentication/authorization;
- deletion/forget is audited and retention-aware.

Tests:

- cross-tenant read/write negative tests;
- pin/archive/search persistence;
- restart safety;
- title/autoname validation;
- deletion and retention semantics.

### Phase SW2 — Context budget and compaction

Add explicit context accounting per conversation:

- estimated/actual token budget;
- model-specific context ceiling;
- included message/artifact/memory references;
- compaction threshold and reason;
- compaction artifact hash/version.

`/compact` creates a new attributable summary artifact and context snapshot. It does not overwrite durable conversation history or automatically write long-term memory.

Tests:

- deterministic snapshot membership;
- no cross-tenant memory inclusion;
- compaction rollback/read-old-context;
- oversized attachment handling;
- sensitive-data redaction hooks.

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
- unknown commands fail safely with discoverable help.

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
- CodeQL, dependency review, SBOM/provenance;
- staging E2E for workspace → plan → execute → review → approve → artifact → PR/publish.

## 4. PR sequence

1. `feat/skywork-inspired-workspace-upgrade` — research map, plans and governed skill lifecycle foundation.
2. `feat/workspace-project-conversations` — durable project/conversation schema + API.
3. `feat/workspace-context-commands` — context budget/compaction + slash command registry.
4. `feat/workspace-task-sidecar` — summaries, artifacts, subagent/tool trace projection.
5. `feat/workspace-local-sandbox` — scoped local workspace executor.
6. `feat/workspace-git-worktrees` — branch/worktree adapter and diff/PR workflow.
7. `feat/zider-browser-use-contract` — read/mutate browser tool boundary.
8. `feat/skill-marketplace-reusable-workflows` — signed install/discovery/candidate compiler.
9. `feat/workspace-notifications-finops` — notification center + cost preflight/ledger UX.
10. `feat/workspace-ux-hardening` — Web/WinUI parity, accessibility, E2E and release evidence.

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

Changed packages must also execute their package-native type/build/test/security gates. Production claims remain subject to `docs/PRODUCTION-EVIDENCE.md`.