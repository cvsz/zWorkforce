# Local Realtime Voice Agent Architecture

## Status

Initial production-oriented vertical slice. External traffic remains disabled by default; published ports bind to loopback.

## Goals

- Real-time speech conversation with interruption handling.
- Local VAD, STT, and TTS, with a local or hosted OpenAI-compatible LLM.
- Keep model/provider credentials and platform service tokens out of the browser.
- Preserve `apps -> services -> packages/contracts` dependency direction.
- Keep provider credentials and model runtime access in server-side services, never in the browser.
- Support Ollama, llama.cpp, and vLLM without coupling the speech pipeline to one runtime.

## Components

```text
Browser / ZVoice
  │ POST /api/voice/session
  ▼
apps/zvoice (server-side)
  │ service-token authenticated ticket request
  ▼
services/voice-gateway :8450
  │ signed one-time ticket + WebSocket tunnel
  ▼
services/voice-agent :8765 (internal only)
  │ VAD -> STT -> LLM -> TTS
  │             │
  │             ├─ Ollama :11434/v1
  │             ├─ llama.cpp :8080/v1
  │             ├─ vLLM :8000/v1
  │             └─ hosted OpenAI-compatible provider
  ▼
PCM audio events returned to the browser
```

## Security boundary

1. `zvoice` holds `Z_PLATFORM_SERVICE_TOKEN` server-side.
2. The browser requests a voice session from `zvoice`; it never receives the service token.
3. `voice-gateway` issues a signed ticket with a 10–300 second lifetime.
4. The browser sends the ticket through `Sec-WebSocket-Protocol` as `zticket.<ticket>`.
5. The gateway validates the HMAC, expiry, tenant, subject, and nonce, then consumes the nonce.
6. The speech runtime has no published host port and only accepts traffic from the internal Compose network.
7. Provider credentials remain server-side in the configured speech/model runtime environment.

The first slice keeps consumed ticket nonces in memory and therefore runs `voice-gateway` as a single replica. Before horizontal scaling, move nonce consumption and active-session admission to Redis using an atomic `SET NX EX` operation.

## Realtime protocol

The speech runtime exposes the OpenAI Realtime-compatible `/v1/realtime` WebSocket endpoint. The ZVoice client sends 16 kHz mono PCM16 audio with `input_audio_buffer.append` and handles:

- `input_audio_buffer.speech_started`
- `input_audio_buffer.speech_stopped`
- live/final transcription events
- `response.output_audio.delta`
- `response.output_audio_transcript.done`
- `response.done`
- `error`

New user speech stops queued playback immediately, enabling barge-in behavior.

## Model/runtime profiles

| Profile | Best fit | OpenAI-compatible upstream |
|---|---|---|
| `voice-ollama` | Simple local setup, CPU/GPU, easy model management | `http://ollama:11434/v1` |
| `voice-llamacpp` | GGUF models, CPU/Metal/CUDA/Vulkan, tight memory control | `http://llama-cpp:8080/v1` |
| `voice-vllm` | NVIDIA GPU throughput, continuous batching, multi-session workloads | `http://vllm:8000/v1` |

Only one LLM profile should be selected per local deployment unless a separate provider router is configured.

## Capacity model

- `VOICE_NUM_PIPELINES` controls concurrent Hugging Face realtime pipelines. Each pipeline loads its own conversation handlers and can materially increase VRAM/RAM.
- `VOICE_MAX_SESSIONS` is enforced at `voice-gateway`.
- Start with one pipeline/session on CPU and two only after measuring memory and latency.
- The browser sends approximately 32 KB/s of uncompressed 16 kHz mono PCM16 before WebSocket framing.

## Target SLOs

These are engineering targets, not guarantees:

- Ticket issuance p95: under 100 ms on the local network.
- VAD end-of-turn decision: 300–600 ms after speech ends.
- First partial transcript: under 700 ms where the STT backend supports streaming.
- First synthesized audio: under 1.5 seconds after end-of-turn on a suitable GPU.
- Session setup success: at least 99.5% in a healthy single-node deployment.

Record actual values before enabling external production traffic.

## Speech Provider Selection

The voice-agent uses the `SpeechProviderRegistry` to resolve STT and TTS backends.

### Selection rules

1. **Explicit selection**: Workloads that pin a backend name (via `ZARVIS_STT_PROVIDER` / `ZARVIS_TTS_PROVIDER`) get exactly that provider. If the named provider is not registered, startup fails closed — no silent fallback.
2. **Default selection**: When no pin is set and a `default` provider is registered, that provider is used.
3. **Locality classification**: `local` providers run on-device/on-server without external network calls. `cloud` providers require credentials and egress — credentials are always server-side only.
4. **Health reporting**: The health endpoint reports provider name and locality, never credentials. An unhealthy provider does not trigger automatic failover without explicit `ZARVIS_STT_FALLBACK` / `ZARVIS_TTS_FALLBACK` configuration.
5. **Timeout and capability**: Each provider declares `timeout_seconds` and `max_audio_seconds`. The voice-agent enforces these before dispatching audio.

### Environment variables (non-secret)

| Variable | Purpose | Default |
|---|---|---|
| `ZARVIS_STT_PROVIDER` | STT provider name to select | `default` |
| `ZARVIS_TTS_PROVIDER` | TTS provider name to select | `default` |
| `ZARVIS_STT_FALLBACK` | Fallback STT provider on health failure | unset (no fallback) |
| `ZARVIS_TTS_FALLBACK` | Fallback TTS provider on health failure | unset (no fallback) |
| `VOICE_AGENT_REPORT_PROVIDERS` | Include provider summary in health output | `false` |

Credentials for cloud providers are loaded exclusively from server-side environment variables or secret store references — never from client requests, browser payloads, or query parameters.
