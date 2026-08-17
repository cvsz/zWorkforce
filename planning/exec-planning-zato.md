# Zeto Execution Plan

**Updated:** 2026-08-15

> Repository: `cvsz/zeto`
>
> Product target: **Zeto ProMeta Master Professional — Enterprise-grade Production Release**
>
> Baseline: v1.1.0 Facebook Page automation dashboard evolving into a complete AI Content Factory.
>
> Visual reverse-engineering note: the Z.A.R.V.I.S. requirements below are derived from the supplied screenshot and the recorded operator demo (`videoplayback.mp4`, ~251.84 s, 640×360, 30 fps). The authoritative reverse-engineering and implementation specification for **M12 — Z.A.R.V.I.S. Operator Runtime** is `docs/JARVIS-VIDEO-REVERSE-ENGINEERING.md`; this plan defers to it for state-transition semantics, contracts, schemas, event catalog, persistence, SLOs and acceptance criteria.

## 1. Mission

Zeto is a production-grade AI Content Factory and operator control plane executing the complete lifecycle:

```text
IDEATE → GENERATE → WRITE → APPROVE → SCHEDULE → PUBLISH → MONITOR → LEARN
```

The operating model is ProMeta/P-MASTER:

```text
ROLE → INPUTS → MODES → CONSTRAINTS → OUTPUT → SELF-CHECK → EVIDENCE → OPTIMIZE
```

Every major AI module supports:

- `PRODUCTION` — create the requested artifact.
- `OPS` — operate the capability continuously and safely.
- `OPTIMIZE` — learn from persisted metrics and improve future outputs.
- `REVIEW` — inspect evidence, policy, quality, cost, and reliability before promotion.

The existing Facebook implementation is the first production publishing adapter, not a disposable prototype.

## 2. Definition of Complete

The project is **not complete** because a feature exists in a mockup. Final completion requires all applicable items below:

- Production implementation, not placeholders.
- Authenticated and authorized API boundary.
- Durable persistence and restart safety.
- Typed/validated contracts.
- Idempotent mutations and side effects.
- Audit/provenance evidence.
- Unit, integration, API-contract, workflow, provider-fake, security and end-to-end tests.
- Observability: logs, metrics, traces and actionable alerts.
- Failure, retry, timeout, cancellation and recovery semantics.
- Security review and no known critical/high defects.
- Operator documentation and rollback/runbook coverage.
- CI green on protected `main`.
- Staging proof for the complete factory workflow.

No phase may be marked complete solely from documentation or UI appearance.

## 3. Current Baseline

Implemented baseline capabilities include:

- Dashboard and KPI overview.
- Facebook rich-text/photo publishing.
- Local post queue.
- Cron scheduler.
- Facebook Page feed management.
- Publish history.
- Settings UI and server-side configuration.
- Analytics and AI Generator UI entry points.
- Express backend and static SPA frontend.
- JSON-backed persistence.
- Google Drive media integration.

Current technical debt / gaps:

- Local JSON persistence instead of PostgreSQL.
- No durable distributed queue.
- No complete workflow/approval state machine.
- Legacy `/api` dominates; `/v1` migration is incomplete.
- No provider-neutral model router with production fallback evidence.
- No complete observability stack.
- Test coverage is newly bootstrapped and incomplete.
- No global policy engine for generated assets.
- Facebook is the only production publishing adapter.
- Legacy product references remain in parts of the UI/storage namespace.

## 4. Repository and Product Identity

Canonical identity:

```text
cvsz/zeto
@zeaz/zeto
Product name: Zeto
```

Rules:

- `Zeto` is the platform/product.
- `Facebook Adapter` is one integration inside Zeto.
- New code must not introduce `zfbauto` as a namespace.
- Legacy browser storage keys may be read temporarily for migration, but new writes use `zeto_*` keys.
- Repository, CI, deployment, badges, webhooks, GitHub Apps and environments must reference `cvsz/zeto`.

Migration checklist:

