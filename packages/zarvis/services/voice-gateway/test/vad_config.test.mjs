import assert from "node:assert/strict";
import test from "node:test";
import { parseVadConfig, computePcm16Rms, isSpeechDetected, DEFAULT_VAD_CONFIG } from "../vad_config.mjs";

test("parseVadConfig returns defaults when empty", () => {
  const cfg = parseVadConfig();
  assert.equal(cfg.energyThreshold, DEFAULT_VAD_CONFIG.energyThreshold);
  assert.equal(cfg.silenceDurationMs, DEFAULT_VAD_CONFIG.silenceDurationMs);
  assert.equal(cfg.bargeInEnabled, true);
  assert.equal(cfg.autoRestartOnStall, true);
});

test("parseVadConfig bounds values to safe ranges", () => {
  const low = parseVadConfig({ energyThreshold: 0.00001, silenceDurationMs: 10, stallTimeoutMs: 100 });
  assert.equal(low.energyThreshold, 0.001);
  assert.equal(low.silenceDurationMs, 100);
  assert.equal(low.stallTimeoutMs, 1000);

  const high = parseVadConfig({ energyThreshold: 5.0, silenceDurationMs: 10000, stallTimeoutMs: 50000 });
  assert.equal(high.energyThreshold, 1.0);
  assert.equal(high.silenceDurationMs, 5000);
  assert.equal(high.stallTimeoutMs, 30000);
});

test("computePcm16Rms correctly measures amplitude", () => {
  // Silent buffer
  const silent = new Uint8Array(480 * 2); // 480 samples of 16-bit PCM
  assert.equal(computePcm16Rms(silent), 0);

  // Full amplitude square wave (+32767 / -32768)
  const full = new Uint8Array(480 * 2);
  const view = new DataView(full.buffer);
  for (let i = 0; i < 480; i++) {
    view.setInt16(i * 2, 32767, true);
  }
  const rms = computePcm16Rms(full);
  assert(rms > 0.99 && rms <= 1.0);
});

test("isSpeechDetected discriminates voice from silence", () => {
  const cfg = parseVadConfig({ energyThreshold: 0.05 });
  const silent = new Uint8Array(480 * 2);
  assert.equal(isSpeechDetected(silent, cfg), false);

  const speech = new Uint8Array(480 * 2);
  const view = new DataView(speech.buffer);
  for (let i = 0; i < 480; i++) {
    view.setInt16(i * 2, 8000, true); // ~0.24 amplitude
  }
  assert.equal(isSpeechDetected(speech, cfg), true);
});
