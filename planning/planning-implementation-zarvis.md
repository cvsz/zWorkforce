# Planning & Implementation: Z.A.R.V.I.S. Voice & Assistant Gateway (`planning-implementation-zarvis.md`)

**Updated:** 2026-08-17T05:25Z (do-all-e2e + do-implementation-all-e2e cycle)
**Module:** `packages/zarvis/` Voice UI, Realtime Audio Streaming, Session Orchestrator, and WinUI Integration  
**Parent Strategy:** [`exec-planning.master.md`](exec-planning.master.md) & [`exec-planning-zarvis.md`](exec-planning-zarvis.md)

---

## 1. Module Overview & Architecture

Z.A.R.V.I.S. provides low-latency voice interaction, push-to-talk (PTT) streaming, and unified session orchestration:

```mermaid
graph TD
    subgraph "Client Interfaces"
        VOICE_CARD["Web Voice Card & Waveform HUD"]
        ORB_UI["Animated Voice State & Orb UI"]
        WINUI["Native Windows Client (WinUI 3)"]
    end

    subgraph "Voice Gateway & Audio Processing"
        WORKLET["Audio Worklet (PCM16 / 24kHz)"]
        VAD["Voice Activity Detection (VAD) & Barge-in"]
        BFF["Voice BFF Gateway (/api/v1/zarvis/voice)"]
    end

    subgraph "Orchestration & Tooling"
        SESSION_ORCH["Session & Task Orchestrator"]
        SLASH_RESOLVER["Slash Command Engine (/plan, /goal, /undo)"]
        TOOL_RUNNER["Governed Tool Execution Pipeline"]
    end

    VOICE_CARD --> WORKLET
    ORB_UI --> WORKLET
    WINUI --> BFF
    WORKLET --> VAD
    VAD --> BFF
    BFF --> SESSION_ORCH
    SESSION_ORCH --> SLASH_RESOLVER
    SESSION_ORCH --> TOOL_RUNNER
```

---

## 2. Completed Implementation Milestones

- [x] **Realtime Audio Streaming & PTT Barge-in**: Zero-secret browser-safe tokens with ephemeral lifetimes.
- [x] **Interactive Slash Command Menu & Doc Hints**: Real-time keyboard-driven autocomplete (`#slashMenu`, `#slashHint`) in frontend dashboard.
- [x] **Session Snapshot & State Machine**: Full resilience against network drops and restart events without secret leakage.
- [x] **Windows Client Contract Parity**: Multi-targeting build and tests for Windows Client compatibility.

---

## 3. Active & Upcoming Implementation Workstreams

### Phase 1: Gemini Live API & OpenAI Realtime Multi-Provider Voice Engine
- **Objective**: Bidirectional streaming WebSocket bridge supporting Gemini Live API and OpenAI Realtime audio.
- **Files**:
  - `packages/zarvis/services/zarvis-orchestrator/src/live_voice.ts`: Low-latency WebSocket handler.
  - `zworkforce/api_zarvis.py`: Ephemeral session issuing endpoint.

### Phase 2: Native WinUI Assistant Deep Integration
- **Objective**: WinUI 3 background audio capture, system global hotkey (`Win+Alt+Z`), and live transcription overlay.
- **Files**:
  - `ZWorkforceClient/src/ZWorkforceClient.Core/Services/VoiceService.cs`: Native audio pipeline.
  - `ZWorkforceClient/tests/ZWorkforceClient.Core.Tests/VoiceServiceTests.cs`: Unit tests.

### Phase 3: VAD Sensitivity Tuning & Adaptive Barge-in
- **Objective**: Configurable server-side VAD threshold (`energy_threshold`, `silence_duration_ms`) with per-session override and fail-safe auto-restart on stream stall.
- **Files**:
  - `packages/zarvis/services/voice-gateway/src/vad_config.ts`: VAD parameter schema and validation.
  - `packages/zarvis/services/voice-gateway/test/vad_config.test.mjs`: Boundary-value unit tests.

### Phase 4: Multi-Language Live Transcription Overlay
- **Objective**: Browser-visible real-time captions synchronized with Gemini Live streaming responses with language code switching (`BCP-47`).
- **Files**:
  - `packages/zarvis/apps/zvoice/src/transcript_overlay.ts`: DOM injection and fade-out animation.
  - `packages/zarvis/apps/zvoice/test/transcript_overlay.test.mjs`: Overlay rendering and cleanup tests.

---

## 4. Verification & Validation Protocol

```bash
# 1. Zarvis Package Tests & Linters
pnpm --dir packages/zarvis test
pnpm --dir packages/zarvis audit --audit-level high

# 2. Voice API Endpoint Unit Tests
PYTHONPATH=. python3 -m unittest tests/test_zarvis_voice_api.py -v
```
