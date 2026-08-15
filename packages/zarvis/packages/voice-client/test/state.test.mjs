import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { INITIAL_STATE, reduce, VoiceStore } from "../src/state.js";

describe("state reducer", () => {
  it("SESSION_STATE updates session", () => {
    const next = reduce(INITIAL_STATE, { type: "SESSION_STATE", payload: "idle" });
    assert.equal(next.session, "idle");
  });

  it("PTT_START clears transcript and error", () => {
    const base = { ...INITIAL_STATE, transcript: "old", error: "prev" };
    const next = reduce(base, { type: "PTT_START" });
    assert.equal(next.ptt, "active");
    assert.equal(next.transcript, null);
    assert.equal(next.error, null);
  });

  it("PTT_COMMIT sets committed", () => {
    const next = reduce(INITIAL_STATE, { type: "PTT_COMMIT" });
    assert.equal(next.ptt, "committed");
  });

  it("PTT_CANCEL resets to idle", () => {
    const base = { ...INITIAL_STATE, ptt: "active" };
    const next = reduce(base, { type: "PTT_CANCEL" });
    assert.equal(next.ptt, "idle");
  });

  it("TRANSCRIPT sets transcript", () => {
    const next = reduce(INITIAL_STATE, { type: "TRANSCRIPT", payload: "hello" });
    assert.equal(next.transcript, "hello");
  });

  it("REPLY sets reply and resets ptt", () => {
    const base = { ...INITIAL_STATE, ptt: "committed" };
    const next = reduce(base, { type: "REPLY", payload: "world" });
    assert.equal(next.reply, "world");
    assert.equal(next.ptt, "idle");
  });

  it("APPROVAL_REQUIRED sets flag", () => {
    const next = reduce(INITIAL_STATE, { type: "APPROVAL_REQUIRED" });
    assert.equal(next.approvalRequired, true);
  });

  it("RESET returns to initial shape", () => {
    const dirty = { ...INITIAL_STATE, error: "oops", transcript: "stale" };
    const next = reduce(dirty, { type: "RESET" });
    assert.equal(next.error, null);
    assert.equal(next.transcript, null);
  });

  it("unknown action returns same state", () => {
    const next = reduce(INITIAL_STATE, { type: "__UNKNOWN__" });
    assert.equal(next, INITIAL_STATE);
  });

  it("INITIAL_STATE is frozen", () => {
    assert.throws(() => { INITIAL_STATE.session = "x"; });
  });
});

describe("VoiceStore", () => {
  it("dispatches and notifies subscribers", () => {
    const store = new VoiceStore();
    const states = [];
    store.subscribe((s) => states.push(s.session));
    store.dispatch({ type: "SESSION_STATE", payload: "idle" });
    assert.deepEqual(states, ["idle"]);
  });

  it("unsubscribe stops notifications", () => {
    const store = new VoiceStore();
    const seen = [];
    const unsub = store.subscribe((s) => seen.push(s.session));
    unsub();
    store.dispatch({ type: "SESSION_STATE", payload: "idle" });
    assert.equal(seen.length, 0);
  });
});
