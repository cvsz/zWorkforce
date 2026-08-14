(function attachZarvisVoiceClient(root) {
  "use strict";

  const SAMPLE_RATE = 16000;
  const STATES = Object.freeze([
    "idle", "arming", "ready", "listening", "transcribing", "thinking",
    "speaking", "approval_required", "interrupted", "muted", "disconnected", "error",
  ]);
  const STATE_SET = new Set(STATES);

  function bytesToBase64(bytes) {
    let binary = "";
    const chunkSize = 0x8000;
    for (let index = 0; index < bytes.length; index += chunkSize) {
      binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
    }
    return root.btoa(binary);
  }

  function base64ToBytes(value) {
    const binary = root.atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
    return bytes;
  }

  function resampleToPcm16(input, inputRate, outputRate = SAMPLE_RATE) {
    if (!input.length) return new Uint8Array();
    if (!Number.isFinite(inputRate) || inputRate <= 0 || !Number.isFinite(outputRate) || outputRate <= 0) {
      throw new TypeError("sample rates must be positive finite numbers");
    }
    const ratio = inputRate / outputRate;
    const outputLength = Math.max(1, Math.floor(input.length / ratio));
    const output = new ArrayBuffer(outputLength * 2);
    const view = new DataView(output);
    for (let index = 0; index < outputLength; index += 1) {
      const position = index * ratio;
      const leftIndex = Math.floor(position);
      const rightIndex = Math.min(input.length - 1, leftIndex + 1);
      const fraction = position - leftIndex;
      const sample = input[leftIndex] * (1 - fraction) + input[rightIndex] * fraction;
      const clamped = Math.max(-1, Math.min(1, sample));
      view.setInt16(index * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
    }
    return new Uint8Array(output);
  }

  function pcm16ToFloat32(bytes) {
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const samples = new Float32Array(Math.floor(bytes.byteLength / 2));
    for (let index = 0; index < samples.length; index += 1) {
      const value = view.getInt16(index * 2, true);
      samples[index] = value < 0 ? value / 0x8000 : value / 0x7fff;
    }
    return samples;
  }

  function rms(samples) {
    if (!samples.length) return 0;
    let total = 0;
    for (const value of samples) total += value * value;
    return Math.min(1, Math.sqrt(total / samples.length) * 4);
  }

  function decodeRealtimeEvent(event) {
    const raw = typeof event === "string" ? event : event?.data;
    if (typeof raw !== "string") return null;
    try {
      const payload = JSON.parse(raw);
      return payload && typeof payload === "object" ? payload : null;
    } catch {
      return null;
    }
  }

  function createStateMachine(onChange, initial = "idle") {
    if (!STATE_SET.has(initial)) throw new TypeError(`unknown voice state: ${initial}`);
    let current = initial;
    return Object.freeze({
      get value() { return current; },
      transition(next, detail) {
        if (!STATE_SET.has(next)) throw new TypeError(`unknown voice state: ${next}`);
        current = next;
        onChange?.(next, detail);
        return current;
      },
    });
  }

  function isEditableTarget(target) {
    return Boolean(target?.closest?.('input,textarea,select,button,a,[contenteditable="true"]'));
  }

  function bindPushToTalk({ button, keyTarget = root, onStart, onStop, onCancel, editable = isEditableTarget }) {
    if (!button?.addEventListener || !keyTarget?.addEventListener) throw new TypeError("PTT targets must support events");
    let active = false;
    const start = (event) => { if (active || button.disabled) return; active = true; onStart?.(event); };
    const stop = (event) => { if (!active) return; active = false; onStop?.(event); };
    const pointerDown = (event) => { event.preventDefault?.(); try { button.setPointerCapture?.(event.pointerId); } catch {} start(event); };
    const pointerUp = (event) => { event.preventDefault?.(); stop(event); };
    const pointerCancel = (event) => stop(event);
    const click = (event) => { if (event.detail !== 0 || button.disabled) return; active ? stop(event) : start(event); };
    const keyDown = (event) => { if (event.code === "Escape") { onCancel?.(event); return; } if (event.code === "Space" && !event.repeat && !editable(event.target)) { event.preventDefault?.(); start(event); } };
    const keyUp = (event) => { if (event.code === "Space" && !editable(event.target)) { event.preventDefault?.(); stop(event); } };
    button.addEventListener("pointerdown", pointerDown);
    button.addEventListener("pointerup", pointerUp);
    button.addEventListener("pointercancel", pointerCancel);
    button.addEventListener("click", click);
    keyTarget.addEventListener("keydown", keyDown);
    keyTarget.addEventListener("keyup", keyUp);
    return Object.freeze({
      get active() { return active; }, stop,
      destroy() {
        button.removeEventListener("pointerdown", pointerDown); button.removeEventListener("pointerup", pointerUp); button.removeEventListener("pointercancel", pointerCancel); button.removeEventListener("click", click); keyTarget.removeEventListener("keydown", keyDown); keyTarget.removeEventListener("keyup", keyUp); active = false;
      },
    });
  }

  async function createAudioCapture({ audioContext, workletUrl, processorName, onSamples, mediaDevices = root.navigator?.mediaDevices, AudioWorkletNodeCtor = root.AudioWorkletNode }) {
    if (!audioContext?.audioWorklet || !mediaDevices?.getUserMedia || !AudioWorkletNodeCtor) throw new Error("browser audio capture is unavailable");
    await audioContext.audioWorklet.addModule(workletUrl);
    const stream = await mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } });
    const source = audioContext.createMediaStreamSource(stream);
    const node = new AudioWorkletNodeCtor(audioContext, processorName);
    node.port.onmessage = ({ data }) => onSamples?.(data);
    source.connect(node);
    const silent = audioContext.createGain(); silent.gain.value = 0; node.connect(silent).connect(audioContext.destination);
    let stopped = false;
    return Object.freeze({ stream, node, stop() { if (stopped) return; stopped = true; try { node.disconnect(); } catch {} try { source.disconnect(); } catch {} for (const track of stream.getTracks()) track.stop(); } });
  }

  function openRealtimeSocket(session, { onEvent, onClose, onError, WebSocketCtor = root.WebSocket } = {}) {
    if (!session?.websocket_url || !session?.ticket || !WebSocketCtor) return Promise.reject(new Error("invalid realtime voice session"));
    return new Promise((resolve, reject) => {
      const socket = new WebSocketCtor(session.websocket_url, [`zticket.${session.ticket}`]);
      let settled = false;
      socket.addEventListener("message", (event) => { const payload = decodeRealtimeEvent(event); if (payload) onEvent?.(payload, event); });
      socket.addEventListener("open", () => { if (!settled) { settled = true; resolve(socket); } }, { once: true });
      socket.addEventListener("error", (event) => { onError?.(event); if (!settled) { settled = true; reject(new Error("unable to connect realtime voice session")); } }, { once: true });
      socket.addEventListener("close", (event) => onClose?.(event), { once: true });
    });
  }

  root.ZarvisVoiceClient = Object.freeze({ SAMPLE_RATE, STATES, bytesToBase64, base64ToBytes, resampleToPcm16, pcm16ToFloat32, rms, decodeRealtimeEvent, createStateMachine, isEditableTarget, bindPushToTalk, createAudioCapture, openRealtimeSocket });
})(globalThis);

