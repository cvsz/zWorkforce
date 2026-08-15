"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const {
  EVENT_TYPES,
  isKnownEventType,
  assertEventType,
  buildEvent,
  buildStateChanged,
  buildEmergencyStop,
} = require("../src/domain/operatorEvents");
const { eventEnvelopeSchema } = require("../src/domain/operatorContracts");

test("event catalog is complete per spec §10", () => {
  const expected = [
    "session.started",
    "session.ended",
    "session.state_changed",
    "input.received",
    "transcript.partial",
    "transcript.final",
    "intent.resolved",
    "plan.created",
    "plan.approved",
    "plan.rejected",
    "step.started",
    "step.finished",
    "step.failed",
    "tool.require_approval",
    "verification.passed",
    "verification.failed",
    "speech.started",
    "speech.ended",
    "pairing.issued",
    "pairing.consumed",
    "incident.raised",
    "incident.resolved",
    "emergency.stop",
  ];
  assert.deepEqual([...EVENT_TYPES], expected);
});

test("envelope builder assigns unique event_id and leaves sequence_id null", () => {
  const event = buildEvent({
    sessionId: "00000000-0000-4000-8000-000000000001",
    generation: 3,
    type: "intent.resolved",
    correlationId: "cmd_x",
    payload: { intent: "publish", confidence: 0.9 },
  });
  assert.match(event.event_id, /^evt_[0-9a-f-]{36}$/);
  assert.equal(event.sequence_id, null); // assigned at persistence, never guessed
  assert.equal(event.generation, 3);
  assert.equal(event.correlation_id, "cmd_x");
  assert.equal(event.payload.intent, "publish");
});

test("unknown event types are rejected", () => {
  assert.throws(
    () => assertEventType("made.up.event"),
    /Unknown operator event type/,
  );
  assert.equal(isKnownEventType("session.started"), true);
  assert.equal(isKnownEventType("session.hacked"), false);
});

test("state_changed events carry from/to/trigger/actor for audit", () => {
  const event = buildStateChanged({
    sessionId: "00000000-0000-4000-8000-000000000001",
    generation: 1,
    from: "EXECUTING",
    to: "PAUSED",
    trigger: "pause",
    actor: "operator",
  });
  assert.equal(event.type, "session.state_changed");
  assert.deepEqual(event.payload, {
    from: "EXECUTING",
    to: "PAUSED",
    trigger: "pause",
    actor: "operator",
  });
});

test("emergency.stop is self-contained and immutable", () => {
  const event = buildEmergencyStop({
    sessionId: "00000000-0000-4000-8000-000000000001",
    generation: 1,
    actorId: "user-1",
    reason: "safety interlock",
    source: "operator",
    activePlanId: "plan-9",
    activeStepId: "step-3",
    grantsRevokedCount: 2,
    toolsCancelledCount: 1,
    killSwitchLatched: true,
  });
  assert.equal(event.type, "emergency.stop");
  assert.deepEqual(event.payload, {
    actor_id: "user-1",
    reason: "safety interlock",
    source: "operator",
    active_plan_id: "plan-9",
    active_step_id: "step-3",
    grants_revoked_count: 2,
    tools_cancelled_count: 1,
    kill_switch_latched: true,
  });
});

test("persisted envelope satisfies the contract schema", () => {
  const envelope = {
    event_id: "evt_1",
    session_id: "00000000-0000-4000-8000-000000000001",
    generation: 1,
    sequence_id: 42,
    type: "step.finished",
    occurred_at: new Date().toISOString(),
    correlation_id: "cmd_x",
    payload: { plan_id: "p1", step_id: "s1" },
  };
  const parsed = eventEnvelopeSchema.parse(envelope);
  assert.equal(parsed.sequence_id, 42);
  assert.equal(parsed.type, "step.finished");
});