- [x] Canonical GitHub repository is `cvsz/zeto`.
- [x] Package is `@zeaz/zeto`.
- [x] README product identity uses Zeto.
- [x] Execution plan exists.
- [x] Runtime health service identity uses `zeto` on the implementation branch.
- [x] Replace remaining UI labels containing `zfbauto` or `FB Auto` when they refer to the product rather than the Facebook adapter.
- [x] Update clone URLs and documentation links after GitHub rename.
- [ ] Remove remaining stale product labels in UI/source/storage migration paths.
- [ ] Update CI/CD repository references, deployment targets, badges, webhooks, GitHub App configuration, and environment integrations.
- [ ] Preserve redirects from the old GitHub repository URL where GitHub provides them.
- [ ] Verify branch protection, environments and secrets.
- [ ] Verify deployment targets and external webhooks.

## 5. Target Architecture

```mermaid
flowchart LR
    UI[Zeto Dashboard] --> API[/v1 API Gateway]
    HUM[Z.A.R.V.I.S. Operator View] --> API
    API --> AUTH[Auth / RBAC / Policy]
    API --> IDEAS[M01 Strategy]
    API --> GEN[M02-M05 Generation]
    API --> QA[M10 QA & Approval]
    API --> PUB[M06 Calendar & Publishing]
    API --> MON[M07 Monitoring]
    API --> BI[M08 Analytics]
    API --> ORCH[M09 Orchestrator]

    ORCH --> QUEUE[Durable Job Queue]
    QUEUE --> WORKERS[Worker Pool]
    ORCH --> EVENTS[Event Bus / Outbox]

    GEN --> ROUTER[AI Model Router]
    ROUTER --> IMG[Image Providers]
    ROUTER --> VIDEO[Video Providers]
    ROUTER --> AUDIO[Audio Providers]
    ROUTER --> LLM[LLM Providers]

    PUB --> ADAPTERS[PublishingProvider]
    ADAPTERS --> FB[Facebook]
    ADAPTERS --> IG[Instagram]
    ADAPTERS --> YT[YouTube]
    ADAPTERS --> TT[TikTok]
    ADAPTERS --> X[X]
    ADAPTERS --> LI[LinkedIn]

    API --> DB[(PostgreSQL)]
    WORKERS --> DB
    WORKERS --> OBJ[(Object Storage)]
    API --> OBS[Logs / Metrics / Traces / Audit]
    HUM --> OBS
```

Architecture principles:

1. Provider secrets stay server-side.
2. Every mutation is authenticated, authorized, validated, auditable and idempotent.
3. Platform-specific publishing code remains behind adapters.
4. AI generation remains provider-neutral with bounded fallback and cost policy.
5. Human approval remains possible even with `AUTO_PILOT=true`.
6. Every async job has ownership, retry, timeout, cancellation and failure semantics.
7. Every generated artifact records provenance/version/cost/model route.
8. Public application APIs converge under `/v1`.
9. UI telemetry must be derived from persisted/runtime state; never fabricate KPI values.
10. Autonomous remediation may prepare changes, but release promotion remains evidence-gated.

## 6. Core Domain Model

Minimum production entities:

```text
brands
brand_kits
users
roles
provider_credentials
ideas
assets
asset_variants
captions
posts
schedules
publications
metrics_daily
mentions
sentiment_scores
competitors
workflows
workflow_runs
workflow_steps
approvals
model_routes
cost_events
alerts
audit_events
operator_sessions
system_snapshots
agent_states
maintenance_runs
release_evidence
```

Canonical `Asset` contract:

```json
{
  "id": "asset_id",
  "type": "image|video|audio|caption",
  "prompt_hash": "sha256",
  "seed": "provider_seed",
  "brand_delta_e": 0,
  "lufs": -14,
  "ar": "9:16",
  "tags": [],
  "score": 0,
  "status": "draft|review|approved|blocked|published",
  "version": 1
}
```

Canonical `Post` contract:

```json
{
  "id": "post_id",
  "asset_ids": [],
  "caption": "",
  "hashtags": [],
  "platform": "facebook",
  "slot": "ISO-8601",
  "status": "queued|live|failed",
  "permalink": "",
  "retry_count": 0
}
```

Canonical `OperatorSnapshot` contract:

