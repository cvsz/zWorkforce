# Z.A.R.V.I.S. Operator Runtime — Reverse-Engineering & Implementation Specification

**Status:** Master spec · Source of truth for **M12 — Z.A.R.V.I.S. Operator Runtime** (`exec-planing.md` references this document).
**Source inspected:** uploaded `videoplayback.mp4`, duration ~251.84 seconds, 640×360, 30fps. Brand surface observed: "Brahma AI".
**Acronym:** Z.A.R.V.I.S. = **Zeto Autonomous Runtime Virtual Intelligence System**.

This document records visible product behavior from the supplied recording and translates it into Zeto requirements. It does not claim hidden implementation details that cannot be observed from the recording. §1.3 holds a coarse timeline-evidence pass derived from automated frame extraction + OCR of the source recording: each row separates observed text from inference, and nothing is fabricated.

---

## 1. Video Evidence

### 1.1 Source metadata

| Property      | Value                                                                                               |
| ------------- | --------------------------------------------------------------------------------------------------- |
| Original file | `videoplayback.mp4`                                                                                 |
| Local ref     | `media/zarvis-ref.mp4` · SHA-256 `9f93ebdda2971c532a2bbde4767dcb71115d5da018c86bfcf594be0f40651398` (**local-only** — git-ignored, not committed to the repository) |
| Duration      | ~251.84 s (verified 251.843628 s via ffprobe)                                                       |
| Resolution    | 640×360 (h264, 30 fps, AAC)                                                                         |
| Frame rate    | 30 fps                                                                                              |
| Brand surface | "Brahma AI" (dark desktop app)                                                                      |

> **Reference-media policy:** the source recording is **local-only** — kept at `media/zarvis-ref.mp4` (SHA-256 `9f93ebdd…`), with `media/` git-ignored so the recording is **never committed to the repository**. The blob was removed from all commit history via a filter-branch rewrite (2026-08-15; `refs/original`/reflogs expired and `git gc --prune=now` run, so the object is no longer reachable — the rewrite requires force-push to fully take effect on any clones/remotes). Future reference media must likewise stay out of the repo or use **Git LFS / artifact storage with an immutable SHA-256 manifest**; replacing or re-encoding the reference requires updating the SHA-256 above and re-running frame extraction + OCR.
>
> **Reference-media manifest** (the recording is not distributed through the repository, so redistribution/license are not-applicable for repo releases):
>
> ```yaml
> id: zarvis-reference-video
> sha256: 9f93ebdda2971c532a2bbde4767dcb71115d5da018c86bfcf594be0f40651398
> source_type: user-supplied
> source_url: internal-upload
> repository_status: local-only (media/ git-ignored; not committed)
> license_status: not-applicable (not redistributed via the repository)
> redistribution_allowed: false
> added_at: 2026-08-15
> purpose: reverse-engineering-reference
> ```

### 1.2 Observed UI / interaction inventory

The recording shows a dark desktop AI operator application with a persistent command-center layout. Observed capabilities and surfaces:

1. Central animated AI orb / neural status visualization.
2. Mode controls across the top, including chat/voice-oriented and advanced/automation-oriented modes.
3. Left navigation with Dashboard and Settings.
4. Right-side Command Stream showing executed/observed actions and system messages.
5. Right-side Sequence Builder for composing and saving multi-step command sequences.
6. Command input bar with Send action and suggestion/shortcut controls.
7. Runtime telemetry such as CPU, RAM, network status and camera state.
8. Desktop automation demonstrated by opening/controlling another application (presentation software).
9. Browser automation demonstrated by navigating/interacting with a web page.
10. Computer/typing intent shown in command-stream examples.
11. Mobile pairing flow using a QR code and connection information.
12. Initial setup/onboarding flow for initializing the assistant and account/API configuration.
13. Advanced/automation modes surfaced as first-class operating modes.
14. Error/failure messages are visible in the command stream rather than being silently swallowed.
15. Dedicated **CAMERA PREVIEW** panel beside the command center (observed ~01:35–01:45).
16. Orb idle surface labelled **JARVIS CORE / WAITING FOR INPUT** with a "Ask Jarvis anything in STUDY mode…" prompt (~01:40–01:50).

### 1.3 Timeline evidence

**Pass type:** coarse evidence pass — 25 frames sampled on a 10-second grid (`ffmpeg` frame extraction) + `tesseract` OCR of `media/zarvis-ref.mp4`. This is **not** a frame-accurate scene map: interactions shorter than ~10 s, transitions, modal opens, clicks, and voice-state changes can be missed.

Rows are **independent observations** from the grid samples listed in `Sample(s)` — they are **not** a partition of the timeline. Overlapping windows (e.g., 01:20–01:40, 01:35–01:45, 01:40–01:50) simply mean the same samples informed multiple observations; downstream tooling must not treat them as mutually exclusive segments.

Sample IDs are **timestamp-based** (`t000` = 00:00, `t010` = 00:10, …, `t250` = 02:50) and unambiguous: at 30 fps, `t050` is the 50-second mark (frame 1500), not "frame 50". `Frame #` records the actual video frame number (`timestamp_s × 30`).

Each row separates **Observed** (visually confirmed from the frame) from **OCR text** (raw extracted text, noisy) from **Inference** (interpretation of the above). Confidence: **High** = OCR text matches a known surface; **Medium** = partial/weak OCR; **Low** = no OCR text, inference only.

**Confirmation taxonomy:** every row carries a `Confirmation` value — `pending_human` (pipeline-derived, awaiting visual pass), `human_confirmed` (reviewer-verified; record `confirmed_by` + `confirmed_at` + contact-sheet frame used). **High OCR confidence is not human confirmation** — no row below is `human_confirmed` yet; the human pass promotes rows individually.

