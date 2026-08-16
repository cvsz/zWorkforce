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

- [x] Record the OpenJarvis-to-Z.A.R.V.I.S. file mapping in `packages/zarvis/docs/architecture/openjarvis-upgrade-map.md`.
- [x] Keep Apache-2.0 attribution for any source material actually adapted.
- [x] Define a browser-safe voice contract that contains no provider/service credentials.
- [x] Define one canonical Z.A.R.V.I.S. conversation state machine:
  `idle -> arming -> listening -> transcribing -> thinking -> speaking -> idle`, plus `muted`, `interrupted`, `approval_required`, and `error` substates.
- [x] Preserve existing `zarvis.command.requested.v1` and approval/action contracts unless a versioned migration is required.

### R1 — Z.A.R.V.I.S. CARD in the zWorkforce frontend

Goal: talk to Z.A.R.V.I.S. directly from the AI Workforce control plane.

- [x] Add a dedicated `Z.A.R.V.I.S.` dashboard card in `zworkforce/static/index.html`.
- [x] Add a GPU-friendly animated AI orb with state-driven animation in `zworkforce/static/styles.css`.
- [x] Add push-to-talk to `zworkforce/static/app.js`:
  - pointer/touch press-and-hold;
  - `Space` press-and-hold when focus is not in an editable control;
  - explicit microphone permission state;
  - keyboard-accessible toggle fallback;
  - barge-in/cancel while Z.A.R.V.I.S. is speaking.
- [x] Show live state, partial/final transcript, last reply, runtime/model label, microphone state and approval-required state.
- [x] Reuse/extract the existing ZVoice PCM16/AudioWorklet realtime client instead of embedding ZVoice in an iframe.
- [x] Keep credentials server-side through a zWorkforce BFF/session endpoint.
- [x] Respect `prefers-reduced-motion` and provide a non-animated accessible state representation.

**R1 acceptance:** an authenticated control-plane user can hold PTT, speak, see the orb move through listening/thinking/speaking states, hear the answer, interrupt playback, and never receive an upstream credential.

### R2 — Shared browser voice client

- [x] Extract browser-safe capture/session/event logic from `apps/zvoice/public/app.js` into a shared Z.A.R.V.I.S. voice-client package.
- [x] Keep AudioWorklet PCM16 capture at 16 kHz and realtime interruption semantics.
- [x] Make ZVoice and the dashboard card consume the same client contract.
- [x] Add contract tests for session lifecycle, interruption, reconnect, ticket expiry and microphone denial.
- [x] Ensure the shared library cannot accept or serialize service/provider secrets.

### R3 — Speech provider registry

Refactor the voice runtime toward a typed registry while keeping the current service boundary.

- [x] Define STT provider interface: `transcribe/stream`, languages, sample-rate support, health and local/cloud classification.
- [x] Define TTS provider interface: `synthesize/stream`, voices, sample rates, health and local/cloud classification.
- [x] Register existing local speech implementation first.
- [x] Add optional adapters for Faster Whisper / Whisper-compatible STT and local TTS implementations already supported by deployment profiles.
- [x] Permit hosted providers only through server-side configuration and policy.
- [x] Surface provider health/capabilities to operators without exposing secrets.

### R4 — Z.A.R.V.I.S. skills runtime

- [x] Maintain a runtime skill manifest/catalog distinct from repository coding-agent skills under `.agents/skills`.
- [x] Each runtime skill declares: ID/version, description, required capabilities, allowed tools, mutability, approval policy, timeout, retry/idempotency behavior and input/output schema.
- [x] Discover skills deterministically with first-class validation and duplicate rejection.
- [x] Wrap skills behind the same policy/tool-execution boundary as normal tools.
- [x] Add skill dependency validation and bounded nested invocation.
- [x] Add active-version resolution, enable/disable, safe system-skill auto-update and explicit rollback foundation.
- [x] Reject automatic updates that silently add tool capabilities, escalate read→write mutability or weaken approval requirements.
- [ ] Persist complete lifecycle/trace state through the durable repository and prove restart-safe recovery for every lifecycle transition.
- [ ] Integrate signed remote marketplace packages through the existing skill-registry trust boundary.
- [x] Never auto-promote trace-mined/repeated-workflow skills into production; generated candidates require review and tests.

### R5 — Agent manager and execution modes