```json
{
  "generated_at": "ISO-8601",
  "mode": "OPERATOR|AUTO-PILOT",
  "system_state": "ONLINE|DEGRADED|PAUSED",
  "neural_load": 0,
  "confidence": 0,
  "focus": "APPROVAL|PUBLISHING|MONITORING|INCIDENT",
  "queue_depth": 0,
  "approval_backlog": 0,
  "failed_jobs": 0,
  "modules": [],
  "alerts": []
}
```

## 7. Module Delivery Matrix

| Module | Capability              | Primary production output          | Ops responsibility   | Optimization loop             |
| ------ | ----------------------- | ---------------------------------- | -------------------- | ----------------------------- |
| M01    | Strategy & Ideation     | Scored ideas, pillars, hooks       | Daily idea standup   | Recalibrate idea scoring      |
| M02    | AI Image                | Image prompts + variants           | Batch generation     | Style-token performance       |
| M03    | AI Video                | Reel/avatar/B-roll specs           | Render queue         | Retention-curve tuning        |
| M04    | AI Music & Audio        | Jingles, loops, stings, sonic logo | Audio library ops    | Track/watch-time correlation  |
| M05    | Captions/Hooks/Hashtags | Platform-ready copy                | Daily caption packs  | Hook/CTA analysis             |
| M06    | Calendar & Auto-Post    | Content calendar                   | Idempotent publisher | Best-time recompute           |
| M07    | Monitoring & Sentiment  | Alerts/digests/replies             | Social listening     | Threshold tuning              |
| M08    | Analytics Dashboard     | KPI/dashboard views                | Daily factory report | Weekly executive review       |
| M09    | Automation & API        | End-to-end workflows               | Pipeline health      | Cost/latency optimization     |
| M10    | QA/Brand Safety         | 12-point score + approval          | Approval routing     | Calibration of policy weights |
| M11    | Z.A.R.V.I.S. Operator   | Live system twin/control room      | Operator awareness   | Attention prioritization      |

# 8. Delivery Phases

## Phase 0 — Rebrand and Engineering Baseline (COMPLETE)

Deliverables:

