# OpenJarvis → Z.A.R.V.I.S. Upgrade Map

## Purpose

This document records the architectural comparison between `open-jarvis/OpenJarvis` and the Z.A.R.V.I.S. suite inside `cvsz/zworkforce`. It is a refactor map, not an instruction to vendor or mirror OpenJarvis.

OpenJarvis is Apache-2.0 licensed. Architectural ideas may be independently implemented. If source code is adapted, preserve applicable copyright/license notices and record the upstream path/commit in the implementing PR.

## Decision summary

Z.A.R.V.I.S. already has stronger production boundaries for its current use case: short-lived realtime tickets, explicit service separation, server-side secrets, approval gateways, durable zWorkforce task semantics and a dedicated realtime browser experience. OpenJarvis contributes useful **composition and extensibility patterns**: typed registries, config-driven assembly, skill discovery/tool wrapping and explicit scheduled/continuous agent modes.

The target is therefore:

```text
OpenJarvis patterns
  registry + builder + skills + agent modes
                    |
                    v
zWorkforce / Z.A.R.V.I.S. existing control plane
  auth + tenant + approvals + audit + durable scheduler
                    |
                    v
shared realtime voice client
          /                       \
Dashboard Z.A.R.V.I.S. CARD       ZVoice full console
                    |
                    v
voice gateway -> voice agent -> orchestrator -> action/memory services
```

## Verified file-by-file comparison