const VC = globalThis.ZarvisVoiceClient;
const startButton = document.querySelector("#start");
const muteButton = document.querySelector("#mute");
const stopButton = document.querySelector("#stop");
const cancelButton = document.querySelector("#cancel");
const clearButton = document.querySelector("#clear");
const stateBadge = document.querySelector("#voice-state");
const emptyState = document.querySelector("#empty");
const voiceStatus = document.querySelector("#status");
const voiceTranscript = document.querySelector("#transcript");
const systemPrompt = document.querySelector("#instructions");
const modelField = document.querySelector("#model");

const PIPELINE_SAMPLE_RATE = VC.SAMPLE_RATE;
let socket = null;
let audioContext = null;
let capture = null;
let muted = false;
let sessionConfigured = false;
let playhead = 0;
let activeSources = new Set();
let zarvisMode = false;
let zarvisSessionId = null;
let commandInFlight = false;

const voiceState = VC.createStateMachine();
function setVoiceStatus(message, tone = "idle", state = "idle") {
  voiceState.transition(state);
  voiceStatus.textContent = message;
  voiceStatus.dataset.tone = tone;
  stateBadge.textContent = message;
  stateBadge.dataset.tone = tone;
}

function appendTranscript(role, text) {
  if (!text) return;
  const item = document.createElement("li");
  const label = document.createElement("strong");
  label.textContent = role === "assistant" ? "ZARVIS: " : "You: ";
  item.append(label, document.createTextNode(text));
  item.dataset.role = role;
  voiceTranscript.append(item);
  emptyState.hidden = true;
  voiceTranscript.scrollTop = voiceTranscript.scrollHeight;
}

