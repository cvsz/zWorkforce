# Z.A.R.V.I.S. Feature Execution Plan

**Updated:** 2026-08-15  
**Branch:** `feat/zarvis-openjarvis-upgrade-plan`  
**Scope:** OpenJarvis-inspired refactor, dashboard Z.A.R.V.I.S. CARD, push-to-talk, skills and agent execution modes.

> `exec-planning-zwf.md` remains the canonical v3.0.3 production-readiness plan. This intentionally user-requested `exec-planning-zarvis.md` is the feature delivery plan for the next Z.A.R.V.I.S. upgrade line.

## 1. Delivery strategy

Implement vertical slices. Do not replace the existing ZVoice/voice-gateway/voice-agent/orchestrator stack. Reuse its protocol and security model, then expose a second browser client inside the zWorkforce dashboard.

OpenJarvis is used as an architectural reference for registries, config-driven composition, skills and scheduled/continuous agents. Existing zWorkforce tenant, approval, audit, idempotency and server-secret controls remain authoritative.

## 2. File-by-file upgrade list

### P0 — Architecture, contracts and governance

| File | Action | Result |
|---|---|---|
| `ROADMAPS.md` | **ADD** | Forward Z.A.R.V.I.S. feature roadmap. |
| `exec-planning-zarvis.md` | **ADD** | This executable feature plan. |
| `packages/zarvis/docs/architecture/openjarvis-upgrade-map.md` | **ADD** | Verified source-to-target architecture mapping and licensing notes. |
| `packages/zarvis/docs/architecture/skills-agents.md` | **ADD** | Canonical Z.A.R.V.I.S. skill/agent model and feature matrix. |
| `packages/zarvis/AGENTS.md` | **UPDATE** | Require the new architecture docs for voice/runtime changes. |
| `packages/zarvis/docs/requirements/master-requirements.md` | **UPDATE** | Add PTT, shared voice client, speech-provider, skill/agent-mode requirements. |

### P1 — Dashboard Z.A.R.V.I.S. CARD

| File | Action | Implementation |
|---|---|---|
| `zworkforce/static/index.html` | **UPDATE** | Add Z.A.R.V.I.S. CARD: animated orb, PTT control, state label, transcript/reply, runtime status and approval indicator. |
| `zworkforce/static/styles.css` | **UPDATE** | Orb layers, waveform, listening/thinking/speaking states, focus states, responsive design and `prefers-reduced-motion`. |
| `zworkforce/static/app.js` | **UPDATE** | Dashboard voice controller, PTT pointer/keyboard lifecycle, interruption, transcript rendering and session cleanup. |
| `zworkforce/zarvis_voice.py` | **ADD** | Browser-facing BFF/service boundary for voice session bootstrap and Z.A.R.V.I.S. command dispatch without exposing upstream secrets. |
| `zworkforce/api.py` | **UPDATE** | Register authenticated/tenant-scoped Z.A.R.V.I.S. voice endpoints and health snapshot. |
| `zworkforce/config.py` | **UPDATE** | Add validated voice gateway/orchestrator configuration and feature flags; no client-secret serialization. |
| `.env.example` | **UPDATE** | Document non-secret endpoint/feature settings and secret names without values. |
| `tests/test_static_assets.py` | **UPDATE** | Assert card/assets/accessibility hooks exist and no credential names/values leak. |
| `tests/test_zarvis_voice_api.py` | **ADD** | Auth, tenant, timeout, upstream error, secret isolation and command/session tests. |

**PTT semantics**

- Pointer/touch: press = start capture; release/cancel = commit/end turn.
- Keyboard: hold `Space` outside form controls; key repeat ignored; release commits turn.
- Accessible fallback: click toggles recording for switch/keyboard users.
- New speech while playback is active triggers barge-in and cancels queued output.
- `Escape` cancels current assistant playback/response but never approves a mutation.

### P2 — Shared realtime browser voice client

Current ZVoice already has the more capable implementation. Extract rather than duplicate.