| OpenJarvis source | What it provides | Z.A.R.V.I.S. target | Decision |
|---|---|---|---|
| `src/openjarvis/system/builder.py` | Config-driven composition of engine, model, tools, memory, channel, telemetry, sandbox, scheduler, workflow, sessions, speech, skills and agents. | `services/zarvis-orchestrator`, voice runtime configuration, existing zWorkforce scheduler/policy layers. | **ADOPT PATTERN.** Add explicit factories/composition boundaries; do not create a second scheduler or security subsystem. |
| `src/openjarvis/core/registry.py` | Isolated typed registries with duplicate rejection and `register/get/create/keys`. | Speech-provider registry first; later runtime skill/agent provider registries. | **ADOPT PATTERN.** Keep type/capability metadata and deterministic duplicate failure. |
| `src/openjarvis/speech/__init__.py` | Optional discovery/import of STT and TTS backends. | `services/voice-agent/speech/providers`. | **ADOPT PATTERN WITH POLICY.** Discovery must not silently enable cloud backends or bypass approved configuration. |
| `src/openjarvis/speech/tts.py` | TTS backend/result abstraction with synthesize, voices and health. | `services/voice-agent/speech/tts.py`. | **ADAPT.** Add streaming capability, local/cloud classification, latency/capability metadata and redaction-safe health reporting. |
| `src/openjarvis/speech/faster_whisper.py` | Local Faster Whisper STT backend. | Existing/local voice-agent STT implementation. | **REFERENCE/ADAPTER.** Preserve current realtime pipeline and expose it behind the new STT interface. |
| `src/openjarvis/speech/openai_whisper.py` | Whisper-compatible STT adapter. | Optional server-side STT provider adapter. | **OPTIONAL.** Feature-flagged; credentials remain server-side. |
| `src/openjarvis/speech/deepgram.py` | Hosted STT adapter. | Optional hosted speech provider. | **OPTIONAL / POLICY-GATED.** Never default-enable for protected data. |
| `src/openjarvis/speech/kokoro_tts.py` | Local TTS adapter. | Optional local TTS provider. | **REFERENCE.** Evaluate compatibility/latency before implementation. |
| `src/openjarvis/speech/openai_tts.py` | Hosted TTS adapter. | Optional hosted TTS provider. | **OPTIONAL / SERVER-SIDE ONLY.** |
| `src/openjarvis/speech/cartesia_tts.py` | Hosted/streaming TTS option. | Optional provider adapter. | **OPTIONAL.** Require explicit config, timeout, health and data-policy checks. |
| `frontend/src/hooks/useSpeech.ts` | Simple browser recording/transcription state hook using MediaRecorder. | Dashboard PTT state UX. | **ADOPT UX STATE IDEAS ONLY.** Do not replace ZVoice's lower-latency AudioWorklet/PCM16 realtime transport with MediaRecorder. |
| `frontend/src/components/Chat/MicButton.tsx` | Mic states, disabled reasons, progress feedback. | Z.A.R.V.I.S. CARD PTT control. | **ADOPT UX PRINCIPLES.** Expand to press-and-hold, keyboard, barge-in, approval and accessibility states. |
| `src/openjarvis/skills/manager.py` | Skill discovery, precedence, dependency validation, tool wrapping, catalog, nested invocation and trace-derived candidates. | `services/zarvis-orchestrator` runtime skill manager + `packages/zarvis/skills`. | **ADOPT PATTERN WITH STRONGER GOVERNANCE.** Every skill needs capability/tool/approval/timeout/idempotency metadata. Trace-derived skills remain review-only candidates. |
| `src/openjarvis/agents/manager.py` via system builder | Persistent agent management. | Z.A.R.V.I.S. agent manifest/version state. | **ADOPT CONCEPT.** Preserve zWorkforce database/tenant boundaries. |
| `src/openjarvis/agents/executor.py` via system builder | Agent execution integrated with traces/system. | Orchestrator + existing task runtime. | **INTEGRATE, DO NOT DUPLICATE.** Existing task execution/approval semantics remain authoritative. |
| `src/openjarvis/agents/scheduler.py` via system builder | Scheduled agent execution. | Existing zWorkforce scheduler/event infrastructure. | **DO NOT PORT AS A SECOND SCHEDULER.** Map agent manifests to existing durable occurrence/idempotency semantics. |
| OpenJarvis built-in `orchestrator`/`native_react` concepts | On-demand reasoning/tool selection. | Existing Z.A.R.V.I.S. orchestrator and specialist-agent catalog. | **REFERENCE.** Add low-latency `voice-orchestrator`; reuse existing agents. |
| OpenJarvis `morning_digest` | Scheduled briefing agent. | Future productivity/briefing runtime skill + scheduled agent. | **ADAPT AS OPTIONAL FEATURE.** Only when connectors and user subscription exist. |
| OpenJarvis `monitor_operative` / `operative` | Continuous stateful agents. | `operator-supervisor` + continuous execution mode. | **ADOPT MODE, HARDEN CONTROL.** Heartbeat, lease, rate limit, pause, failure budget and no privilege expansion. |
| OpenJarvis `native_openhands` concept | Code-executing agent. | Existing Z.A.R.V.I.S. code/build/review specialist agents and bounded tools. | **DO NOT DUPLICATE.** Route code work to existing catalog and sandbox/policy boundaries. |
| `docs/development/roadmap.md` continuous-operator items | Heartbeat, metrics, capability policy, rate limits, chaining, event-driven agents, version/rollback. | Z.A.R.V.I.S. agent manager/supervisor roadmap. | **ADOPT AS HARDENING BACKLOG.** |
| OpenJarvis local/cloud routing roadmap | Complexity routing, per-query cost, redaction-before-cloud, taint controls. | zWorkforce provider routing/FinOps/security layers. | **ADOPT SELECTIVELY.** Integrate with existing routing and policy rather than parallel engine logic. |

## Existing Z.A.R.V.I.S. files that remain authoritative

### Dashboard

- `zworkforce/static/index.html`
- `zworkforce/static/styles.css`
- `zworkforce/static/app.js`

The Z.A.R.V.I.S. CARD belongs here because this is the existing AI Workforce control-plane frontend.

### Voice surface

- `packages/zarvis/apps/zvoice/public/index.html`
- `packages/zarvis/apps/zvoice/public/app.js`
- `packages/zarvis/apps/zvoice/public/voice-worklet.js`
- `packages/zarvis/apps/zvoice/public/humanoid-view.js`
- `packages/zarvis/apps/zvoice/public/styles.css`
- `packages/zarvis/apps/zvoice/public/humanoid.css`
- `packages/zarvis/apps/zvoice/server.mjs`