| Sample(s)  | Timecode    | Frame #    | Surface                       | Observed                                             | OCR text                                                                                                                                 | Inference                                                                  | Requirement link         | Confidence | Confirmation  |
| ---------- | ----------- | ---------- | ----------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- | ------------------------ | ---------- | ------------- |
| t000, t010 | 00:00–00:10 | 0, 300     | Command center                | Orb + branding; telemetry cluster visible            | CPU, RAM, NET ONLINE, CAM OFF; COMMAND STREAM                                                                                            | Command-center layout active at start                                      | §2.2 S1; §2.3            | High       | pending_human |
| t010–t050  | 00:10–00:50 | 300–1500   | Command center                | Command stream + sequence panels; telemetry updating | COMMAND STREAM, SEQUENCE BUILDER; CPU 2–30%, RAM 38–52%, NET ONLINE, CAM OFF; clock 12:22–12:56 PM                                       | Live session with both panels and live telemetry                           | §2.2 S1; §4.2; §4.3      | High       | pending_human |
| t050–t090  | 00:50–01:30 | 1500–2700  | Orb / visual                  | No OCR-detectable text                               | (none)                                                                                                                                   | Likely orb/chat-mode surface — absence of text, not a positive observation | §2.3                     | Low        | pending_human |
| t080–t100  | 01:20–01:40 | 2400–3000  | Command center                | Telemetry cluster visible                            | CPU ~50%, NET ONLINE, CAM OFF; 02:11 PM                                                                                                  | Telemetry continues updating                                               | §2.2                     | Medium     | pending_human |
| t090       | 01:35–01:45 | 2700       | Camera preview                | Dedicated preview panel visible                      | CAMERA PREVIEW; 01:06 PM; CPU ~69%                                                                                                       | Camera preview is a first-class surface                                    | §2.2 S1 (camera preview) | Medium     | pending_human |
| t090, t100 | 01:40–01:50 | 2700, 3000 | JARVIS CORE orb               | Orb idle surface visible                             | JARVIS CORE / WAITING FOR INPUT; "Ask Jarvis anything in STUDY mode…"                                                                    | Orb idle surface labelled JARVIS CORE                                      | §2.2 S1; §2.3; §4.1      | Medium     | pending_human |
| t110–t130  | 01:50–02:10 | 3300–3900  | Onboarding                    | First-run setup flow visible                         | "Initialize Brahma AI — Set up your assistant in two quick steps, then launch into your personal AI dashboard"; Create Account; AI Setup | Onboarding wizard for assistant initialization                             | §2.1 S5; §2.2            | High       | pending_human |
| t130, t140 | 02:10–02:20 | 3900, 4200 | Transition                    | No OCR-detectable text                               | (none)                                                                                                                                   | Scene transition — not observed positively                                 | —                        | Low        | pending_human |
| t140–t160  | 02:20–02:40 | 4200–4800  | Command center + computer-use | Command stream updating                              | (Computer) type; "Brahma AI: I've opened Notepad and typed the HTML code for…"; CPU ~18%, RAM ~51%                                       | Desktop automation executed and reported in stream                         | §4.2; §7 DesktopTool     | High       | pending_human |
| t160–t170  | 02:40–02:52 | 4800–5100  | Command center                | Command stream continuation                          | Notepad/HTML task continuation text                                                                                                      | Task in progress / completion                                              | §4.2                     | Medium     | pending_human |

> **Coverage status:** coarse evidence pass only. Sub-10 s detail and all Medium/Low rows require human visual confirmation against the contact sheet (25-frame montage) before promotion to evidence; a frame-accurate scene-by-scene pass on re-watch would upgrade this from coarse to full reconstruction.
>
> **Provenance rule:** do not fabricate timecodes or behaviors. Every row is derived from the actual recording via `ffmpeg` frame extraction + `tesseract` OCR; rows with no OCR text are marked inference (Low) and must not be treated as positive observations. Rows remain `pending_human` until a reviewer confirms them (`confirmed_by`, `confirmed_at`).

---

## 2. UI Reconstruction

### 2.1 Screen map

| Screen              | Purpose                                                            | Path / surface       |
| ------------------- | ------------------------------------------------------------------ | -------------------- |
| S1 Command Center   | Primary operator surface (orb, telemetry, input)                   | `/zarvis`            |
| S2 Settings         | Provider/permission/capability configuration                       | Settings nav         |
| S3 Sequence Builder | Compose, save, reorder, run multi-step sequences                   | Right panel + dialog |
| S4 Pairing          | Mobile connect via short-lived QR token                            | Overlay              |
| S5 Onboarding       | First-run setup wizard (providers, permissions, capability checks) | Full-screen flow     |
| S6 Approval Drawer  | Consequential/mutating action approval                             | Slide-over           |
| S7 Incident Overlay | Degraded state, non-color-only alerting                            | Overlay on S1        |

### 2.2 Component hierarchy (S1 Command Center)

```
Command Center
├── Top Bar
│   ├── Mode Controls (Chat · Voice · Operator · Advanced/Automation)
│   ├── Telemetry Cluster (CPU, RAM, network, camera, CAMERA PREVIEW panel)
│   └── Connection / Identity pill
├── Left Navigation (Dashboard, Settings)
├── Center Stage
│   ├── Orb Renderer (state-driven)
│   └── Transcript Surface (streaming)
├── Right Column
│   ├── Command Stream
│   └── Sequence Builder
└── Bottom Command Bar
    ├── Text Input
    ├── Push-to-Talk Mic
    ├── Suggestion/Shortcut Chips
    └── Send
```

### 2.3 Orb motion & animation states

