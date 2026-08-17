/**
 * vad_config.mjs
 *
 * Configurable Voice Activity Detection (VAD) & Adaptive Barge-in Parameters
 * for Z.A.R.V.I.S. Realtime Audio Streaming (PCM16 / 24kHz).
 */

export const DEFAULT_VAD_CONFIG = Object.freeze({
  energyThreshold: 0.015,
  silenceDurationMs: 650,
  speechPaddingMs: 120,
  bargeInEnabled: true,
  autoRestartOnStall: true,
  stallTimeoutMs: 5000,
});

export function parseVadConfig(input = {}) {
  const energy = Number(input.energyThreshold ?? DEFAULT_VAD_CONFIG.energyThreshold);
  const silence = Number(input.silenceDurationMs ?? DEFAULT_VAD_CONFIG.silenceDurationMs);
  const padding = Number(input.speechPaddingMs ?? DEFAULT_VAD_CONFIG.speechPaddingMs);
  const stall = Number(input.stallTimeoutMs ?? DEFAULT_VAD_CONFIG.stallTimeoutMs);

  return {
    energyThreshold: Math.min(1.0, Math.max(0.001, Number.isFinite(energy) ? energy : DEFAULT_VAD_CONFIG.energyThreshold)),
    silenceDurationMs: Math.min(5000, Math.max(100, Number.isFinite(silence) ? silence : DEFAULT_VAD_CONFIG.silenceDurationMs)),
    speechPaddingMs: Math.min(1000, Math.max(0, Number.isFinite(padding) ? padding : DEFAULT_VAD_CONFIG.speechPaddingMs)),
    bargeInEnabled: typeof input.bargeInEnabled === "boolean" ? input.bargeInEnabled : DEFAULT_VAD_CONFIG.bargeInEnabled,
    autoRestartOnStall: typeof input.autoRestartOnStall === "boolean" ? input.autoRestartOnStall : DEFAULT_VAD_CONFIG.autoRestartOnStall,
    stallTimeoutMs: Math.min(30000, Math.max(1000, Number.isFinite(stall) ? stall : DEFAULT_VAD_CONFIG.stallTimeoutMs)),
  };
}

export function computePcm16Rms(pcm16Bytes) {
  if (!pcm16Bytes || pcm16Bytes.length < 2) return 0;
  let sumSquare = 0;
  const sampleCount = Math.floor(pcm16Bytes.length / 2);
  const view = new DataView(pcm16Bytes.buffer, pcm16Bytes.byteOffset, pcm16Bytes.byteLength);

  for (let i = 0; i < sampleCount; i++) {
    const sample = view.getInt16(i * 2, true) / 32768.0;
    sumSquare += sample * sample;
  }
  return Math.sqrt(sumSquare / sampleCount);
}

export function isSpeechDetected(pcm16Bytes, config) {
  const rms = computePcm16Rms(pcm16Bytes);
  return rms >= config.energyThreshold;
}