function stopPlayback() {
  for (const source of activeSources) { try { source.stop(); } catch {} }
  activeSources = new Set();
  playhead = audioContext?.currentTime || 0;
}

function queueAudio(base64Audio) {
  if (!audioContext || !base64Audio || zarvisMode) return;
  const samples = VC.pcm16ToFloat32(VC.base64ToBytes(base64Audio));
  if (!samples.length) return;
  const buffer = audioContext.createBuffer(1, samples.length, PIPELINE_SAMPLE_RATE);
  buffer.copyToChannel(samples, 0);
  const source = audioContext.createBufferSource();
  source.buffer = buffer;
  source.connect(audioContext.destination);
  const startAt = Math.max(audioContext.currentTime + 0.02, playhead);
  source.start(startAt);
  playhead = startAt + buffer.duration;
  activeSources.add(source);
  source.addEventListener("ended", () => activeSources.delete(source), { once: true });
}

function speakWithBrowser(text, locale) {
  if (!("speechSynthesis" in globalThis) || !text) return;
  globalThis.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = locale || "th-TH";
  globalThis.speechSynthesis.speak(utterance);
}

function sendSessionUpdate(instructions, target = socket) {
  if (!target || target.readyState !== WebSocket.OPEN) return;
  const effectiveInstructions = zarvisMode
    ? "Transcribe the owner's speech accurately. Do not answer the user; the ZARVIS orchestrator will produce the response."
    : instructions;
  target.send(JSON.stringify({ type: "session.update", session: { type: "realtime", instructions: effectiveInstructions } }));
  sessionConfigured = true;
}

