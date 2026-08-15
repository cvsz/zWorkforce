"use strict";

const crypto = require("node:crypto");

/**
 * Canonical M12 event catalog — spec §10.
 * Every catalog event is emitted inside the envelope below; every persisted
 * `operator_events` row stores the envelope fields.
 */

const EVENT_TYPES = Object.freeze([
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
]);

function isKnownEventType(type) {
  return EVENT_TYPES.includes(type);
}

function assertEventType(type) {
  if (!isKnownEventType(type)) {
    throw new Error(`Unknown operator event type: ${type}`);
  }
  return type;
}

/**
 * Build a catalog event envelope. `sequence_id` is assigned at persistence
 * time (monotonic per (session_id, generation)); here it stays null so callers
 * never guess ordering.
 */
function buildEvent({
  sessionId,
  generation,
  type,
  correlationId = null,
  payload = {},
  occurredAt = new Date(),
}) {
  assertEventType(type);
  return {
    event_id: `evt_${crypto.randomUUID()}`,
    session_id: sessionId,
    generation,
    sequence_id: null,
    type,
    occurred_at: occurredAt.toISOString(),
    correlation_id: correlationId,
    payload,
  };
}

/**
 * Build the mandatory `session.state_changed` event for a transition
 * (from, to, trigger, actor) — emitted for EVERY §3.3 transition.
 */
function buildStateChanged({
  sessionId,
  generation,
  from,
  to,
  trigger,
  actor,
  correlationId = null,
}) {
  return buildEvent({
    sessionId,
    generation,
    type: "session.state_changed",
    correlationId,
    payload: { from, to, trigger, actor },
  });
}

/**
 * Build the self-contained `emergency.stop` incident record — append-only and
 * immutable; re-playable independently of session state.
 */
function buildEmergencyStop({
  sessionId,
  generation,
  actorId,
  reason,
  source,
  activePlanId = null,
  activeStepId = null,
  grantsRevokedCount = 0,
  toolsCancelledCount = 0,
  killSwitchLatched = true,
  correlationId = null,
}) {
  return buildEvent({
    sessionId,
    generation,
    type: "emergency.stop",
    correlationId,
    payload: {
      actor_id: actorId,
      reason,
      source,
      active_plan_id: activePlanId,
      active_step_id: activeStepId,
      grants_revoked_count: grantsRevokedCount,
      tools_cancelled_count: toolsCancelledCount,
      kill_switch_latched: killSwitchLatched,
    },
  });
}

module.exports = {
  EVENT_TYPES,
  isKnownEventType,
  assertEventType,
  buildEvent,
  buildStateChanged,
  buildEmergencyStop,
};
