/**
 * PCM-16 audio helpers — resampling, playback scheduling, and RMS.
 *
 * Browser-safe. No server credentials.
 * @module @z-platform/zarvis-voice-client/audio
 */

"use strict";

const DEFAULT_SAMPLE_RATE = 16000;

/**
 * Resample a Float32Array from inputRate → outputRate and return Uint8Array (PCM-16 LE).
 * @param {Float32Array} samples
 * @param {number} inputRate
 * @param {number} [outputRate=16000]
 * @returns {Uint8Array}
 */
export function resampleToPcm16(samples, inputRate, outputRate = DEFAULT_SAMPLE_RATE) {
  if (!samples.length) return new Uint8Array(0);
  if (!Number.isFinite(inputRate) || inputRate <= 0 || !Number.isFinite(outputRate) || outputRate <= 0) {
    throw new TypeError("sample rates must be positive finite numbers");
  }
  const ratio = inputRate / outputRate;
  const outLen = Math.max(1, Math.floor(samples.length / ratio));
  const buf = new ArrayBuffer(outLen * 2);
  const view = new DataView(buf);
  for (let i = 0; i < outLen; i++) {
    const pos = i * ratio;
    const left = Math.floor(pos);
    const right = Math.min(samples.length - 1, left + 1);
    const frac = pos - left;
    const s = samples[left] * (1 - frac) + samples[right] * frac;
    const clamped = Math.max(-1, Math.min(1, s));
    view.setInt16(i * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true);
  }
  return new Uint8Array(buf);
}

/**
 * Convert PCM-16 LE bytes → Float32Array.
 * @param {Uint8Array} bytes
 * @returns {Float32Array}
 */
export function pcm16ToFloat32(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const out = new Float32Array(Math.floor(bytes.byteLength / 2));
  for (let i = 0; i < out.length; i++) {
    const v = view.getInt16(i * 2, true);
    out[i] = v < 0 ? v / 0x8000 : v / 0x7fff;
  }
  return out;
}

/**
 * Compute RMS amplitude of Float32Array samples.
 * @param {Float32Array} samples
 * @returns {number}
 */
export function rms(samples) {
  if (!samples.length) return 0;
  let sum = 0;
  for (let i = 0; i < samples.length; i++) sum += samples[i] * samples[i];
  return Math.sqrt(sum / samples.length);
}

/**
 * Decode a base64 string to Uint8Array.
 * @param {string} b64
 * @returns {Uint8Array}
 */
export function base64ToBytes(b64) {
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

/**
 * Encode Uint8Array to base64.
 * @param {Uint8Array} bytes
 * @returns {string}
 */
export function bytesToBase64(bytes) {
  let binary = "";
  const chunk = 0x8000;
  for (let i = 0; i < bytes.length; i += chunk) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunk));
  }
  return btoa(binary);
}

/**
 * Schedule PCM-16 audio playback on the given AudioContext.
 * Returns the source node so the caller can stop it for barge-in.
 * @param {AudioContext} ctx
 * @param {Uint8Array} pcm16Bytes
 * @param {number} [sampleRate=16000]
 * @returns {AudioBufferSourceNode}
 */
export function schedulePcm16Playback(ctx, pcm16Bytes, sampleRate = DEFAULT_SAMPLE_RATE) {
  const samples = pcm16ToFloat32(pcm16Bytes);
  const buffer = ctx.createBuffer(1, samples.length, sampleRate);
  buffer.copyToChannel(samples, 0);
  const source = ctx.createBufferSource();
  source.buffer = buffer;
  source.connect(ctx.destination);
  source.start();
  return source;
}
