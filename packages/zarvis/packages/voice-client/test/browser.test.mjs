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

class FakeTarget {
  constructor() { this.listeners = new Map(); this.disabled = false; }
  addEventListener(type, handler) { const list = this.listeners.get(type) || []; list.push(handler); this.listeners.set(type, list); }
  removeEventListener(type, handler) { this.listeners.set(type, (this.listeners.get(type) || []).filter((item) => item !== handler)); }
  emit(type, event = {}) { for (const handler of this.listeners.get(type) || []) handler({ preventDefault() {}, detail: 1, repeat: false, target: null, ...event }); }
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

test("push-to-talk controller shares pointer, keyboard and cancel semantics", async () => {
  const client = await loadClient();
  const button = new FakeTarget();
  const keyboard = new FakeTarget();
  let starts = 0;
  let stops = 0;
  let cancels = 0;
  const ptt = client.bindPushToTalk({
    button,
    keyTarget: keyboard,
    editable: () => false,
    onStart: () => { starts += 1; },
    onStop: () => { stops += 1; },
    onCancel: () => { cancels += 1; },
  });
  button.emit("pointerdown", { pointerId: 1 });
  button.emit("pointerup", { pointerId: 1 });
  keyboard.emit("keydown", { code: "Space" });
  keyboard.emit("keyup", { code: "Space" });
  keyboard.emit("keydown", { code: "Escape" });
  assert.equal(starts, 2);
  assert.equal(stops, 2);
  assert.equal(cancels, 1);
  assert.equal(ptt.active, false);
  ptt.destroy();
});

test("dashboard and ZVoice consume the shared client primitives", async () => {
  const zvoice = await readFile(new URL("../../../apps/zvoice/public/app.js", import.meta.url), "utf8");
  const dashboard = await readFile(new URL("../../../../../zworkforce/static/app.js", import.meta.url), "utf8");
  for (const source of [zvoice, dashboard]) {
    assert.match(source, /ZarvisVoiceClient/);
    assert.match(source, /\.createAudioCapture\(/);
    assert.match(source, /\.openRealtimeSocket\(/);
    assert.equal((source.match(/function resampleToPcm16/g) || []).length, 1);
    assert.equal((source.match(/function bytesToBase64/g) || []).length, 1);
  }
  assert.match(dashboard, /\.bindPushToTalk\(/);
  assert.match(dashboard, /\.createStateMachine\(/);
  assert.match(zvoice, /\.createStateMachine\(/);
});