- [x] Normalize Z.A.R.V.I.S. agent manifests around three modes: `on_demand`, `scheduled`, `continuous`.
- [x] Add `voice-orchestrator` for low-latency spoken-turn routing.
- [x] Add `operator-supervisor` for heartbeat, stalled-run detection, rate limits and safe recovery.
- [x] Reuse existing specialist agents such as chief-of-staff, memory, code and review agents rather than cloning them.
- [x] Persist agent state/version, enforce capability policy, rate limits and max-concurrency.
- [x] Add event-driven triggers using existing durable scheduler/event infrastructure.
- [x] Add versioned rollout/rollback and failure budgets for continuous agents.

### R6 — Memory, context and conversation continuity

- [x] Bind voice sessions to tenant/subject-scoped conversation state.
- [x] Add durable project/conversation IDs, search, pin/archive and stable history navigation foundation.
- [ ] Expose context-budget state per conversation/model.
- [ ] Implement explicit compaction that creates a versioned summary artifact instead of silently rewriting history.
- [x] Retrieve only authorized memory and redact sensitive content before model/tool boundaries.
- [x] Separate ephemeral transcript context from durable memory writes.
- [x] Require explicit retention/consent policy for durable voice-derived memory.
- [x] Provide “forget this conversation” / deletion flows with auditable completion.

### R7 — Proactive Z.A.R.V.I.S.

- [x] Enable scheduled/continuous agents only with explicit subscriptions.
- [x] Add quiet hours, notification policy, rate limits and deduplication.
- [ ] Add tenant-scoped notification center for completion, approval, questions, failures, budget risk and stalled agents.
- [x] Add health/heartbeat telemetry and stalled-operator detection.
- [x] Route requests needing human authorization into the existing approval system rather than executing mutation autonomously.

### R8 — Intelligent local/cloud routing

- [x] Add query complexity classification and explicit local-first routing policy.
- [x] Add redaction-before-cloud and taint-aware policy checks.
- [x] Track latency, cost, quality and energy per route.
- [x] Support operator-configured failover without silent provider substitution for pinned workloads.
- [x] Keep cloud transmission disabled for protected data unless policy explicitly permits it.

### R9 — Observability and SLO hardening

- [x] Voice session setup, STT, reasoning, TTS and end-to-end latency histograms.
- [x] PTT start failures, microphone denial, ticket rejection, reconnects and interruption counters.
- [x] Agent/skill invocation traces with redacted parameters and correlation IDs.
- [x] Continuous-agent heartbeat, stale-run and rate-limit metrics.
- [x] Dashboard health view for the complete speech/agent pipeline.

Target interactive SLOs remain engineering targets until measured in an authorized production-equivalent environment:

- session ticket p95 < 100 ms on local network;
- end-of-turn detection ~300–600 ms;
- first partial transcript < 700 ms where supported;
- first synthesized audio < 1.5 s on suitable hardware.

### R10 — Production release gate

Repository/CI evidence and external production evidence are distinct. Completion of repository checks does not imply the following external gates have passed.

- [x] Repository Python, Node, voice, contract, static asset and Windows validation surfaces are defined and covered by CI/release tooling.
- [x] Security review requirements for microphone, WebSocket, auth, CSP, secrets and approval boundaries are defined.
- [x] Dependency/SBOM/provenance gates are represented in repository workflows.
- [ ] Record authorized staging voice latency, failure recovery and provider failover evidence for the exact release candidate.
- [x] Accessibility verification coverage for keyboard, screen reader and reduced-motion modes is implemented in the repository surface.
- [x] Rollback target and feature flags are documented.

### R11 — Workspace Agent UX and local execution

This roadmap line translates the strongest public Skywork workspace-agent patterns into zWorkforce-native capabilities. Full sequencing and acceptance criteria are in `planning/exec-planning-skywork.md`.

- [x] Durable projects, conversations, search, pin/archive and stable conversation IDs foundation.
- [ ] Auto naming and richer history navigation UX.
- [ ] Context gauge, explicit `/compact`, question anchors and context snapshot history.
- [ ] Slash command registry: `/plan`, `/review`, `/compact`, `/goal`, `/status`, `/artifacts`, `/cost`, `/skill`, `/workflow`, `/feedback`.
- [ ] Task summary sidecar with artifact manifest, review state, tool timeline and sanitized subagent hierarchy.
- [ ] Operator-granted local workspace roots with path/symlink escape protection and bounded subprocesses.
- [ ] Git branch/worktree adapter for isolated coding tasks; protected/default branches never mutated directly.
- [ ] Zider browser-use tool classes with read-only default and approval-gated side effects.
- [ ] Signed skill marketplace install, discovery scoring and repeated-workflow → draft skill/workflow candidate compiler.
- [ ] Markdown source/rendered preview, safe HTML preview and artifact history resilient across restarts.
- [ ] Task quick-start templates and evidence-based next-step suggestions.
- [ ] Theme profiles across web/WinUI without weakening accessibility/high-contrast support.
- [ ] FinOps preflight before expensive runs plus project/task/agent/model usage drilldown.
- [ ] Optional internal request signing with replay protection and key rotation for selected service-to-service boundaries.