The current ZVoice implementation already provides PCM16 AudioWorklet capture, realtime events, interruption, an animated orb/humanoid view, transcript state and Z.A.R.V.I.S. command dispatch. The dashboard should share/extract this client behavior rather than implement a weaker parallel stack.

### Voice runtime

- `packages/zarvis/services/voice-gateway/`
- `packages/zarvis/services/voice-agent/`
- `packages/zarvis/docs/architecture/voice-agent.md`
- `packages/zarvis/docs/operations/voice-agent.md`
- `packages/zarvis/compose.voice.yml`
- `packages/zarvis/compose.zarvis-owner-voice.yml`

### Assistant/orchestration boundaries

- `packages/zarvis/services/zarvis-orchestrator/`
- `packages/zarvis/services/zarvis-task-gateway/`
- `packages/zarvis/services/zarvis-action-gateway/`
- `packages/zarvis/services/zarvis-memory/`
- `packages/zarvis/services/zarvis-perception/`
- `packages/zarvis/services/zarvis-proactive/`
- `packages/zarvis/packages/contracts/`

### Agent catalog

`packages/zarvis/agents/` already contains a broad specialist catalog including architecture, memory, code exploration/review, build repair and chief-of-staff roles. New files should fill orchestration gaps rather than duplicate specialists.

## Z.A.R.V.I.S. CARD integration decision

### Rejected: iframe ZVoice

ZVoice deliberately sends defensive framing restrictions (`frame-ancestors 'none'` / `X-Frame-Options: DENY`). Weakening those headers only to embed the app would regress its isolation.

### Rejected: new MediaRecorder-only voice path

OpenJarvis's browser hook is useful as a small state-machine reference, but ZVoice already implements lower-level realtime capture and interruption. Replacing it with record-then-upload would increase turn latency and split behavior.

### Selected: shared browser-safe realtime client

1. Extract presentation-independent PTT/audio/session logic from ZVoice.
2. Keep all service/provider secrets in server components.
3. Add authenticated zWorkforce BFF endpoints that return only bounded browser session material.
4. Render a compact orb/PTT surface in the root dashboard.
5. Keep ZVoice as the rich/full-screen humanoid console.

## Target state machine

```text
idle
  -> arming
  -> listening
  -> transcribing
  -> thinking
       -> approval_required -> thinking
  -> speaking
       -> interrupted -> listening | idle
  -> idle

Any active state -> error -> idle/retry
Any capture state -> muted
```

Presentation components consume this state; transport code does not directly manipulate UI styling.

## Skill model decision

OpenJarvis treats skills as discoverable tool-like capabilities. Z.A.R.V.I.S. will adopt this idea but make the production manifest stricter.

Minimum manifest fields:

```text
id
version
description
input_schema
output_schema
required_capabilities
allowed_tools
mutability
approval_policy
timeout
max_concurrency
retry_policy
idempotency_strategy
audit_event_types
owner
```

A skill is rejected at discovery when its manifest is invalid, dependencies cycle, capabilities are unknown, a mutating path lacks approval policy, or a required tool is not allowlisted.

## Agent model decision

Every runtime agent has a declared mode:

- `on_demand`
- `scheduled`
- `continuous`

All modes use the existing zWorkforce authorization/audit/durable execution boundaries. Scheduled/continuous modes additionally require occurrence/lease IDs, heartbeat, concurrency/rate limits and version pinning.

## Licensing and provenance rule

For each future PR that adapts OpenJarvis implementation code:

1. identify the exact upstream file and commit;
2. confirm Apache-2.0 compatibility with the destination;
3. retain applicable notices/header attribution;
4. describe substantive modifications in the PR;
5. avoid copying unrelated modules/dependencies;
6. test the adapted behavior against zWorkforce security invariants.

Pure architectural reimplementation should still mention OpenJarvis as design inspiration in the PR when appropriate, but must not falsely represent upstream code as locally authored.