| Orb state    | Trigger                                 | Animation                     | Reduced-motion fallback |
| ------------ | --------------------------------------- | ----------------------------- | ----------------------- |
| IDLE         | No active session                       | Slow pulse                    | Static glyph            |
| LISTENING    | Mic active / VAD open                   | Rings expand, waveform        | "LISTENING" label       |
| TRANSCRIBING | Speech being decoded                    | Streaming tick                | Spinner                 |
| THINKING     | Planner running                         | Orbit speed-up                | "THINKING" label        |
| EXECUTING    | Tool running                            | Directed pulse                | Progress bar            |
| VERIFYING    | Postcondition check                     | Scan sweep                    | "VERIFYING" label       |
| SPEAKING     | TTS active                              | Speaking bars                 | Waveform icon           |
| DEGRADED     | Partial failure                         | Amber/red tint, non-color cue | Text + icon             |
| FAILED       | Canonical `FAILED` state (hard failure) | Shake/red flash + message     | Text + icon             |

Every animation is derived from real operator state (§3.3); the orb never fabricates status. Orb visual states are **presentations** of the canonical operator state machine — `ERROR` is not a runtime state; all failures map to canonical `FAILED` and are styled separately.

### 2.4 Responsive, error and empty states

- Breakpoints: desktop ≥1280 (full 3-column), tablet 768–1279 (2-column), mobile <768 (stacked; command stream collapses to drawer).
- Empty states: command stream ("No commands yet"), sequence list ("No saved sequences"), transcript ("Say or type a command").
- Error states: visible in command stream with `error` result and recovery hint; never silently swallowed (video observation 14).

---

## 3. Architecture

### 3.1 Target runtime diagram

```text
User
 │
 ├── Text
 ├── Push-to-Talk
 └── Sequence
       │
       ▼
┌───────────────────────┐
│ Z.A.R.V.I.S. Runtime  │
│ Session / Event Loop  │
└───────────┬───────────┘
            │
      Intent Router
            │
         Planner
            │
      Policy Engine
       ┌────┴────┐
       │         │
   Approved   Approval UI
       │
       ▼
     Executor
       │
 ┌─────┼─────────────┐
 ▼     ▼       ▼     ▼
Browser Desktop File Shell
 │
 ▼
Observer / Verifier
 │
 ▼
Audit + Memory + Events
 │
 ├── Command Stream
 ├── Orb State
 ├── Transcript
 └── Voice Response
```

### 3.2 Layers

1. **Session / event loop** — owns the operator session, correlates all events via `session_id`.
2. **Intent router** — maps text/speech to typed intents; resolves ambiguity.
3. **Planner** — produces typed, inspectable plans (never free-form).
4. **Policy engine** — deny-by-default grants, approval routing, budget/frequency/rate limits, kill switch.
5. **Executor** — runs plan steps through the tool gateway with timeout, cancellation, retry.
6. **Adapters** — Browser/Desktop/File/Shell/Application behind typed contracts (§7).
7. **Observer / verifier** — confirms postconditions before success is reported.
8. **Audit + memory + events** — immutable provenance, bounded memory, canonical event stream.

### 3.3 Operator state machine (transition table)

**State groups** — every transition rule references these sets; there are **no bare `any` rules**:

```text
IDLE
ACTIVE_STATES   = LISTENING, TRANSCRIBING, THINKING, PLANNING, AWAITING_APPROVAL,
                  EXECUTING, VERIFYING, SPEAKING, DEGRADED
PAUSABLE_STATES = AWAITING_APPROVAL, EXECUTING, VERIFYING, DEGRADED   (subset of ACTIVE_STATES)
RECOVERY_STATES = RECOVERING, REAUTHORIZING
PAUSED           (interruptible, resumable)
TERMINAL_STATES = FAILED, CANCELLED, EMERGENCY_STOPPED
NON_TERMINAL     = IDLE ∪ ACTIVE_STATES ∪ RECOVERY_STATES ∪ {PAUSED}
```

**Determinism rules:**

