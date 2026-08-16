# Z.A.R.V.I.S. Upgrade Roadmaps

**Status:** active forward roadmap  
**Scope:** `cvsz/zworkforce` with the consolidated Z.A.R.V.I.S. suite under `packages/zarvis`  
**Reference implementations studied:** `open-jarvis/OpenJarvis` (Apache-2.0) and publicly documented Skywork workspace-agent capabilities

> `ROADMAP.md` remains the release-history and production-readiness roadmap. This file is the forward feature roadmap for the Z.A.R.V.I.S. assistant experience, workspace-agent UX, and architecture refactors.

## 1. Baseline

zWorkforce already contains a substantial Z.A.R.V.I.S. implementation:

- `packages/zarvis/apps/zvoice` provides the realtime browser voice surface;
- `services/voice-gateway` issues short-lived WebSocket tickets;
- `services/voice-agent` owns VAD/STT/LLM/TTS processing;
- `services/zarvis-orchestrator` owns command routing and speech-ready results;
- `services/zarvis-task-gateway` and `services/zarvis-action-gateway` preserve approval boundaries;
- memory, perception, proactive services, contracts, Windows and console surfaces already exist;
- the root control-plane frontend is served from `zworkforce/static`.

The upgrade therefore **must refactor and compose existing primitives rather than add a second assistant stack**.

## 2. Architecture concepts to adopt

Adopt architectural/product ideas, not wholesale source imports:

1. **Config-driven system composition** — one builder/factory composes model, tools, skills, memory, speech, scheduling and policy.
2. **Typed registry/discovery** — pluggable STT, TTS, model, tool, skill and agent providers with explicit health/capabilities.
3. **Skills as first-class invokable capabilities** — discoverable catalog, dependency validation, policy checks, tool wrapping and trace evidence.
4. **Agent execution modes** — on-demand, scheduled and continuous operators with persistent state.
5. **Trace-driven improvement** — evaluate latency, quality, cost and energy before changing routing or skill selection.
6. **Workspace-first task continuity** — durable projects/conversations, context budget/compaction, artifacts, review state and subagent visibility.
7. **Isolated local execution** — scoped workspace roots plus bounded git branch/worktree operations rather than unrestricted host access.
8. **Governed skill lifecycle** — immediate activation inside the existing capability envelope, safe update, disable/enable and rollback.
9. **Operator-facing FinOps** — preflight budget checks and durable usage/chargeback drilldown.

Keep zWorkforce's stronger existing security boundaries: server-side secrets, tenant isolation, approval-scoped mutation, durable idempotency and audited action gateways.

Research evidence and the full Skywork-derived map are maintained in `docs/SKYWORK-CHANGELOG-REVERSE-ENGINEERING.md`. The executable cross-subsystem plan is `planning/exec-planning-skywork.md`.

## 3. Roadmap

### R0 — Architecture and compatibility contract

- [ ] Record the OpenJarvis-to-Z.A.R.V.I.S. file mapping in `packages/zarvis/docs/architecture/openjarvis-upgrade-map.md`.
- [ ] Keep Apache-2.0 attribution for any source material actually adapted.
- [ ] Define a browser-safe voice contract that contains no provider/service credentials.
- [ ] Define one canonical Z.A.R.V.I.S. conversation state machine:
  `idle -> arming -> listening -> transcribing -> thinking -> speaking -> idle`, plus `muted`, `interrupted`, `approval_required`, and `error` substates.
- [ ] Preserve existing `zarvis.command.requested.v1` and approval/action contracts unless a versioned migration is required.

### R1 — Z.A.R.V.I.S. CARD in the zWorkforce frontend

Goal: talk to Z.A.R.V.I.S. directly from the AI Workforce control plane.

- [ ] Add a dedicated `Z.A.R.V.I.S.` dashboard card in `zworkforce/static/index.html`.
- [ ] Add a GPU-friendly animated AI orb with state-driven animation in `zworkforce/static/styles.css`.
- [ ] Add push-to-talk to `zworkforce/static/app.js`:
  - pointer/touch press-and-hold;
  - `Space` press-and-hold when focus is not in an editable control;
  - explicit microphone permission state;
  - keyboard-accessible toggle fallback;
  - barge-in/cancel while Z.A.R.V.I.S. is speaking.
- [ ] Show live state, partial/final transcript, last reply, runtime/model label, microphone state and approval-required state.
- [ ] Reuse/extract the existing ZVoice PCM16/AudioWorklet realtime client instead of embedding ZVoice in an iframe.
- [ ] Keep credentials server-side through a zWorkforce BFF/session endpoint.
- [ ] Respect `prefers-reduced-motion` and provide a non-animated accessible state representation.