| File | Action | Implementation |
|---|---|---|
| `packages/zarvis/packages/voice-client/package.json` | **ADD** | Browser-safe package metadata. |
| `packages/zarvis/packages/voice-client/src/client.js` | **ADD** | WebSocket/session event state machine. |
| `packages/zarvis/packages/voice-client/src/audio.js` | **ADD** | PCM16/resampling/playback helpers. |
| `packages/zarvis/packages/voice-client/src/ptt.js` | **ADD** | Pointer/keyboard PTT controller independent of presentation. |
| `packages/zarvis/packages/voice-client/src/state.js` | **ADD** | Canonical conversation state reducer. |
| `packages/zarvis/packages/voice-client/test/*` | **ADD** | Session, PTT, reconnect, cancel and audio lifecycle tests. |
| `packages/zarvis/apps/zvoice/public/app.js` | **REFACTOR** | Consume shared client while preserving current ZVoice behavior. |
| `packages/zarvis/apps/zvoice/public/voice-worklet.js` | **MOVE/SHARE carefully** | Keep AudioWorklet module reusable without bundling credentials/config. |
| `zworkforce/static/app.js` | **REFACTOR** | Consume the same browser-safe behavior or generated distribution asset. |

No iframe integration: `apps/zvoice` correctly denies framing.

### P3 — Speech provider registry

| Target | Action |
|---|---|
| `packages/zarvis/services/voice-agent/` | Introduce explicit STT/TTS backend protocols and registry/discovery. |
| `packages/zarvis/services/voice-agent/speech/registry.py` | **ADD** typed registry with duplicate protection. |
| `packages/zarvis/services/voice-agent/speech/stt.py` | **ADD** STT protocol/result/capability model. |
| `packages/zarvis/services/voice-agent/speech/tts.py` | **ADD** TTS protocol/result/capability model. |
| `packages/zarvis/services/voice-agent/speech/providers/` | **ADD/REFACTOR** local and optional provider adapters. |
| `packages/zarvis/services/voice-agent/healthcheck.py` | **UPDATE** report selected backend and health without secrets. |
| `packages/zarvis/docs/architecture/voice-agent.md` | **UPDATE** provider-selection and fallback policy. |
| `packages/zarvis/docs/operations/voice-agent.md` | **UPDATE** configuration, health, rollback and troubleshooting. |

Requirements:

- explicit provider selection must not silently fall back when a workload pins one backend;
- local/cloud classification is first-class;
- server-side-only credentials;
- per-provider timeout, health and capability metadata;
- deterministic tests using fakes.

### P4 — Runtime skills

Repository coding skills in `.agents/skills` and runtime assistant skills are different concepts and must stay distinct.

| File/area | Action |
|---|---|
| `packages/zarvis/packages/contracts/` | Add/version skill manifest and invocation/result schemas if not already present. |
| `packages/zarvis/services/zarvis-orchestrator/` | Add skill catalog discovery, validation and policy-mediated invocation. |
| `packages/zarvis/skills/` | Add runtime skill manifests grouped by domain. |
| `packages/zarvis/skills/conversation/` | Spoken conversation shaping, summarization and response formatting. |
| `packages/zarvis/skills/memory/` | Authorized recall/write/delete workflows. |
| `packages/zarvis/skills/research/` | Bounded research workflow with provenance. |
| `packages/zarvis/skills/code/` | Code exploration/review/repair orchestration using existing specialist agents. |
| `packages/zarvis/skills/operations/` | Health/status/incident workflows; mutating steps approval-gated. |
| `packages/zarvis/skills/productivity/` | Scheduled briefing/task coordination where connectors are configured. |
| `packages/zarvis/skills/*/test*` | Manifest, dependency, policy, timeout and denial-path tests. |

### P4.1 — OpenRouter Agent SDK & Reliability Patterns

Adopt key resilience patterns from the OpenRouter Agent SDK and Cookbook:

