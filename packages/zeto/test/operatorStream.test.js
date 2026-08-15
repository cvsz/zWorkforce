"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const {
  parseSseBlocks,
  parseEventData,
  streamEntryFromEvent,
  orbPresentationForState,
  mergeEvents,
  applyStateChanged,
} = require("../public/js/operatorStream.js");

const SESSION = "00000000-0000-4000-8000-000000000001";

function envelope(type, payload = {}, sequenceId = 1) {
  return {
    event_id: `evt_${sequenceId}`,
    session_id: SESSION,
    generation: 1,
    sequence_id: sequenceId,
    type,
    occurred_at: "2026-08-15T00:00:00.000Z",
    correlation_id: "cmd_1",
    payload,
  };
}

test("parseSseBlocks parses event/data blocks and ignores comments", () => {
  const text = [
    ": keep-alive",
    "",
    "event: session.state_changed",
    'data: {"type":"session.state_changed","from":"IDLE","to":"LISTENING"}',
    "",
    "event: input.received",
    'data: {"type":"input.received"}',
    "",
  ].join("\n");
  const blocks = parseSseBlocks(text);
  assert.equal(blocks.length, 2);
  assert.equal(blocks[0].event, "session.state_changed");
  assert.equal(parseEventData(blocks[0].data).to, "LISTENING");
  assert.equal(blocks[1].event, "input.received");
});

test("streamEntryFromEvent maps catalog events to §4.2 entries", () => {
  const entry = streamEntryFromEvent(
    envelope("step.started", {
      plan_id: "p1",
      step_id: "s1",
      tool: "browser_navigate",
    }),
  );
  assert.equal(entry.id, "evt_1");
  assert.equal(entry.session_id, SESSION);
  assert.equal(entry.plan_id, "p1");
  assert.equal(entry.step_id, "s1");
  assert.equal(entry.actor, "zarvis");
  assert.equal(entry.result, "ok");
  assert.match(entry.summary, /browser_navigate/);
  assert.equal(entry.correlation_id, "cmd_1");

  const failed = streamEntryFromEvent(
    envelope("step.failed", { step_id: "s1", error: "timeout" }),
  );
  assert.equal(failed.result, "error");
  assert.equal(failed.error, "timeout");

  const blocked = streamEntryFromEvent(
    envelope("tool.require_approval", { step_id: "s1", risk: "high" }),
  );
  assert.equal(blocked.result, "blocked");
  assert.equal(blocked.risk, "high");

  const emergency = streamEntryFromEvent(
    envelope("emergency.stop", {
      reason: "safety interlock",
      kill_switch_latched: true,
    }),
  );
  assert.equal(emergency.result, "error");
  assert.equal(emergency.risk, "critical");
  assert.match(emergency.summary, /EMERGENCY STOP/);
});

test("streamEntryFromEvent classifies state_changed results per target", () => {
  const executing = streamEntryFromEvent(
    envelope("session.state_changed", {
      from: "IDLE",
      to: "EXECUTING",
      trigger: "auto_approved",
      actor: "zarvis",
    }),
  );
  assert.equal(executing.result, "ok");
  assert.match(executing.summary, /IDLE → EXECUTING/);

  const failed = streamEntryFromEvent(
    envelope("session.state_changed", {
      from: "EXECUTING",
      to: "FAILED",
      trigger: "step_failed",
      actor: "system",
    }),
  );
  assert.equal(failed.result, "error");

  const cancelled = streamEntryFromEvent(
    envelope("session.state_changed", {
      from: "PLANNING",
      to: "CANCELLED",
      trigger: "plan_rejected",
      actor: "policy",
    }),
  );
  assert.equal(cancelled.result, "cancelled");
});

test("streamEntryFromEvent returns null for non-stream events", () => {
  assert.equal(
    streamEntryFromEvent(envelope("transcript.partial", { text: "hel" })),
    null,
  );
  assert.equal(streamEntryFromEvent(null), null);
});

test("orbPresentationForState covers every canonical state with a reduced-motion fallback", () => {
  const states = [
    "IDLE",
    "LISTENING",
    "TRANSCRIBING",
    "THINKING",
    "PLANNING",
    "AWAITING_APPROVAL",
    "EXECUTING",
    "VERIFYING",
    "SPEAKING",
    "DEGRADED",
    "RECOVERING",
    "REAUTHORIZING",
    "PAUSED",
    "FAILED",
    "CANCELLED",
    "EMERGENCY_STOPPED",
  ];
  for (const state of states) {
    const presentation = orbPresentationForState(state);
    assert.ok(presentation.label, `${state} needs a label`);
    assert.ok(
      presentation.reducedMotion,
      `${state} needs a reduced-motion fallback`,
    );
    assert.ok(presentation.tone, `${state} needs a tone`);
  }
  assert.equal(orbPresentationForState("FAILED").tone, "danger");
  assert.equal(orbPresentationForState("DEGRADED").tone, "attention");
  assert.equal(orbPresentationForState("IDLE").tone, "idle");
});

test("mergeEvents dedupes by event_id, orders by sequence_id, and caps", () => {
  const a = envelope("input.received", { type: "text" }, 1);
  const b = envelope("session.state_changed", { to: "EXECUTING" }, 2);
  const c = envelope("step.finished", {}, 3);
  const merged = mergeEvents([b], [c, a, b]); // b duplicated, out of order
  assert.deepEqual(
    merged.map((e) => e.sequence_id),
    [1, 2, 3],
  );
  const capped = mergeEvents([a, b], [c], { max: 2 });
  assert.deepEqual(
    capped.map((e) => e.sequence_id),
    [2, 3],
  );
});

test("applyStateChanged returns the new state only for state_changed events", () => {
  assert.equal(
    applyStateChanged(
      "IDLE",
      envelope("session.state_changed", { to: "PLANNING" }),
    ),
    "PLANNING",
  );
  assert.equal(
    applyStateChanged("IDLE", envelope("input.received", {})),
    "IDLE",
  );
});