---

## 6. Monorepo Sub-Package Forward Roadmaps

### 6.1 ZSP AI Studio & Video Renderer (`packages/zsp-aitool`)
- **Mission**: Thai-First Shopee Affiliate Marketing Platform and HyperFrames multi-scene video rendering engine (`:3005` / `studio.zeaz.dev`).
- **Milestones**:
  - [x] Integrate the package data model with strict tenant isolation requirements.
  - [x] App Router app shell (`AppLayout`, `Sidebar`, `Header`, `MobileNav`).
  - [x] Admin & Operator audit panel gated behind `ADMIN_PANEL_ENABLED`.
  - [x] Shopee API product ingestion and OCR vision pipeline foundation.
  - [x] Multi-platform social publishing adapter surfaces.
  - [x] Video rendering watchdog with stale-job recovery.

### 6.2 Zider AI Browser Companion (`packages/zider`)
- **Mission**: Manifest V3 AI Browser Sidebar Companion with Shadow DOM isolation, ChatPDF document intelligence, and multi-model group streaming (`:8085`).
- **Milestones**:
  - [x] Shadow DOM isolated sidebar and selection toolbar.
  - [x] Service worker background orchestrator and Chrome runtime message bus.
  - [x] Multi-model router with configured fallback support.
  - [x] Group AI multi-model streaming compare.
  - [x] ChatPDF tenant-scoped vector indexing and citation highlights.
  - [x] YouTube transcript summarizer and multi-language translator surfaces.

### 6.3 Zeto AI Content Factory (`packages/zeto`)
- **Mission**: Enterprise AI content lifecycle engine executing `IDEATE → GENERATE → WRITE → APPROVE → SCHEDULE → PUBLISH → MONITOR → LEARN`.
- **Milestones**:
  - [x] ProMeta prompt compiler architecture.
  - [x] Tool registry and point-cloud canvas HUD foundation.
  - [x] Multi-tenant content scheduling outbox with integrity protection.
  - [x] Automated QA scorecard evaluation and self-correction loops.

### 6.4 Autonomous Workspace & Deep Research Super Agents (`zworkforce` + `packages/zeto`)
- **Mission**: Skywork-inspired multimodal workspace intelligence capable of turning prompts into end-to-end research reports, slide specs, structured spreadsheets, and TTS-ready audio scripts while retaining source provenance and approval boundaries.
- **Architectural Paradigms**:
  - **A2A (Agent2Agent) Protocol Support**: interoperability for workforce agents to discover capabilities, exchange bounded context, and delegate sub-tasks across heterogeneous runtimes.
  - **Deep Research Autonomous Engine**: iterative multi-hop search, citation cross-referencing, document verification, and synthesis pipeline with source provenance.
  - **Cross-Model Memory Import**: standardized memory import/export with tenant, consent, and provenance controls.
  - **Multimodal Document Output Formats**: compilation of verified research into formatted Markdown, presentation specs, CSV/Excel data sheets, and TTS-ready audio scripts.

---

## 7. Non-goals

- Do not embed `apps/zvoice` with an iframe; its defensive framing policy is intentional.
- Do not send provider or service credentials to the dashboard or client extensions.
- Do not replace durable zWorkforce scheduler/approval/audit systems with a parallel OpenJarvis runtime.
- Do not claim a provider, model or external service is production-ready until operator evidence exists.
- Do not grant continuous agents unrestricted shell/network/action access.
- Do not grant a newly installed or auto-updated skill capabilities outside its existing authorized envelope.
- Do not treat local workspace access as permission to read or write arbitrary host filesystem paths.

## 8. Completion definition

The combined Z.A.R.V.I.S./workspace-agent upgrade is feature-complete when the control plane, Z.A.R.V.I.S. voice gateway, ZSP studio, Zider companion, and Zeto factory share unified tenant and secret boundaries, skills and agent modes are policy-governed and rollback-capable, scheduled/continuous operation has health and recovery controls, projects/conversations/context/artifacts are durable and tenant scoped, local/browser execution is sandboxed and approval-safe, FinOps is visible before and after execution, and all mutation continues through explicit approval/action boundaries.