- Canonical Zeto branding.
- `AGENTS.md`, `ARCHITECTURE.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, ADR directory.
- Complete `.env.example` contract.
- ESLint/format/build validation.
- Real test runner and test structure.
- GitHub Actions for lint, tests, dependency audit, secret scanning and container build.
- Runtime policy pinned to supported Node release.
- `/health` and `/ready` endpoints.

Exit criteria:

- Fresh checkout installs cleanly.
- Lint/tests/build/container checks pass.
- No committed secrets.
- Runtime and UI consistently use Zeto identity.

## Phase 1 — Persistence, API Boundary and Workflow Foundation (COMPLETE)

Deliverables:

- PostgreSQL adapter and migrations.
- Repository/data-access layer separated from HTTP handlers.
- `/v1` API namespace.
- Request validation and typed schemas.
- Durable queue abstraction.
- Workflow and approval state machines.
- Audit-event writer.
- Idempotency-key support for mutations.
- Correlation/request IDs.
- Object-storage abstraction.
- Outbox/event pattern for reliable side effects.

Minimum persistence rules:

- Foreign keys, timestamps, unique constraints and indexes.
- Explicit retention/archival strategy.
- Forward-safe migrations.
- Backup and restore proof.

Exit criteria:

- Business logic no longer depends directly on JSON files.
- Queue/schedule/publication state survives restarts.
- Duplicate publish commands cannot create duplicate publications.
- Every mutation emits auditable evidence.

## Phase 2 — ProMeta Prompt Compiler + M01-M05 Generation Plane

Compiler inputs:

```text
brand
niche
voice
colors
fonts
platforms
goals
timezone
budget_per_asset
stack
image_model
video_model
audio_model
```

Compiler requirements:

- Resolve placeholders before execution.
- Preserve P-MASTER/ProMeta structure.
- Produce typed machine-readable output.
- Preserve approval gates unless explicitly policy-approved.
- Append brand-kit policy to generation requests.
- Record prompt hash, compiler version, model route and cost estimate.

M01 Strategy & Deep Research:

- 90-day strategy.
- Content pillars.
- Persona/pain mapping.
- Idea scoring.
- Hook bank.
- Daily/weekly optimization routines.
- **Deep Research Engine**: Iterative multi-hop search, citation cross-referencing, document verification, and synthesis pipeline.
- **Multimodal Super Agent Office Suite**: Automated compilation of research into structured Markdown whitepapers, Slide deck schemas, Excel/CSV analytical sheets, and podcast scripts.
- **SkyClaw Cross-Model Memory Migration**: Import/export protocol for migrating memories across Luna/Terra/Sol tiers and external LLMs.

M02 Image:

- Prompt/negative prompt.
- Aspect-ratio policy.
- Variant seeds.
- Prompt hash/palette provenance.
- Brand-delta validation.

M03 Video:

- Reel/avatar/B-roll templates.
- Timecoded shot lists.
- Captions/CTA requirements.
- Provider-independent render jobs.

M04 Audio:

- Generated/licensed audio only.
- LUFS validation.
- Mood/BPM/use-case tags.
- License provenance.

M05 Captions:

- Per-platform rewriting.
- Hook/CTA/hashtag generation.
- Alt text/SEO description.
- Character and policy limits.

Model router:

```text
Task → Preferred Model → Fallback 1 → Fallback 2 → Failure Queue
```

Each attempt records provider, model, latency, usage, estimated cost, retry count, quality score and fallback reason.

Exit criteria:

- One idea generates a complete draft asset pack.
- Artifacts have provenance/versioning.
- Cost caps are enforced before generation.
- Provider failure uses bounded fallback without losing workflow state.

## Phase 3 — M10 QA, Brand Safety and Human Approval

12-point scorer:

1. Brand palette.
2. Font policy.
3. Logo policy.
4. Claim substantiation.
5. Platform policy.
6. Copyright/music clearance.
7. Text length.
8. Safe margins.
9. Alt text.
10. Hashtag risk.
11. Sentiment/reputation risk.
12. CTA presence.

Routing:

```text
score < 70  → BLOCK
70-89       → HUMAN REVIEW
>= 90       → AUTO-PASS only if AUTO_PILOT=true and all hard policies pass
```

Exit criteria:

- Visible score breakdown and remediation hints.
- Approval decisions are immutable audit records.
- Publishing checks approval transactionally.
- Approval bypass tests fail closed.

## Phase 4 — M06 Calendar, Scheduling and Production Publishing

Deliverables:

- Timezone-safe calendar slots.
- Publication state machine.
- Idempotent publishing.
- Exponential backoff + jitter.
- Dead-letter/failure queue.
- Manual retry/cancel.
- Persisted publication IDs/permalinks/provider metadata.
- Evergreen recycling rules.
- Best-time recommendations based on historical metrics.

Facebook adapter hardening:

- `PublishingProvider` interface.
- Permission/token validation.
- Normalized provider errors.
- Rate-limit awareness.
- Token-expiry diagnostics.
- Provider fake tests for publish/delete/read/status.

Exit criteria:

- Restart cannot duplicate publication.
- Failed jobs are inspectable/retryable.
- Every attempt has audit/provider evidence.

## Phase 5 — M07 Monitoring, Sentiment and Competitor Intelligence

Deliverables:

- Mention ingestion adapters.
- Classification: `question|complaint|praise|spam|lead`.
- Normalized sentiment 0-100.
- Alert rules and deduplication.
- Reply-draft generation.
- Escalation workflow + SLA timers.
- Lead handoff interface.
- Competitor metrics model.

Default alerts:

- Volume spike.
- Sentiment deterioration.
- Viral negative content.
- Competitor pricing mention.
- Creator/influencer mention.
- Overdue critical reply.

Exit criteria:

- Alerts deduplicate deterministically.
- Every complaint has draft response or escalation.
- Precision/recall can be measured.

## Phase 6 — M08 Analytics and Control Room

Dashboard areas:

- Followers/reach/engagement deltas.
- Best publishing times.
- Idea → Generating → Review → Scheduled → Live kanban.
- Mention feed with sentiment.
- 30-day trends.
- Platform performance.
- Production queue.
- Alerts/approvals.
- Cost per asset.
- Model latency/failure rate.

Every chart defines query source, period, prior-period comparison, empty state and mobile behavior.

Exit criteria:

- KPIs are reproducible from persisted data.
- No fabricated values.
- Daily and weekly reports use the same source metrics.

## Phase 6A / M11 — Z.A.R.V.I.S. Neural Operator View

**Z.A.R.V.I.S.** = **Zeto Autonomous Runtime Virtual Intelligence System** — the live system twin / operator control surface for Zeto.

> **M12 — Z.A.R.V.I.S. Operator Runtime** (the agent/voice/computer-use runtime, distinct from this M11 operator view) is specified in `docs/JARVIS-VIDEO-REVERSE-ENGINEERING.md`, which is the source of truth for its state-transition table, contracts, schemas, event catalog, persistence model, SLOs and acceptance matrix.

### Visual source and intent

The supplied screenshot shows a dark operator workstation with a large display presenting a side-profile Z.A.R.V.I.S. head rendered as thousands of cyan/gold particles, with a bright energy/core point and dense control surfaces around it. Zeto will implement this as a **live system twin**, not a cosmetic animation.

### Current implementation slice

- [x] Standalone `/zarvis` operator surface.
- [x] Canvas point-cloud zarvis visualization without external 3D dependency.
- [x] Live backend-derived queue/approval/schedule/history telemetry.
- [x] Authenticated `/v1/zarvis/state` endpoint.
- [x] Module/agent matrix for M01-M10/M11 operational state.
- [x] Runtime Node/uptime/scheduler visibility.
- [x] Unit test for operator-state derivation.

### Full-stack target

Frontend:

- WebGL/Canvas renderer supporting desktop/tablet/mobile.
- Side-profile point cloud, neural core, orbital/voice-wave effects and scan telemetry.
- 30/60 FPS adaptive rendering with reduced-motion fallback.
- Keyboard navigation and screen-reader state summary.
- Agent/workflow topology view.
- Drill-down from head regions/nodes into workflow, provider, queue, approval and incident panels.
- Operator command palette.
- Incident mode that visually distinguishes degraded modules without relying on color alone.
- Historical playback of operator snapshots.

Backend:

- `/v1/zarvis/state` — current system twin snapshot.
- `/v1/zarvis/timeline` — historical snapshots.
- `/v1/zarvis/modules/:id` — module detail and health evidence.
- `/v1/zarvis/commands` — admin-only allowlisted operator commands.
- Server-Sent Events or WebSocket transport for live events after durable event foundation exists.
- State sourced from PostgreSQL/workflows/metrics/alerts/providers, never random dashboard data.
- Snapshot provenance, sequence numbers and correlation IDs.

Operator commands must be allowlisted and RBAC-protected, including:

- Pause/resume AUTO-PILOT.
- Pause/resume scheduler.
- Retry/cancel a selected failed job.
- Open approval item.
- Trigger health diagnostics.
- Activate emergency publishing kill switch.

No arbitrary shell execution is exposed through the UI.

Z.A.R.V.I.S. semantics:

- `confidence` = derived operational confidence, with documented formula/version.
- `neural_load` = normalized queue/worker/provider pressure.
- `focus` = highest-priority current operator concern.
- `alert_level` = deterministic rules from incidents/approvals/failures/SLOs.
- Head/particle animation reacts to real state but does not redefine the state.

Video reconciliation pass, once the source video is uploaded:

- Extract key frames and interaction timeline.
- Inventory every visible panel/control/transition.
- Reproduce interaction hierarchy without copying protected branding/assets.
- Map each interaction to a real Zeto API/domain capability.
- Add missing animation states, gestures and transitions.
- Add visual-regression tests for representative viewport states.

Exit criteria:

- Operator view remains useful with animation disabled.
- Every displayed operational metric has a source and timestamp.
- Stale/disconnected states are visibly indicated.
- Viewer cannot invoke mutations.
- Admin commands are audited/idempotent where applicable.
- 1-hour soak test has no unbounded memory growth.
- Rendering meets performance budget on supported targets.

## Phase 6B / M12 — Z.A.R.V.I.S. Operator Runtime

**Source of truth:** `docs/JARVIS-VIDEO-REVERSE-ENGINEERING.md` — the master reverse-engineering and implementation specification for the M12 runtime. This phase implements the runtime on top of the M11 operator view (`Phase 6A`).

**Z.A.R.V.I.S.** = **Zeto Autonomous Runtime Virtual Intelligence System** — the agent/voice/computer-use operator runtime, distinct from the M11 operator view.

### Scope

- Session/event loop with canonical event catalog (spec §10).
- Operator state machine with guarded transitions — `IDLE → LISTENING → TRANSCRIBING → THINKING → PLANNING → AWAITING_APPROVAL → EXECUTING → VERIFYING → SPEAKING → IDLE`, with `RECOVERING`/`REAUTHORIZING` for recovery, `PAUSED` for resumable interruption (pause legal only from `PAUSABLE_STATES` — `AWAITING_APPROVAL / EXECUTING / VERIFYING / DEGRADED` ∪ `RECOVERY_STATES`; voice/planner pause defers or cancels to IDLE), `PAUSED → CANCELLED` for ordinary cancel, and terminal `FAILED / CANCELLED / EMERGENCY_STOPPED` (terminal states have no outbound transitions; emergency stop is immediate and never shares pause semantics) — including timeout, retry, cancellation, checkpoint (`previous_state`/`resume_state`) and recovery semantics (spec §3.3).
- Intent router, planner, skill/agent registries, tool gateway, executor, observer/verifier (spec §6).
- Voice plane: push-to-talk/VAD, streaming STT/TTS, barge-in, latency budgets and fallback matrix (spec §5).
- Computer-use adapters (Browser/Desktop/File/Shell/Application) behind typed contracts with observe→decide→act→verify loops (spec §7).
- Command Stream, Sequence Builder, approval drawer, mobile pairing, onboarding (spec §2, §4).
- Audit, memory boundaries, persistence model, observability/SLOs and recovery/checkpoint model (spec §8, §11–§13).

### Current implementation slice

- [x] M12 contracts + operator state machine + event stream (spec §3.3, §9, §10).
- [x] Command Stream and orb wired to real events (spec §2.2 S1, §2.3, §2.4, §4.2): `/zarvis` command center opens/resumes an operator session over SSE (`Last-Event-ID` resume persisted), renders the command stream from real catalog events with empty/error states, submits text commands to the runtime, and drives the orb presentation from canonical session state with reduced-motion fallbacks. Stream-entry and orb-presentation mapping is a shared, unit-tested module (`public/js/operatorStream.js`); `GET /v1/operator/sessions/:id` restores the session snapshot on reload.
- [x] Sequence Builder persistence and execution (spec §4.3, §9, §11): durable sequence definitions with ordered steps (`operator_sequences`/`operator_sequence_steps`), `GET/POST/PUT/DELETE /v1/operator/sequences` + `GET /v1/operator/sequences/:id`, sequential execution with `s<N>.result` arg resolution, per-run idempotent step execution (`operator_sequence_runs`/`operator_sequence_run_steps`, UNIQUE `(run_id, step_key)`), dry-run, partial-failure stop with resume (`POST /v1/operator/sequences/:id/run`, resume reuses the same run and skips succeeded steps), operator confirmation gate for high-risk replay, canonical event emission (`input.received` type sequence + `step.started/finished/failed`), built-in read-only intents grounded in persisted state (`queue.read`, `session.status`, `events.recent`) with loud unsupported-intent failures, and `GET /v1/operator/sequence-runs/:id` for resume UI.
- [ ] Skill/tool registries and policy gateway.
- [ ] OpenRouter Advisor & Subagent Delegation:
  - Token-efficient Advisor server tool invocation for high-uncertainty brand QA and factual review;
  - Subagent server tool for parallel research and media generation task delegation;
  - Automatic Doom-Loop detection to terminate unproductive copy generation cycles;
  - Dynamic prompt cache block optimization (`cache_control`) across large brand voice guidelines.
- [ ] Browser automation adapter + verifier.
- [ ] Desktop/application adapters + verifier.
- [ ] Voice STT/TTS + push-to-talk + barge-in.
- [ ] Mobile pairing.
- [ ] Advanced autonomous mode with bounded budgets and approvals.
- [ ] Full security/E2E/soak/recovery evidence.

### Non-negotiable invariants (spec §8)

- Deny-by-default tool permissions; approval required for destructive, external side-effect, credential, financial, publication and privilege-changing actions.
- Observed browser/screen content is **untrusted data** — it can never grant tools or change policy (prompt-injection defense).
- Every action carries provenance: `session_id`, `plan_id`, `step_id`, `risk`, `approval`, `idempotency_key` and verification evidence.
- Secrets redacted in UI, logs, screenshots and model context; emergency stop revokes ephemeral grants.
- No raw audio persistence by default; retention requires explicit policy.

### Exit criteria (mapped to spec §14.1 acceptance matrix)

- All state-machine transitions in spec §3.3 covered by tests; timeout/retry/cancellation/recovery paths green.
- Permission-bypass and prompt-injection suites green; approval matrix enforced.
- Voice latency SLOs met in staging; fallback matrix exercised.
- E2E: voice/text command → plan → approval → tool execution → verification → spoken/UI result passes in staging.
- Crash mid-plan resumes without duplicate side effects (idempotency proven).
- 12-hour soak: zero unrecoverable failures and no unbounded memory growth.
- Audit completeness and QR-token expiry/replay tests green.

## Phase 7 — M09 Orchestration and AUTO-PILOT

Canonical chain:

```text
M01[OPS]
  → M02-M05[PRODUCTION]
  → M10[QA]
  → approval gate
  → M06[PUBLISH]
  → M07[MONITOR]
  → M08[REPORT]
  → M01-M05[OPTIMIZE]