async function dispatchZarvisTranscript(transcript) {
  if (!zarvisMode || !zarvisSessionId || !transcript || commandInFlight) return;
  commandInFlight = true;
  setVoiceStatus("ZARVIS is reasoning…", "busy", "thinking");
  try {
    const response = await fetch("/api/zarvis/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command_id: globalThis.crypto?.randomUUID?.() || `command-${Date.now()}`, session_id: zarvisSessionId, transcript, locale: "th-TH" }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload?.error?.message || "ZARVIS command failed");
    appendTranscript("assistant", payload.speech?.text || "Command completed");
    speakWithBrowser(payload.speech?.text, payload.speech?.locale);
    setVoiceStatus(payload.replayed ? "Replayed safely" : "Connected — speak naturally", "ready", "ready");
  } catch (error) {
    setVoiceStatus(error instanceof Error ? error.message : "ZARVIS command failed", "error", "error");
  } finally { commandInFlight = false; }
}

function handleRealtimeEvent(payload, event) {
  switch (payload.type) {
    case "session.created":
      sendSessionUpdate(systemPrompt?.value || "You are a concise, helpful voice assistant.", event?.target);
      setVoiceStatus("Connected — speak naturally", "ready", "ready");
      break;
    case "input_audio_buffer.speech_started":
      stopPlayback(); setVoiceStatus("Listening…", "busy", "listening"); break;
    case "input_audio_buffer.speech_stopped":
      setVoiceStatus("Transcribing…", "busy", "transcribing"); break;
    case "conversation.item.input_audio_transcription.completed": {
      const transcript = payload.transcript || payload.text || "";
      appendTranscript("user", transcript);
      if (zarvisMode) { event?.target?.send?.(JSON.stringify({ type: "response.cancel" })); void dispatchZarvisTranscript(transcript); }
      break;
    }
    case "response.audio.delta":
    case "response.output_audio.delta":
      queueAudio(payload.delta); if (!zarvisMode) setVoiceStatus("Speaking…", "busy", "speaking"); break;
    case "response.audio_transcript.done":
    case "response.output_audio_transcript.done":
      if (!zarvisMode) appendTranscript("assistant", payload.transcript || payload.text || ""); break;
    case "response.done":
      if (!zarvisMode && !commandInFlight) setVoiceStatus("Connected — speak naturally", "ready", "ready"); break;
    case "error":
      if (!zarvisMode) setVoiceStatus(payload.error?.message || "Voice session error", "error", "error"); break;
    default: break;
  }
}

async function requestVoiceSession() {
  const response = await fetch("/api/voice/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instructions: systemPrompt?.value || "You are a concise, helpful voice assistant.", session_id: zarvisSessionId || undefined }),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error?.message || payload.error || "Unable to start voice session");
  return payload;
}

async function startCapture() {
  audioContext = new AudioContext({ latencyHint: "interactive" });
  capture = await VC.createAudioCapture({
    audioContext,
    workletUrl: "/voice-worklet.js",
    processorName: "z-platform-voice-capture",
    onSamples: (data) => {
      if (muted || !sessionConfigured || socket?.readyState !== WebSocket.OPEN) return;
      const bytes = VC.resampleToPcm16(data, audioContext.sampleRate, PIPELINE_SAMPLE_RATE);
      if (!bytes.length) return;
      socket.send(JSON.stringify({ type: "input_audio_buffer.append", audio: VC.bytesToBase64(bytes) }));
    },
  });
}

async function startVoice() {
  startButton.disabled = true;
  sessionConfigured = false;
  setVoiceStatus("Requesting secure voice ticket…", "busy", "arming");
  try {
    const session = await requestVoiceSession();
    zarvisMode = Boolean(session.zarvis_mode);
    zarvisSessionId = session.zarvis_session_id || zarvisSessionId;
    if (modelField) modelField.value = session.model || modelField.value;
    await startCapture();
    socket = await VC.openRealtimeSocket(session, {
      onEvent: handleRealtimeEvent,
      onClose: () => { setVoiceStatus("Disconnected", "idle", "disconnected"); void stopVoice(); },
      onError: () => setVoiceStatus("Unable to connect to the voice gateway", "error", "error"),
    });
    muteButton.disabled = false;
    cancelButton.disabled = false;
    stopButton.disabled = false;
    setVoiceStatus("Configuring realtime session…", "busy", "arming");
  } catch (error) {
    setVoiceStatus(error instanceof Error ? error.message : "Unable to start voice", "error", "error");
    await stopVoice();
  }
}

async function stopVoice() {
  sessionConfigured = false;
  const currentSocket = socket;
  socket = null;
  if (currentSocket && currentSocket.readyState < WebSocket.CLOSING) currentSocket.close(1000, "client_stop");
  stopPlayback();
  capture?.stop();
  capture = null;
  if (audioContext && audioContext.state !== "closed") await audioContext.close();
  audioContext = null;
  muted = false;
  commandInFlight = false;
  startButton.disabled = false;
  muteButton.disabled = true;
  muteButton.textContent = "Mute";
  cancelButton.disabled = true;
  stopButton.disabled = true;
}

startButton?.addEventListener("click", () => void startVoice());
stopButton?.addEventListener("click", () => void stopVoice());
muteButton?.addEventListener("click", () => {
  muted = !muted;
  muteButton.textContent = muted ? "Unmute" : "Mute";
  setVoiceStatus(muted ? "Microphone muted" : "Connected — speak naturally", muted ? "idle" : "ready", muted ? "muted" : "ready");
});
cancelButton?.addEventListener("click", () => {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: "response.cancel" }));
    stopPlayback();
    globalThis.speechSynthesis?.cancel?.();
    setVoiceStatus("Response cancelled", "ready", "interrupted");
  }
});
clearButton?.addEventListener("click", () => { voiceTranscript.replaceChildren(); emptyState.hidden = false; });
window.addEventListener("beforeunload", () => { const currentSocket = socket; if (currentSocket && currentSocket.readyState < WebSocket.CLOSING) currentSocket.close(); capture?.stop(); });