**R1 acceptance:** an authenticated control-plane user can hold PTT, speak, see the orb move through listening/thinking/speaking states, hear the answer, interrupt playback, and never receive an upstream credential.

### R2 — Shared browser voice client

- [ ] Extract browser-safe capture/session/event logic from `apps/zvoice/public/app.js` into a shared Z.A.R.V.I.S. voice-client package.
- [ ] Keep AudioWorklet PCM16 capture at 16 kHz and realtime interruption semantics.
- [ ] Make ZVoice and the dashboard card consume the same client contract.
- [ ] Add contract tests for session lifecycle, interruption, reconnect, ticket expiry and microphone denial.
- [ ] Ensure the shared library cannot accept or serialize service/provider secrets.

### R3 — Speech provider registry

Refactor the voice runtime toward a typed registry while keeping the current service boundary.

- [ ] Define STT provider interface: `transcribe/stream`, languages, sample-rate support, health and local/cloud classification.
- [ ] Define TTS provider interface: `synthesize/stream`, voices, sample rates, health and local/cloud classification.
- [ ] Register existing local speech implementation first.
- [ ] Add optional adapters for Faster Whisper / Whisper-compatible STT and local TTS implementations already supported by deployment profiles.
- [ ] Permit hosted providers only through server-side configuration and policy.
- [ ] Surface provider health/capabilities to operators without exposing secrets.

### R4 — Z.A.R.V.I.S. skills runtime

- [ ] Maintain a runtime skill manifest/catalog distinct from repository coding-agent skills under `.agents/skills`.
- [ ] Each runtime skill declares: ID/version, description, required capabilities, allowed tools, mutability, approval policy, timeout, retry/idempotency behavior and input/output schema.
- [ ] Discover skills deterministically with first-class validation and duplicate rejection.
- [ ] Wrap skills behind the same policy/tool-execution boundary as normal tools.
- [ ] Add skill dependency validation and bounded nested invocation.
- [x] Add active-version resolution, enable/disable, safe system-skill auto-update and explicit rollback foundation.
- [x] Reject automatic updates that silently add tool capabilities, escalate read→write mutability or weaken approval requirements.
- [ ] Record trace evidence per skill and persist lifecycle state through the durable repository.
- [ ] Integrate signed remote marketplace packages through the existing skill-registry trust boundary.
- [ ] Never auto-promote trace-mined/repeated-workflow skills into production; generated candidates require review and tests.

### R5 — Agent manager and execution modes

- [ ] Normalize Z.A.R.V.I.S. agent manifests around three modes: `on_demand`, `scheduled`, `continuous`.
- [ ] Add `voice-orchestrator` for low-latency spoken-turn routing.
- [ ] Add `operator-supervisor` for heartbeat, stalled-run detection, rate limits and safe recovery.
- [ ] Reuse existing specialist agents such as chief-of-staff, memory, code and review agents rather than cloning them.
- [ ] Persist agent state/version, enforce capability policy, rate limits and max-concurrency.
- [ ] Add event-driven triggers using existing durable scheduler/event infrastructure.
- [ ] Add versioned rollout/rollback and failure budgets for continuous agents.

### R6 — Memory, context and conversation continuity

- [ ] Bind voice sessions to tenant/subject-scoped conversation state.
- [ ] Add durable project/conversation IDs, search, pin/archive and history navigation.
- [ ] Expose context-budget state per conversation/model.
- [ ] Implement explicit compaction that creates a versioned summary artifact instead of silently rewriting history.
- [ ] Retrieve only authorized memory and redact sensitive content before model/tool boundaries.
- [ ] Separate ephemeral transcript context from durable memory writes.
- [ ] Require explicit retention/consent policy for durable voice-derived memory.
- [ ] Provide “forget this conversation” / deletion flows with auditable completion.

### R7 — Proactive Z.A.R.V.I.S.

- [ ] Enable scheduled/continuous agents only with explicit subscriptions.
- [ ] Add quiet hours, notification policy, rate limits and deduplication.
- [ ] Add tenant-scoped notification center for completion, approval, questions, failures, budget risk and stalled agents.
- [ ] Add health/heartbeat telemetry and stalled-operator detection.
- [ ] Route requests needing human authorization into the existing approval system rather than executing mutation autonomously.

### R8 — Intelligent local/cloud routing