- **Human-in-the-Loop (HITL) Tool Gates**: tools with side-effects or external mutating authority pause execution and serialize conversation/tool state until operator approval.
- **Doom-Loop Detection**: runtime monitor detects cyclical repeated tool calls, identical arguments, or stagnant text responses and terminates or escalates to fallback.
- **Dynamic Context Injection (`nextTurnParams`)**: dynamic prompt parameter and cache injection across multi-turn reasoning steps.
- **Advisor & Subagent Tools**:
  - `advisor`: consults stronger models mid-generation for compact uncertainty checks;
  - `subagent`: delegates isolated sub-tasks to faster/cheaper worker models with bounded tool envelopes.

Every runtime skill requires:

- stable ID + semantic version;
- explicit input/output schema;
- capability and tool allowlist;
- mutability classification and approval rule;
- timeout/concurrency/retry semantics;
- idempotency strategy for any durable/external effect;
- audit event mapping;
- owner and rollback/version policy.

### P5 — Agents and continuous operators (Free Model First)

Reuse the large existing specialist-agent catalog and adopt OpenCode `oh-my-opencode` specialist personas:

| File | Action | Responsibility |
|---|---|---|
| `packages/zarvis/agents/voice-orchestrator.md` | **ADD** | Low-latency spoken-turn planner/router and safe handoff. |
| `packages/zarvis/agents/operator-supervisor.md` | **ADD** | Continuous/scheduled agent health, heartbeat, rate-limit, execution ceilings (max cost/tokens/steps), and recovery policy. |
| `packages/zarvis/agents/chief-of-staff.md` | **KEEP/INTEGRATE** | High-level task decomposition and delegation. |
| `packages/zarvis/agents/brain-memory-agent.md` | **KEEP/INTEGRATE** | Memory/context specialization. |
| `packages/zarvis/agents/code-reviewer.md` | **ADD** | `oh-my-opencode` style async non-blocking PR and code review agent powered by `qwen-2.5-coder-32b:free`. |
| `packages/zarvis/agents/test-architect.md` | **ADD** | Test coverage generator and regression test planner on `deepseek-r1:free`. |
| `packages/zarvis/agents/security-auditor.md` | **ADD** | SAST vulnerability scan and credential leak defense specialist. |
| Existing code/review/build agents | **KEEP/INTEGRATE** | Specialist engineering work; no duplicate clones. |
| `packages/zarvis/services/zarvis-orchestrator/` | **UPDATE** | Agent manifest resolution, execution mode, long-horizon loop control, ACP server dispatch, pre-mutation file snapshot rollback, and handoff policy. |
| Existing scheduler/event infrastructure | **INTEGRATE** | Durable scheduled/event-driven dispatch rather than a second scheduler. |

Required modes:

- `on_demand`: user/request initiated;
- `scheduled`: cron/interval occurrence with stable idempotency key;
- `continuous`: bounded long-running operator with heartbeat/lease/rate limit.

Continuous and long-horizon modes require heartbeat, stale-run detection, max concurrency, token/cost budget enforcement, pause/resume, version pinning, failure budget and rollback. All specialist agents default to **Free Model First** routing (`openrouter/free`, `qwen-2.5-coder-32b-instruct:free`, `deepseek-r1:free`). Pre-mutation file modifications create sha256 checksummed snapshot checkpoints allowing one-click visual diff rollback.

### P6 — Repository coding-agent skills

| File | Action |
|---|---|
| `.agents/skills/zworkforce-zarvis-voice-ui/SKILL.md` | **ADD** safe implementation workflow for dashboard/ZVoice/realtime speech work. |
| `.agents/skills/zworkforce-zarvis-runtime-orchestration/SKILL.md` | **ADD** safe workflow for skills, agents, scheduler and capability-policy work. |
| `.agents/skills/zworkforce-safety-hooks/SKILL.md` | **ADD** deterministic pre/post execution safety guards (`branch-guard`, `secret-guard`, `destructive-guard`). |
| `.agents/skills/zworkforce-llm-wiki-patterns/SKILL.md` | **ADD** structured LLM wiki knowledge compounding and pre-mortem architectural review patterns. |
| Corresponding `agents/openai.yaml` files | **OPTIONAL FOLLOW-UP** if the repository requires provider-specific skill metadata. |

### P7 — Observability, tests and release

