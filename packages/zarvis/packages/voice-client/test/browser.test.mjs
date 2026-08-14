import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import vm from "node:vm";

async function loadClient(path = new URL("../src/browser.js", import.meta.url)) {
  const code = await readFile(path, "utf8");
  const context = {
    Uint8Array,
    Float32Array,
    ArrayBuffer,
    DataView,
    Math,
    Number,
    Set,
    TypeError,
    Error,
    Promise,
    btoa: (value) => Buffer.from(value, "binary").toString("base64"),
    atob: (value) => Buffer.from(value, "base64").toString("binary"),
  };
  context.globalThis = context;
  vm.runInNewContext(code, context, { filename: String(path) });
  return context.ZarvisVoiceClient;
}

test("PCM16 helpers round-trip and clamp", async () => {
  const client = await loadClient();
  const pcm = client.resampleToPcm16(new Float32Array([-2, -0.5, 0, 0.5, 2]), 16000, 16000);
  const decoded = client.pcm16ToFloat32(pcm);
  assert.equal(decoded.length, 5);
  assert.ok(decoded[0] <= -0.99);
  assert.ok(decoded[4] >= 0.99);
  assert.ok(Math.abs(decoded[2]) < 0.001);
  const b64 = client.bytesToBase64(pcm);
  assert.deepEqual(Array.from(client.base64ToBytes(b64)), Array.from(pcm));
});

test("state machine rejects unknown states", async () => {
  const client = await loadClient();
  const seen = [];
  const state = client.createStateMachine((next) => seen.push(next));
  assert.equal(state.value, "idle");
  state.transition("listening");
  state.transition("thinking");
  assert.deepEqual(seen, ["listening", "thinking"]);
  assert.throws(() => state.transition("executing_mutation"), /unknown voice state/);
});

test("realtime decoder ignores malformed frames", async () => {
  const client = await loadClient();
  assert.equal(client.decodeRealtimeEvent({ data: "{" }), null);
  assert.equal(client.decodeRealtimeEvent({ data: JSON.stringify({ type: "response.done" }) }).type, "response.done");
});

test("consumer distributions expose the same public API", async () => {
  const canonical = await loadClient();
  const zvoice = await loadClient(new URL("../../../apps/zvoice/public/voice-client.js", import.meta.url));
  const dashboard = await loadClient(new URL("../../../../../zworkforce/static/zarvis-voice-client.js", import.meta.url));
  const keys = Object.keys(canonical).sort();
  assert.deepEqual(Object.keys(zvoice).sort(), keys);
  assert.deepEqual(Object.keys(dashboard).sort(), keys);
  assert.equal(zvoice.SAMPLE_RATE, 16000);
  assert.equal(dashboard.SAMPLE_RATE, 16000);
});