- [ ] Add query complexity classification and explicit local-first routing policy.
- [ ] Add redaction-before-cloud and taint-aware policy checks.
- [ ] Track latency, cost, quality and energy per route.
- [ ] Support operator-configured failover without silent provider substitution for pinned workloads.
- [ ] Keep cloud transmission disabled for protected data unless policy explicitly permits it.

### R9 — Observability and SLO hardening

- [ ] Voice session setup, STT, reasoning, TTS and end-to-end latency histograms.
- [ ] PTT start failures, microphone denial, ticket rejection, reconnects and interruption counters.
- [ ] Agent/skill invocation traces with redacted parameters and correlation IDs.
- [ ] Continuous-agent heartbeat, stale-run and rate-limit metrics.
- [ ] Dashboard health view for the complete speech/agent pipeline.

Target interactive SLOs remain engineering targets until measured in staging:

- session ticket p95 < 100 ms on local network;
- end-of-turn detection ~300–600 ms;
- first partial transcript < 700 ms where supported;
- first synthesized audio < 1.5 s on suitable hardware.

### R10 — Production release gate

- [ ] Full Python, Node, voice, contract, static asset and Windows tests green.
- [ ] Security review of microphone, WebSocket, auth, CSP, secrets and approval boundaries.
- [ ] Dependency/SBOM/provenance gates green.
- [ ] Staging voice latency, failure recovery and provider failover evidence recorded.
- [ ] Accessibility verification for keyboard, screen reader and reduced-motion modes.
- [ ] Rollback target and feature flags documented.

### R11 — Workspace Agent UX and local execution

This roadmap line translates the strongest **verified** public Skywork workspace-agent patterns into zWorkforce-native capabilities. Full sequencing and acceptance criteria are in `planning/exec-planning-skywork.md`.

- [ ] Durable projects, conversations, search, pin/archive, auto naming and stable conversation IDs.
- [ ] Context gauge, explicit `/compact`, question anchors and context snapshot history.
- [ ] Slash command registry: `/plan`, `/review`, `/compact`, `/goal`, `/status`, `/artifacts`, `/cost`, `/skill`, `/workflow`, `/feedback`.
- [ ] Task summary sidecar with artifact manifest, review state, tool timeline and sanitized subagent hierarchy.
- [ ] Operator-granted local workspace roots with path/symlink escape protection and bounded subprocesses.
- [ ] Git branch/worktree adapter for isolated coding tasks; protected/default branches never mutated directly.
- [ ] Zider browser-use tool classes with read-only default and approval-gated side effects.
- [ ] Signed skill marketplace install, discovery scoring and repeated-workflow → draft skill/workflow candidate compiler.
- [ ] Safe HTML preview and artifact history resilient across restarts.
- [ ] Task quick-start templates and evidence-based next-step suggestions.
- [ ] Theme profiles across web/WinUI without weakening accessibility/high-contrast support.
- [ ] FinOps preflight before expensive runs plus project/task/agent/model usage drilldown.

### R12 — Skywork Web capability mappings

- [ ] Zeto social publishing UX on top of the existing approval/provider/outbox pipeline.
- [ ] Versioned tenant design-guideline artifacts bound to brand/project policy and QA evidence.
- [ ] Portable AI-memory import with preview, provenance, dedupe, explicit commit and batch rollback/delete; imported instructions remain untrusted data.

## 4. Non-goals

- Do not embed `apps/zvoice` with an iframe; its defensive framing policy is intentional.
- Do not send provider or service credentials to the dashboard.
- Do not replace durable zWorkforce scheduler/approval/audit systems with a parallel runtime.
- Do not claim a provider, model or external service is production-ready until operator evidence exists.
- Do not grant continuous agents unrestricted shell/network/action access.
- Do not grant a newly installed or auto-updated skill capabilities outside its existing authorized envelope.
- Do not treat local workspace access as permission to read or write arbitrary host filesystem paths.
- Do not promote a feature into the roadmap merely because it appeared in an unverified/non-official changelog result.

## 5. Completion definition

The combined Z.A.R.V.I.S./workspace-agent upgrade is feature-complete when the dashboard and ZVoice share one tested realtime voice contract; speech providers are pluggable; skills and agent modes are policy-governed and rollback-capable; scheduled/continuous operation has health and recovery controls; projects/conversations/context/artifacts are durable and tenant scoped; local/browser execution is sandboxed and approval-safe; FinOps is visible before and after execution; and all mutation continues through explicit zWorkforce approval/action boundaries.