| Area | Work |
|---|---|
| Tests | microphone denial; PTT start/release; keyboard handling; ticket expiration; WS failure; reconnect; transcription; speaking; barge-in; cancellation; approval-required; provider timeout; agent heartbeat; skill denial; duplicate/idempotent execution. |
| Metrics | ticket/STT/reasoning/TTS/E2E latency; active voice sessions; PTT failures; reconnects; provider health; agent heartbeats; skill invocations; policy denials. |
| Security | CSP, framing, authn/authz, tenant isolation, SSRF, WebSocket origin/ticket, secrets, logs/traces and mutation approval. |
| Accessibility | focus states, labels, keyboard flow, live regions, reduced motion, non-color state indicators. |
| Release | package tests, Python suite, Node suite, dependency audit, SBOM/provenance, staging evidence and rollback record. |

## 3. PR sequence

### PR-1 — Architecture and agent/skill contracts

Files: `ROADMAPS.md`, `exec-planning-zarvis.md`, architecture mapping, skill/agent model, coding-agent skills, new agent definitions.  
Risk: low.  
Exit: documentation and repository policy checks green.

### PR-2 — Dashboard card vertical slice

Files: root static frontend + `zworkforce/zarvis_voice.py` + API/config + tests.  
Risk: medium.  
Exit: authenticated PTT works against existing backend; secrets absent from browser payloads.

### PR-3 — Shared voice client extraction

Files: new `packages/voice-client`, ZVoice refactor, dashboard adapter, Node tests.  
Risk: medium.  
Exit: ZVoice and dashboard pass the same protocol conformance tests.

### PR-4 — Speech registry

Files: voice-agent provider contracts/registry/adapters/health/tests/docs.  
Risk: medium-high.  
Exit: local backend behavior unchanged; alternate backend can be selected explicitly.

### PR-5 — Runtime skill catalog

Files: contracts, orchestrator skill manager, initial approved skills, tests.  
Risk: high around authorization.  
Exit: skills cannot exceed their declared capability/tool/approval envelope.

### PR-6 — Agent execution modes and operator supervision

Files: orchestrator, scheduler integration, manifests, supervisor, telemetry/tests.  
Risk: high around autonomy/durable state.  
Exit: scheduled/continuous agents are leased, rate-limited, observable, pausable and rollback-capable.

### PR-7 — Hardening and release evidence

Full suite, accessibility, latency/load, failover, recovery, staging and release docs.

## 4. Security invariants

1. Browser receives only short-lived session material intended for the browser; never provider/service/database secrets.
2. Voice capture is user-initiated and visibly active.
3. A spoken request is not itself approval for a mutating action unless the versioned approval protocol explicitly records a valid scoped approval.
4. Agent/skill invocation is deny-by-default outside declared capabilities/tools.
5. Continuous agents use bounded leases/rate limits and cannot silently broaden privileges.
6. All durable or external mutating work preserves idempotency/audit semantics.
7. Tenant/subject context is resolved server-side from authenticated identity, not trusted from arbitrary browser claims.
8. Raw sensitive audio/transcript content is excluded from telemetry by default.

## 5. Validation commands

Run narrow tests first, then repository gates:

```bash
python -m compileall -q zworkforce tests scripts
PYTHONPATH=. python -m unittest discover -s tests -v
pnpm --dir packages/zarvis install --frozen-lockfile
pnpm --dir packages/zarvis peers check
pnpm --dir packages/zarvis test
pnpm --dir packages/zarvis audit --audit-level high
python scripts/verify_release.py --expected 3.0.3
```

For production-equivalent evidence, follow `exec-planning-zwf.md`; repository CI alone does not prove external infrastructure readiness.

## 6. Definition of done

The work is complete only when Z.A.R.V.I.S. can be used from the dashboard through an accessible animated PTT card; ZVoice and dashboard share a tested realtime client; speech providers are pluggable and health-reporting; skills and on-demand/scheduled/continuous agents are versioned and capability-governed; agent supervision prevents runaway/stalled work; all mutating actions remain approval-scoped; and the full release/security suite is green.