- `TERMINAL_STATES` have **no outbound transitions**. Leaving a terminal state requires a **new session generation** (`session_id` + `generation`), never a revert to a prior state.
- `EMERGENCY_STOPPED` is reachable from any `NON_TERMINAL` state but **only** for genuine safety interrupts: emergency stop, global kill switch, safety interlock. Ordinary cancellation, operator rejection, plan timeout and re-authorization failure route to `CANCELLED` — never to `EMERGENCY_STOPPED`.
- **Pause is only legal from `PAUSABLE_STATES ∪ RECOVERY_STATES`.** A pause request arriving during a non-pausable state is handled **deterministically per state** (single fixed behavior — never an implementer's choice between defer and cancel) and **never creates a checkpoint in a non-resumable state**:

| Non-pausable state | Pause request behavior                                                                                                                                                                                                                                                                             |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `LISTENING`        | Cancel mic capture → `IDLE`. Ephemeral audio discarded; no checkpoint.                                                                                                                                                                                                                            |
| `TRANSCRIBING`     | Cancel STT → `IDLE`. Partial transcript discarded and never entered as a command; no checkpoint.                                                                                                                                                                                                  |
| `THINKING`         | **Defer** — applied at the next pausable state (`AWAITING_APPROVAL` or `EXECUTING`). Intent resolution is bounded (3 s), so the pause lands within seconds; no checkpoint is created in `THINKING` itself.                                                                                         |
| `PLANNING`         | **Defer** — applied at the next pausable state (`AWAITING_APPROVAL` before any execution, or `EXECUTING` at the step boundary). Planning is bounded (≤5 s); no checkpoint is created in `PLANNING` itself.                                                                                         |
| `SPEAKING`         | Cancel TTS → `IDLE`. Tool actions are never replayed; only the in-flight TTS is stopped.                                                                                                                                                                                                          |

  **Pause entered from `RECOVERY_STATES`** preserves the checkpoint contract unchanged: `previous_state` records the recovery state the session was in (`RECOVERING`/`REAUTHORIZING`), while `resume_state` keeps its **original persisted value** (∈ `PAUSABLE_STATES`) — it is never recomputed from the recovery state. On resume the session re-enters `REAUTHORIZING → RECOVERING → resume_state`; recovery is idempotent (re-validates the same checkpoint, reacquires the lease, restores the same context).
- `resume_state` is validated to be in `PAUSABLE_STATES` at recovery time; an invalid target routes to `FAILED` (checkpoint corrupt).
- Every transition is audited (`from, to, trigger, actor, session_id, plan_id, step_id, ts`).

| From                       | To                                                                                                 | Trigger / Guard                                                                                                                                                                  | Timeout                 | Retry                   | On failure                                                    |
| -------------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------- | ----------------------- | ------------------------------------------------------------- |
| IDLE                       | LISTENING                                                                                          | Push-to-talk start or VAD open; mic permission granted                                                                                                                           | Listening idle: 15 s    | —                       | → IDLE                                                        |
| LISTENING                  | TRANSCRIBING                                                                                       | Speech result available                                                                                                                                                          | STT first-token: 2 s    | STT retry ×2            | → IDLE (no speech)                                            |
| TRANSCRIBING               | THINKING                                                                                           | Utterance finalized                                                                                                                                                              | —                       | —                       | → DEGRADED                                                    |
| THINKING                   | PLANNING                                                                                           | Intent resolved                                                                                                                                                                  | Intent budget: 3 s      | Re-route ×1             | → FAILED                                                      |
| PLANNING                   | AWAITING_APPROVAL                                                                                  | Policy requires human approval                                                                                                                                                   | Approval wait: 5 min    | —                       | → CANCELLED on reject/timeout                                 |
| PLANNING                   | EXECUTING                                                                                          | Auto-approved within policy (allowlisted, low risk)                                                                                                                              | —                       | —                       | → FAILED                                                      |
| AWAITING_APPROVAL          | EXECUTING                                                                                          | Operator approves / policy override (audited)                                                                                                                                    | —                       | —                       | → CANCELLED                                                   |
| EXECUTING                  | VERIFYING                                                                                          | Tool step completes                                                                                                                                                              | Step timeout (per tool) | Backoff 1 s→30 s, max 3 | → FAILED (non-retryable)                                      |
| VERIFYING                  | EXECUTING                                                                                          | Postcondition unmet, retry budget left                                                                                                                                           | Verify timeout: 10 s    | ≤ max attempts          | → FAILED                                                      |
| VERIFYING                  | SPEAKING                                                                                           | All steps verified                                                                                                                                                               | —                       | —                       | → DEGRADED                                                    |
| SPEAKING                   | IDLE                                                                                               | TTS completes                                                                                                                                                                    | TTS max: 30 s           | —                       | → IDLE                                                        |
| PAUSABLE_STATES ∪ RECOVERY | PAUSED                                                                                             | Operator pause (resumable, non-critical); pause during non-pausable states follows the deterministic per-state policy above — no checkpoint in a non-resumable state; pause from RECOVERY_STATES preserves the original `resume_state` | —                       | —                       | remains PAUSED                                                |
| PAUSED                     | REAUTHORIZING                                                                                      | Resume requested; session must re-authenticate                                                                                                                                   | Re-auth: 30 s           | ×2                      | → CANCELLED (denied/expired)                                  |
| PAUSED                     | CANCELLED                                                                                          | Operator cancel / session timeout / explicit abandon (ordinary, non-emergency)                                                                                                   | Session timeout: 24 h   | —                       | terminal                                                      |
| REAUTHORIZING              | RECOVERING                                                                                         | Re-authorization granted                                                                                                                                                         | —                       | —                       | → CANCELLED                                                   |
| RECOVERING                 | (persisted `resume_state` ∈ PAUSABLE_STATES: EXECUTING / VERIFYING / AWAITING_APPROVAL / DEGRADED) | Checkpoint validated, lease reacquired, context restored — resumes persisted `resume_state`                                                                                      | Recovery: 30 s          | ×3                      | → FAILED (checkpoint invalid)                                 |
| RECOVERING                 | FAILED                                                                                             | Checkpoint corrupt / unrecoverable                                                                                                                                               | —                       | —                       | terminal                                                      |
| NON_TERMINAL               | EMERGENCY_STOPPED                                                                                  | Emergency stop / global kill switch / safety interlock: immediately revoke ephemeral grants, cancel in-flight tools, latch kill switch                                           | —                       | —                       | terminal; restart = new session generation + re-authorization |
| ACTIVE ∪ RECOVERY          | FAILED                                                                                             | Hard failure, verification exhausted, or non-retryable error                                                                                                                     | —                       | —                       | terminal; incident surfaced                                   |
| ACTIVE ∪ RECOVERY          | CANCELLED                                                                                          | Operator reject / ordinary plan cancellation / plan timeout                                                                                                                      | Plan timeout: 15 min    | —                       | terminal                                                      |
| ACTIVE                     | DEGRADED                                                                                           | Partial/soft failure (e.g., one tool unavailable)                                                                                                                                | Auto-recover ≤ 30 s     | Probe ×3                | → FAILED                                                      |
| DEGRADED                   | (persisted `previous_state` — prior ACTIVE state)                                                  | Recovered; recovery target read from the persisted checkpoint, never guessed                                                                                                     | —                       | —                       | → FAILED                                                      |

**Checkpoint / resume contract** (persisted per session; the runtime never guesses the resume target):

```json
{
  "session_id": "...",
  "generation": 3,
  "state": "PAUSED",
  "previous_state": "EXECUTING",
  "resume_state": "EXECUTING",
  "checkpoint_id": "...",
  "plan_id": "...",
  "step_id": "...",
  "attempt": 2,
  "grants_revoked": true
}
```

Rules: every checkpoint persists **`previous_state`** (the state the session entered from) and **`resume_state`** (the target on resume; must be in `PAUSABLE_STATES` — invalid targets route to `FAILED`). `state: PAUSED` persists `resume_state` from the pre-pause state; `state: DEGRADED` persists `previous_state` as its recovery target; `RECOVERING`/`REAUTHORIZING` persist the same contract so a restart resolves the exact resume target; `grants_revoked` gates grant re-issuance (only on approval).

**Semantics:** checkpointing at plan-step granularity enables resume from `PAUSED`/crash (§13). `FAILED`/`CANCELLED`/`EMERGENCY_STOPPED` run cleanup: revoke ephemeral grants, cancel in-flight tools, emit terminal event. `EMERGENCY_STOPPED` additionally latches the kill switch; leaving it requires a **new session generation** with explicit restart and re-authorization. Re-authorization failure is ordinary cancellation (`CANCELLED`), never an emergency.

---

## 4. Command & Input Planes

### 4.1 Command taxonomy

| Category    | Examples                                                                                           | Risk        | Approval required                               |
| ----------- | -------------------------------------------------------------------------------------------------- | ----------- | ----------------------------------------------- |
| Navigation  | "open dashboard", "go to settings"                                                                 | None        | No                                              |
| Diagnostics | "run health check", "show telemetry"                                                               | None        | No                                              |
| Content     | "draft a caption for X"                                                                            | Low         | No                                              |
| Publish     | "post to Facebook"                                                                                 | High        | Yes (publication)                               |
| Sequence    | "run my morning sequence (dry-run)"                                                                | Medium–High | By policy                                       |
| Automation  | browser/desktop control                                                                            | High        | Yes unless allowlisted                          |
| System      | pause — authenticated operator, immediate                                                          | Low         | No (immediate)                                  |
| System      | emergency_stop — authenticated/authorized operator, immediate, non-blocking, immutable audit event | Critical    | No approval wait (**authorization ≠ approval**) |
| System      | credential_change — admin                                                                          | Critical    | Yes (admin)                                     |

### 4.2 Command stream event

```json
{
  "id": "evt_...",
  "session_id": "...",
  "plan_id": "...",
  "step_id": "...",
  "ts": "ISO-8601",
  "actor": "operator|zarvis|policy|system",
  "intent": "publish",
  "tool": "facebook_publish",
  "target": "https://...",
  "risk": "high",
  "approval": "approved|denied|not_required",
  "result": "ok|error|blocked|cancelled",
  "duration_ms": 0,
  "correlation_id": "..."
}
```

### 4.3 Sequence Builder

```json
{
  "id": "seq_...",
  "name": "morning-brief",
  "mode": "chat|operator|automation",
  "steps": [
    { "id": "s1", "intent": "fetch_queue", "args": {} },
    { "id": "s2", "intent": "summarize", "args": { "input": "s1.result" } },
    { "id": "s3", "intent": "speak", "args": { "text": "s2.result" } }
  ],
  "dryRun": false
}
```

Execution semantics: sequential steps; step outputs addressable (`s<N>.result`); each step idempotent via `idempotency_key`; partial failure stops and offers resume; save/run/dry-run supported; replay after failure is allowed only with operator confirmation for high-risk steps.

---

## 5. Voice Plane

- Browser microphone capture; VAD and push-to-talk modes; streaming STT adapter; barge-in/interruption support; streaming TTS adapter; provider-neutral STT/TTS interfaces with local-provider option.
- **Latency budgets:** STT first-token ≤ 2 s; TTS first-audio ≤ 1.5 s; end-to-end voice command → plan start ≤ 5 s (P95).
- **Fallback matrix:**

| Failure               | Fallback                                     |
| --------------------- | -------------------------------------------- |
| STT provider down     | Secondary STT provider, then text-only input |
| TTS provider down     | Secondary TTS, then silent text reply        |
| Mic permission denied | Text-only with visible notice                |
| Barge-in unreliable   | Disable barge-in for the session             |

- No raw audio persistence by default; retention requires explicit policy.

---

## 6. Agent & Orchestration Plane

### 6.1 Intent router

Classify utterances to typed intents with confidence; below threshold → clarifying question; unsupported intent → visible "cannot do" message with suggestions (never silent).

### 6.2 Planner

```json
{
  "plan_id": "...",
  "session_id": "...",
  "intent": "...",
  "steps": [
    {
      "step_id": "p1",
      "tool": "browser_navigate",
      "args": {},
      "risk": "low",
      "depends_on": []
    }
  ],
  "policy_verdict": "approved|approval_required|denied",
  "estimated_cost": 0,
  "created_at": "ISO-8601"
}
```

### 6.3 Skill manifest (registry)

```json
{
  "skill_id": "queue-brief",
  "version": "1.0.0",
  "description": "...",
  "capabilities": ["queue.read", "speak"],
  "entry": { "intent": "queue_brief" },
  "permissions": ["queue:read"],
  "max_cost_per_run": 0.1,
  "approval": "none"
}
```

### 6.4 Agent registry & delegation

Bounded delegation: parent agent may hand a sub-task to a registered child agent only within policy; child executes under inherited grants, emits its own provenance chain, and returns typed results. Delegation depth and fan-out are capped.

### 6.5 Tool gateway

Deny-by-default; explicit grants scoped by user/workspace/session; tool schemas enforced (zod-style validation); every call carries `session_id, plan_id, step_id, risk, approval, idempotency_key`.

### 6.6 Executor

Timeout, cancellation and retry per §3.3; graceful cancel propagates to adapters; orphaned tool calls are reconciled on session resume.

### 6.7 Observer / verifier

Each step declares postconditions; verifier confirms them before success; failure evidence stored with the step.

### 6.8 Memory boundaries

| Store    | Scope                         | Consent           | Retention        |
| -------- | ----------------------------- | ----------------- | ---------------- |
| Working  | Current session context       | Implicit          | Session end      |
| Episodic | Prior session summaries       | Explicit opt-in   | Configurable TTL |
| Durable  | User-approved facts/sequences | Explicit approval | Until revoked    |

---

## 7. Computer-Use Plane

All adapters are typed and sandboxed — never raw uncontrolled shell/browser access.

| Tool              | Capabilities                                                                        | Guardrails                               |
| ----------------- | ----------------------------------------------------------------------------------- | ---------------------------------------- |
| `BrowserTool`     | navigate, inspect DOM/a11y tree, click, type, upload, download metadata, screenshot | Origin allowlist, session-scoped profile |
| `DesktopTool`     | enumerate apps/windows, focus, keyboard/mouse, screen observation                   | App allowlist, no stealth                |
| `FileTool`        | sandboxed read/write                                                                | Workspace roots, path policy             |
| `ShellTool`       | allowlisted commands                                                                | Sandbox/container, resource+time limits  |
| `ApplicationTool` | typed adapters                                                                      | API-over-coordinates preference          |

**Observation → action loop:** observe (a11y tree/screen) → decide (policy-checked) → act → verify → record evidence. Observed browser/screen content is **untrusted data**: it can never grant tools or change policy (prompt-injection defense).

**Tool contract (request/response):**

```json
{
  "request": {
    "session_id": "",
    "plan_id": "",
    "step_id": "",
    "tool": "",
    "action": "",
    "args": {},
    "risk": "",
    "approval": "",
    "idempotency_key": "",
    "timeout_ms": 0
  },
  "response": {
    "ok": true,
    "result": {},
    "evidence": [],
    "duration_ms": 0,
    "verification": "passed|failed|pending"
  }
}
```

---

## 8. Safety & Security Boundary

### 8.1 Mandatory controls (unchanged from observed baseline)

- Deny-by-default tool permissions; explicit grants scoped by user/workspace/session.
- Approval required for destructive, external side-effect, credential, financial, publication and privilege-changing actions.
- Domain/application allowlists for autonomous execution.
- Secret redaction in UI, logs, screenshots and model context.
- Prompt-injection defense: observed content is untrusted data, never authority.
- Sandboxed shell/filesystem execution; rate, cost and step limits.
- Emergency stop transitions to the terminal `EMERGENCY_STOPPED` state: cancels active plans, revokes ephemeral grants immediately, and requires explicit restart and re-authorization before new sessions are accepted.
- Pairing QR tokens short-lived, single-use, bound to an authenticated operator session.

### 8.2 Threat model / risk matrix

| Threat                                  | Vector                            | Control                                              | Residual risk |
| --------------------------------------- | --------------------------------- | ---------------------------------------------------- | ------------- |
| Prompt injection via web/screen content | Malicious page instructs tools    | Content = untrusted data; no tool grant from content | Low           |
| Tool permission bypass                  | Step requests unlisted capability | Deny-by-default + schema validation + audit          | Low           |
| Plan replay / duplicate side effect     | Re-executed step                  | `idempotency_key` per step; transactional claims     | Low           |
| Secret leakage                          | Logs/screenshots/context          | Redaction pipeline; secret scan in CI                | Low           |
| Approval bypass                         | Policy override abuse             | Overrides audited; admin-only; 4-eyes for critical   | Medium        |
| Pairing token theft                     | QR interception                   | Single-use, short TTL, session-bound                 | Low           |
| Unbounded cost/run                      | Long/looping plans                | Cost/step/rate limits; plan timeout                  | Low           |
| Compromised provider credential         | Exfiltrated token                 | Least-privilege, per-env rotation, audit             | Medium        |

---

## 9. Backend API Contracts

Transport: SSE/WebSocket for transcript, command-stream, plan-step, telemetry and speech state updates. REST for commands and queries.

| Endpoint                             | Method   | Request                               | Response / events                              |
| ------------------------------------ | -------- | ------------------------------------- | ---------------------------------------------- |
| `/v1/operator/sessions`              | POST     | `{ mode, capabilities }`              | `{ session_id, pairing_token? }`               |
| `/v1/operator/sessions/:id/events`   | SSE      | `Last-Event-ID` (last `sequence_id`; 0 = from start) | `event` stream (catalog §10), resumable: server replays persisted events with `sequence_id` > `Last-Event-ID` in order |
| `/v1/operator/sessions/:id/commands` | POST     | `{ text?, audio_ref?, sequence_id? }` | `{ command_id, plan_id }`                      |
| `/v1/operator/sessions/:id/cancel`   | POST     | `{ reason }`                          | `{ status: "cancelling" }`                     |
| `/v1/operator/plans/:id`             | GET      | —                                     | plan object (§6.2)                             |
| `/v1/operator/plans/:id/approve`     | POST     | `{ decision }`                        | updated plan                                   |
| `/v1/operator/plans/:id/reject`      | POST     | `{ reason }`                          | updated plan                                   |
| `/v1/operator/sequences`             | GET/POST | sequence object (§4.3)                | sequence list                                  |
| `/v1/operator/sequences/:id/run`     | POST     | `{ dry_run }`                         | `{ run_id }`                                   |
| `/v1/operator/skills`                | GET      | —                                     | skill manifests (§6.3)                         |
| `/v1/operator/agents`                | GET      | —                                     | agent registry                                 |
| `/v1/operator/tools`                 | GET      | —                                     | tool catalog + grants                          |
| `/v1/operator/pairing`               | POST     | —                                     | short-lived QR token                           |
| `/v1/operator/telemetry`             | SSE      | —                                     | CPU/RAM/network/worker/queue/model/tool health |

---

## 10. Event Catalog (canonical)

**Event envelope (mandatory):** every catalog event is emitted inside this envelope, and every persisted `operator_events` row stores the envelope fields. `sequence_id` is a **monotonically increasing integer unique per `(session_id, generation)`** — the ordering contract for deterministic SSE/WebSocket resume (`Last-Event-ID`, §9/§13). `event_id` is globally unique; `correlation_id` ties the event to its originating command (reused across all events of one command). Timestamps alone are **not** an ordering contract; consumers must order by `sequence_id`.

```json
{
  "event_id": "evt_...",
  "session_id": "...",
  "generation": 3,
  "sequence_id": 1842,
  "type": "step.finished",
  "occurred_at": "ISO-8601",
  "correlation_id": "..."
}
```

| Event                                              | Actor          | Payload (key)                                            | Consumers                    |
| -------------------------------------------------- | -------------- | -------------------------------------------------------- | ---------------------------- |
| `session.started` / `session.ended`                | system         | mode                                                      | audit, telemetry             |
| `session.state_changed`                            | system         | from, to, trigger, actor                                  | audit, orb, SLOs             |
| `input.received`                                   | operator       | type (text/voice/sequence)                                | transcript, orb              |
| `transcript.partial` / `transcript.final`          | STT            | text, confidence                                          | transcript, orb              |
| `intent.resolved`                                  | router         | intent, confidence                                        | planner, audit               |
| `plan.created` / `plan.approved` / `plan.rejected` | planner/policy | plan_id, verdict                                          | UI, audit                    |
| `step.started` / `step.finished` / `step.failed`   | executor       | plan_id, step_id, tool, result                            | command stream, telemetry    |
| `tool.require_approval`                            | policy         | step_id, risk                                             | approval drawer              |
| `verification.passed` / `verification.failed`      | verifier       | step_id, evidence                                         | command stream               |
| `speech.started` / `speech.ended`                  | TTS            | text                                                      | orb, transcript              |
| `pairing.issued` / `pairing.consumed`              | system         | token_id                                                  | pairing UI                   |
| `incident.raised` / `incident.resolved`            | monitor        | level, scope                                              | incident overlay, SLOs       |
| `emergency.stop`                                   | operator       | actor_id, reason, source, active_plan_id, active_step_id, grants_revoked_count, tools_cancelled_count, kill_switch_latched | all subscribers, incident    |

**`session.state_changed`** is emitted for **every** §3.3 transition — this is the state machine's audit contract (`from, to, trigger, actor` in the payload; `session_id`/`generation`/`occurred_at` in the envelope; `plan_id`/`step_id`/`ts` carried via `correlation_id` where applicable). Audit completeness tests must assert one such event per transition.

**`emergency.stop`** is a safety-critical incident record: in addition to the envelope it carries a **self-contained** payload (above) so it can be replayed independently of session state — including how many ephemeral grants were revoked and how many tools were cancelled, and whether the kill switch latched. It is append-only and immutable.

---

## 11. Persistence Model

Entities: `operator_commands, operator_events, operator_plans, operator_plan_steps, operator_sequences, operator_sequence_steps, skill_manifests, agent_manifests, tool_grants, tool_executions, verification_evidence, voice_sessions, pairing_tokens`.

| Entity                                              | Key relations                   | Indexes                    | Retention                      |
| --------------------------------------------------- | ------------------------------- | -------------------------- | ------------------------------ |
| `operator_plans`                                    | 1:N `operator_plan_steps`       | `session_id, created_at`   | 90 d                           |
| `operator_plan_steps`                               | N:1 plan; 1:N `tool_executions` | `plan_id, (status)`        | 90 d                           |
| `operator_events`                                   | N:1 session                     | `(session_id, generation, sequence_id)` **unique**; `(session_id, ts, type)` | 180 d (audit immutable)        |
| `tool_executions`                                   | N:1 step                        | `(session_id, generation, idempotency_key)` **unique** | 90 d                           |
| `verification_evidence`                             | 1:1 step/execution              | `step_id`                  | 90 d                           |
| `pairing_tokens`                                    | 1:1 session                     | `(token_hash)` unique      | TTL 5 min                      |
| `voice_sessions`                                    | 1:1 session                     | `session_id`               | 24 h (no raw audio by default) |
| `skill_manifests`, `agent_manifests`, `tool_grants` | registry                        | `(id, version)`            | indefinite (versioned)         |

Audit events are append-only; all others are mutable operational state. Retention is configurable per deployment.

**Idempotency-key scope (frozen):** `idempotency_key` is scoped as `UNIQUE(session_id, generation, idempotency_key)` — a key is generated by the runtime per plan-step execution and must **survive retry/restart** (replaying the same step within the same session/generation returns the stored result), but is **not global across tenants or sessions**. Two sessions using the same key string (e.g. `publish-step-1`) never collide because the scope includes `session_id` + `generation`. Keys are never derived from user input alone (that would be a replay vector); the runtime prefixes with a per-step nonce. `sequence_id` ordering (same constraint shape as events) is guaranteed by `UNIQUE(session_id, generation, sequence_id)` on `operator_events`.

---

## 12. Observability & SLOs

**Metrics:** operator sessions, commands/sec, intent-resolution rate, plan completion rate, tool success/failure/retry counts, approval request delivery latency, approval UI render latency, policy evaluation latency, voice latency, cost/run, pairing success, incident count.
**Traces:** one trace per command: input → intent → plan → step → tool → verify → response, with `session_id`/`plan_id`/`step_id` as span attributes.
**SLOs (target):**

| SLO                                | Target      |
| ---------------------------------- | ----------- |
| Command → plan start (text)        | ≤ 2 s P95   |
| Voice first-token                  | ≤ 2 s P95   |
| Tool success rate (allowlisted)    | ≥ 99%       |
| Plan completion (no incident)      | ≥ 98%       |
| Approval request delivery latency  | ≤ 500 ms P95 |
| Approval UI render latency         | ≤ 1 s P95   |
| Policy evaluation latency          | ≤ 200 ms P95 |
| Operator surface availability      | ≥ 99.9%     |
| Secret leakage incidents           | 0           |

**SLO layering note:** approval SLOs measure the **platform** (request delivery, UI render, policy evaluation). The **human approval decision time** (how long the operator takes to click approve) is a **business metric** — reported for insight, never an infrastructure SLO; a slow operator is not an SLO violation.

---

## 13. Recovery Model

- **Crash:** session state reconstructed from `operator_events` + the persisted checkpoint contract (§3.3); the runtime enters `RECOVERING`, validates the checkpoint, reacquires the lease, and resumes the persisted `resume_state`. Invalid checkpoints route to `FAILED`. **Checkpoint recovery is only claimed where a durable boundary exists** — crash handling per state is explicit (§3.3 set definitions):

  | State on crash                                    | Restart policy                                                                                                                                                                                                |
  | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
  | `LISTENING` / `TRANSCRIBING`                      | Discard ephemeral audio + partial transcript → `IDLE`. No checkpoint.                                                                                                                                         |
  | `THINKING` / `PLANNING`                           | Restore the last durable command from `operator_commands`, then **re-run intent/planner from that durable input** → planning is redone; no partial plan is trusted. No checkpoint.                              |
  | `SPEAKING`                                        | Tool actions are **never replayed**; session returns to `IDLE`; only TTS may be resumed/restarted. No checkpoint.                                                                                              |
  | `AWAITING_APPROVAL` / `EXECUTING` / `VERIFYING` / `DEGRADED` | Checkpoint recovery allowed (§3.3 checkpoint contract). Unverified steps re-verify before continuation.                                                                                             |
  | `RECOVERING` / `REAUTHORIZING`                    | Crash mid-recovery re-runs recovery **idempotently from the same checkpoint** (re-validate, reacquire lease, restore context); the resume target is never recomputed.                                          |

- **Reconnect:** SSE/WebSocket resume with last `sequence_id` via the `Last-Event-ID` header (or equivalent WS resume field); the server replays persisted `operator_events` with `sequence_id > last` **in order** (see the canonical event envelope, §10), so a reconnected client reconstructs the command stream without gaps or duplicates.
- **Checkpoint:** plan-step granularity; resume from last verified step; unverified steps re-verify before continuation. The `state`/`resume_state`/`checkpoint_id` contract (§3.3) is persisted — the runtime never guesses the resume target.
- **Re-authorization:** `PAUSED → REAUTHORIZING`; granted → `RECOVERING` → prior state; denied/expired → `CANCELLED` (ordinary cancellation, not an emergency).
- **Pause vs emergency stop:** `PAUSED` resumes through `REAUTHORIZING`/`RECOVERING` to the prior resumable state; `EMERGENCY_STOPPED` is terminal — leaving it requires a **new session generation** with explicit restart + re-authorization.
- **Dead-letter:** steps failing past retry budget land in dead-letter with incident raised; operator may retry, cancel, or quarantine.
- **Backup/restore:** covered by `scripts/backup.sh` + `scripts/verify-backup.sh`; operator tables included in restore drills.

---

## 14. Testing & Release Evidence

- State-machine unit tests (every transition in §3.3), including terminal-state isolation (no outbound transitions) and kill-switch determinism (routes only to `EMERGENCY_STOPPED`).
- Planner schema/property tests.
- Tool permission and approval-bypass tests.
- Prompt-injection tests using malicious browser/page content.
- Browser/desktop provider-fake tests.
- Cancellation/timeout/retry/idempotency tests.
- Voice interruption and reconnect tests.
- Sequence replay and partial-failure tests.
- QR token expiry/replay tests.
- Audit completeness tests.
- E2E: voice/text command → plan → approval → tool execution → verification → spoken/UI result.
- Soak tests for long operator sessions and streaming reconnect.

### 14.1 Acceptance matrix (measurable)

| Gate              | Exit criterion                                                                                                                                                          |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| State machine     | All §3.3 transitions covered by tests; timeout/retry/cancel paths green; no outbound transitions from `TERMINAL_STATES`; kill switch routes only to `EMERGENCY_STOPPED` |
| Policy            | Bypass attempts blocked (test suite); approval matrix enforced                                                                                                          |
| Security          | Prompt-injection + secret-leakage suites green; trivy/gitleaks clean                                                                                                    |
| Voice             | Latency SLOs met in staging; fallback matrix exercised                                                                                                                  |
| E2E               | Full voice/text → verified action flow passes in staging                                                                                                                |
| Recovery          | Crash mid-plan resumes without duplicate side effects; crash in each non-checkpointable state (§13) restarts per the durability-boundary policy                            |
| Soak              | 12 h operator session, zero unrecoverable failures                                                                                                                      |
| Event stream      | Every §3.3 transition emits `session.state_changed`; envelope `sequence_id` monotonic per `(session_id, generation)`; SSE resume via `Last-Event-ID` replays without gaps or duplicates |
| Media provenance  | Reference media redistributed only if `redistribution_allowed == true`, **or** excluded from public/release artifacts (current status: `media/` git-ignored + SHA-256 manifest present, so repo releases carry no media) |

---

## 15. Implementation Order

1. M12 contracts + operator state machine + event stream.
2. Z.A.R.V.I.S. card and Command Stream wired to real events.
3. Sequence Builder persistence and execution.
4. Skill/tool registries and policy gateway.
5. Browser automation adapter + verifier.
6. Desktop/application adapter + verifier.
7. Voice STT/TTS + push-to-talk + barge-in.
8. Mobile pairing.
9. Advanced autonomous mode with bounded budgets and approvals.
10. Full security/E2E/soak/recovery evidence and production rollout.

---

## 16. Definition of Done

M12 is complete only when the visual operator is backed by real state, all tool execution passes through policy/approval, failures are visible and recoverable, every state transition is emitted as an ordered `session.state_changed` event resumable over SSE without gaps or duplicates, actions are auditable and verifiable, tests cover permission bypass/prompt injection/cancellation/replay, the full voice/text-to-action workflow passes the §14.1 acceptance matrix and staging release gates, and the **media-provenance release gate** passes (reference media not redistributed without confirmed license, or excluded from release artifacts — `media/` is git-ignored today).