```

Requirements:

- Durable workflow run IDs.
- Step ownership/status.
- Retry/compensation.
- Cancellation/timeouts.
- Idempotent side effects.
- Typed artifact passing.
- Stuck-job detection.
- Per-run cost accounting.
- Human intervention checkpoints.

AUTO-PILOT always obeys QA threshold, platform permission, budget, frequency cap, claims/copyright policy, emergency kill switch and audit logging.

Exit criteria:

- End-to-end workflow requires no manual data copying.
- Failed steps resume without replaying completed side effects.
- Operator can stop autonomous publishing immediately.

## Phase 8 — Multi-Platform Publishing

Adapter sequence:

1. Instagram.
2. YouTube.
3. TikTok.
4. X.
5. LinkedIn.

Shared adapter contract:

- Auth validation.
- Capability discovery.
- Publish/media upload.
- Delete where supported.
- Publication status.
- Metrics ingestion.
- Normalized errors.
- Rate-limit metadata.

Exit criteria:

- Core workflows contain no platform-specific branching beyond capability checks.
- Platform validation occurs before queue acceptance.

## Phase 9 — Enterprise Production Hardening

Reliability:

- Health/readiness/startup endpoints.
- Graceful shutdown.
- Worker heartbeats.
- DB pool limits.
- Request/job timeouts.
- Bounded exponential retry.
- DLQ.
- Disaster recovery.
- Backup/restore verification.
- SLO/SLA definitions and error budgets.

Security:

- Secret manager integration.
- Least-privilege provider credentials.
- Encryption in transit/at rest.
- Session/CSRF policy.
- Input validation/output encoding.
- Upload MIME/size/content validation.
- SSRF protection.
- Rate limiting.
- Dependency/container/code scanning.
- Security audit trail.
- Threat model and abuse-case tests.

Observability:

- Structured JSON logs.
- HTTP/job/provider/publishing/cost/approval metrics.
- Distributed traces for workflow runs.
- Alerts on availability, error rate, stuck jobs, queue depth, DB saturation and provider degradation.

Performance:

- Load baseline for API and workers.
- Queue throughput benchmark.
- Publish/generation latency objectives.
- Browser performance budget.
- Z.A.R.V.I.S. view memory/FPS budget.

## 9. Continuous 30-Minute Engineering Verification Loop

Zeto uses a repository-owned GitHub Actions schedule every 30 minutes for **verification and maintenance evidence**.

The loop must:

1. Checkout the latest target branch.
2. Install dependencies reproducibly.
3. Run lint.
4. Run full unit/integration tests available in the repository.
5. Run build/syntax validation.
6. Run high-severity dependency audit.
7. Build the container.
8. Inspect outdated dependencies without automatically accepting breaking upgrades.
9. Publish an evidence artifact/report for the run.
10. Fail loudly when any gate regresses.

Important engineering rule:

- The 30-minute workflow may verify, inspect, report and prepare safe maintenance metadata.
- It must **not** blindly rewrite application code, auto-merge arbitrary AI changes, rotate secrets, modify production credentials or promote releases without evidence gates.
- Automated implementation agents, when added, work on isolated branches/PRs and must pass the same suite before merge.

This design preserves the user's requested continuous update/upgrade/review cadence without converting production into an uncontrolled self-modifying system.

## 10. Upgrade / Update / Implementation Loop

For every vertical slice:

```text
AUDIT
→ PLAN
→ IMPLEMENT
→ SELF-REVIEW
→ LINT
→ UNIT TEST
→ INTEGRATION TEST
→ API CONTRACT TEST
→ SECURITY TEST
→ CONTAINER TEST
→ PERFORMANCE CHECK (when relevant)
→ REVIEW DIFF
→ PR
→ CI
→ REPAIR FAILURES
→ MERGE WHEN GREEN
→ NEXT SLICE
```

Upgrade policy:

- Patch/minor dependencies may be proposed automatically after compatibility checks.
- Major upgrades require migration review.
- Never bypass failing tests to obtain a green build.
- Never suppress security findings without documented risk acceptance.
- Every release change has rollback notes.

## 11. Full Test Suite Target

Mandatory categories by final release:

- Unit tests.
- Repository/database tests.
- Migration tests.
- API integration tests.
- API schema/contract tests.
- Auth/RBAC tests.
- Idempotency tests.
- Workflow state-machine tests.
- Approval bypass/negative tests.
- Provider fake/timeout/rate-limit tests.
- Publishing duplicate prevention tests.
- Object-storage tests.
- Event/outbox tests.
- Security tests including SSRF/upload/rate-limit/secret leakage.
- Browser/UI smoke tests.
- Z.A.R.V.I.S. view state/render smoke tests.
- End-to-end factory workflow tests.
- Backup/restore test.
- Rollback test.
- Load/performance baseline.
- Soak tests for workers and operator UI.

## 12. Release Evidence Matrix

A release candidate must attach evidence for:

| Gate              | Required evidence                                   |
| ----------------- | --------------------------------------------------- |
| Correctness       | CI unit/integration/E2E results                     |
| Database          | Migration + backup/restore proof                    |
| Publishing safety | Idempotency/duplicate tests                         |
| Approval safety   | Bypass-negative tests                               |
| Provider safety   | Secret leakage + fallback tests                     |
| Security          | Code/dependency/container scans                     |
| Reliability       | Retry/DLQ/restart/soak evidence                     |
| Performance       | API/worker/browser baseline                         |
| Observability     | Logs/metrics/traces visible in staging              |
| Operations        | Runbook/incident/rollback docs                      |
| UX                | Responsive/accessibility/visual regression evidence |

## 13. Final Release Exit Criteria

`ProMeta Master Professional Enterprise Final Release` may be declared complete only when:

- Zero known critical/high security defects.
- Protected `main` is green.
- PostgreSQL is the production source of truth.
- M01-M11 applicable capabilities are implemented and tested.
- Database migrations are forward-safe with documented rollback strategy.
- Publishing duplication tests pass.
- Approval bypass tests pass.
- Provider-secret leakage tests pass.
- Full end-to-end factory workflow passes in staging.
- AUTO-PILOT kill switch is proven.
- Z.A.R.V.I.S. operator view reflects real system state and degrades safely when disconnected.
- Multi-platform adapters meet the shared contract for enabled release platforms.
- Observability/SLO alerts are operational.
- Backup restore and incident exercises have passed.
- Release artifacts are reproducible and signed/traceable as configured.
- Operational runbook, incident procedures and release rollback instructions exist.

Until all applicable evidence is present, status remains **in progress**, even if feature development is functionally broad.
