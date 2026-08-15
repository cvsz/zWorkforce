import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { resampleToPcm16, pcm16ToFloat32, rms, base64ToBytes, bytesToBase64 } from "../src/audio.js";

describe("resampleToPcm16", () => {
  it("returns empty for empty input", () => {
    assert.equal(resampleToPcm16(new Float32Array(0), 44100).length, 0);
  });

  it("throws on non-positive sample rate", () => {
    assert.throws(() => resampleToPcm16(new Float32Array([0]), 0));
    assert.throws(() => resampleToPcm16(new Float32Array([0]), 44100, -1));
  });

  it("produces 2 bytes per sample at correct output length", () => {
    const input = new Float32Array(44100).fill(0.5);
    const out = resampleToPcm16(input, 44100, 16000);
    assert.ok(out.byteLength > 0);
    assert.equal(out.byteLength % 2, 0);
  });
});

describe("pcm16ToFloat32 round-trip", () => {
  it("silence round-trips correctly", () => {
    const silence = new Float32Array(100).fill(0);
    const pcm = resampleToPcm16(silence, 16000, 16000);
    const back = pcm16ToFloat32(pcm);
    for (const s of back) assert.ok(Math.abs(s) < 1e-4);
  });
});

describe("rms", () => {
  it("returns 0 for silence", () => {
    assert.equal(rms(new Float32Array(100).fill(0)), 0);
  });

  it("returns 1 for full-scale positive", () => {
    assert.ok(Math.abs(rms(new Float32Array(100).fill(1)) - 1) < 1e-6);
  });
});

describe("base64 round-trip", () => {
  it("encodes and decodes correctly", () => {
    const bytes = new Uint8Array([1, 2, 3, 255, 0]);
    const b64 = bytesToBase64(bytes);
    const back = base64ToBytes(b64);
    assert.deepEqual(Array.from(back), Array.from(bytes));
  });
});
