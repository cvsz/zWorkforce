"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const databaseUrl = process.env.TEST_DATABASE_URL;
const integrationTest = databaseUrl ? test : test.skip;

async function freshPool() {
  const { createPool } = require("../src/database/pool");
  const { migrate } = require("../src/database/migrate");
  const pool = createPool({ connectionString: databaseUrl, max: 3 });
  await migrate(pool);
  await pool.query(
    "TRUNCATE operator_events, operator_commands, operator_plan_steps, operator_plans, tool_executions, verification_evidence, operator_sessions CASCADE",
  );
  return pool;
}

async function createSession(runtime) {
  return runtime.createSession({
    mode: "operator",
    capabilities: ["queue.read"],
  });
}

integrationTest(
  "session creation emits session.started at sequence 1",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session, event } = await createSession(runtime);
    assert.equal(session.state, "IDLE");
    assert.equal(session.generation, 1);
    assert.equal(event.type, "session.started");
    assert.equal(event.sequence_id, 1);
    await pool.end();
  },
);

integrationTest(
  "every transition emits one state_changed with monotonic sequence",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session } = await createSession(runtime);

    const triggers = [
      "start_listening",
      "speech_available",
      "utterance_finalized",
      "intent_resolved",
      "require_approval",
    ];
    let previousSequence = 1; // session.started
    for (const trigger of triggers) {
      const { events, transition } = await runtime.transition(
        session.id,
        trigger,
        {
          actor: "operator",
        },
      );
      assert.equal(events.length, 1);
      assert.equal(events[0].type, "session.state_changed");
      assert.equal(events[0].payload.from, transition.from);
      assert.equal(events[0].payload.to, transition.to);
      assert.equal(events[0].payload.trigger, trigger);
      assert.ok(
        events[0].sequence_id > previousSequence,
        "sequence_id must increase monotonically",
      );
      previousSequence = events[0].sequence_id;
    }

    const final = await runtime.getSession(session.id);
    assert.equal(final.state, "AWAITING_APPROVAL");

    const replay = await runtime.eventsAfter(session.id, 0);
    assert.equal(replay.length, 6); // started + 5 transitions
    const sequenceIds = replay.map((event) => event.sequence_id);
    assert.deepEqual(
      sequenceIds,
      [...sequenceIds].sort((a, b) => a - b),
      "replay must be in sequence order",
    );
    for (let index = 1; index < sequenceIds.length; index += 1) {
      assert.equal(
        sequenceIds[index] - sequenceIds[index - 1],
        1,
        "replay must have no gaps",
      );
    }
    const stateChanges = replay.filter(
      (e) => e.type === "session.state_changed",
    );
    assert.equal(stateChanges.length, 5, "one state_changed per transition");
    await pool.end();
  },
);

integrationTest(
  "pause from EXECUTING checkpoints and resume returns to EXECUTING",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session } = await createSession(runtime);

    // Drive to EXECUTING
    for (const trigger of [
      "start_listening",
      "speech_available",
      "utterance_finalized",
      "intent_resolved",
      "auto_approved",
    ]) {
      await runtime.transition(session.id, trigger, { actor: "operator" });
    }
    assert.equal((await runtime.getSession(session.id)).state, "EXECUTING");

    const paused = await runtime.pause(session.id, { actor: "operator" });
    assert.equal(paused.session.state, "PAUSED");
    assert.equal(paused.session.previousState, "EXECUTING");
    assert.equal(paused.session.resumeState, "EXECUTING");
    assert.ok(paused.checkpointId);

    const resumed = await runtime.resume(session.id, { actor: "operator" });
    assert.equal(resumed.session.state, "EXECUTING");
    await pool.end();
  },
);

integrationTest(
  "pause during PLANNING defers to the next pausable state",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session } = await createSession(runtime);

    for (const trigger of [
      "start_listening",
      "speech_available",
      "utterance_finalized",
      "intent_resolved",
    ]) {
      await runtime.transition(session.id, trigger, { actor: "operator" });
    }
    assert.equal((await runtime.getSession(session.id)).state, "PLANNING");

    const deferred = await runtime.pause(session.id, { actor: "operator" });
    assert.equal(deferred.deferred, true);
    assert.equal(deferred.session.state, "PLANNING");
    assert.equal(deferred.session.pendingPause, true);

    // Reaching the next pausable state applies the deferred pause automatically.
    await runtime.transition(session.id, "require_approval", {
      actor: "operator",
    });
    const after = await runtime.getSession(session.id);
    assert.equal(after.state, "PAUSED");
    assert.equal(after.resumeState, "AWAITING_APPROVAL");
    assert.equal(after.pendingPause, false);
    await pool.end();
  },
);

integrationTest(
  "pause during LISTENING cancels to IDLE with no checkpoint",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session } = await createSession(runtime);

    await runtime.transition(session.id, "start_listening", {
      actor: "operator",
    });
    const result = await runtime.pause(session.id, { actor: "operator" });
    assert.equal(result.session.state, "IDLE");
    assert.equal(result.session.resumeState, null);
    assert.equal(result.session.checkpointId, null);
    await pool.end();
  },
);

integrationTest(
  "emergency stop is terminal, latches kill switch, revokes grants",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session } = await createSession(runtime);

    for (const trigger of [
      "start_listening",
      "speech_available",
      "utterance_finalized",
      "intent_resolved",
      "auto_approved",
    ]) {
      await runtime.transition(session.id, trigger, { actor: "operator" });
    }

    const stopped = await runtime.emergencyStop(session.id, {
      actor: "operator",
      reason: "safety interlock",
    });
    assert.equal(stopped.session.state, "EMERGENCY_STOPPED");
    assert.equal(stopped.session.killSwitchLatched, true);
    assert.equal(stopped.session.grantsRevoked, true);
    const eventTypes = stopped.events.map((event) => event.type);
    assert.ok(eventTypes.includes("emergency.stop"));
    assert.ok(eventTypes.includes("session.ended"));

    await assert.rejects(
      runtime.transition(session.id, "start_listening", { actor: "operator" }),
      /No outbound transitions from terminal state/,
    );
    await pool.end();
  },
);

integrationTest(
  "ordinary cancellation routes to CANCELLED, not EMERGENCY_STOPPED",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session } = await createSession(runtime);

    await runtime.transition(session.id, "start_listening", {
      actor: "operator",
    });
    await runtime.transition(session.id, "speech_available", {
      actor: "operator",
    });
    const cancelled = await runtime.cancelSession(session.id, {
      actor: "operator",
      reason: "operator reject",
    });
    assert.equal(cancelled.session.state, "CANCELLED");
    assert.equal(cancelled.session.killSwitchLatched, false);
    const emergencyEvents = cancelled.events.filter(
      (event) => event.type === "emergency.stop",
    );
    assert.equal(emergencyEvents.length, 0);
    await pool.end();
  },
);

integrationTest(
  "plan approval routes AWAITING_APPROVAL → EXECUTING; reject → CANCELLED",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });

    // Approved flow
    const approvedSession = await createSession(runtime);
    for (const trigger of [
      "start_listening",
      "speech_available",
      "utterance_finalized",
      "intent_resolved",
    ]) {
      await runtime.transition(approvedSession.session.id, trigger, {
        actor: "operator",
      });
    }
    const plan = await runtime.createPlan({
      sessionId: approvedSession.session.id,
      intent: "publish",
      policyVerdict: "approval_required",
      estimatedCost: 0.5,
      steps: [
        { stepId: "s1", tool: "facebook_publish", args: {}, risk: "high" },
      ],
    });
    assert.equal(plan.session.state, "AWAITING_APPROVAL");
    const approved = await runtime.approvePlan(plan.plan.id, {
      actor: "operator",
      actorId: "user-1",
    });
    assert.equal(approved.session.state, "EXECUTING");
    assert.equal(approved.plan.status, "approved");
    const approvedPlan = await runtime.getPlan(plan.plan.id);
    assert.equal(approvedPlan.steps.length, 1);
    assert.equal(approvedPlan.steps[0].tool, "facebook_publish");

    // Rejected flow
    const rejectedSession = await createSession(runtime);
    for (const trigger of [
      "start_listening",
      "speech_available",
      "utterance_finalized",
      "intent_resolved",
    ]) {
      await runtime.transition(rejectedSession.session.id, trigger, {
        actor: "operator",
      });
    }
    const rejectedPlan = await runtime.createPlan({
      sessionId: rejectedSession.session.id,
      intent: "publish",
      policyVerdict: "approval_required",
      estimatedCost: 0.5,
      steps: [
        { stepId: "s1", tool: "facebook_publish", args: {}, risk: "high" },
      ],
    });
    const rejected = await runtime.rejectPlan(rejectedPlan.plan.id, {
      actor: "operator",
      actorId: "user-2",
      reason: "not on brand",
    });
    assert.equal(rejected.session.state, "CANCELLED");
    assert.equal(rejected.plan.status, "rejected");
    await pool.end();
  },
);

integrationTest(
  "tool executions are idempotent per (session, generation, key)",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRepository,
    } = require("../src/repositories/operatorRepository");
    const repo = new OperatorRepository(pool);
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session } = await createSession(runtime);

    const key = `publish-step-1`;
    const first = await repo.recordToolExecution({
      sessionId: session.id,
      generation: session.generation,
      planId: null,
      stepId: null,
      tool: "facebook_publish",
      action: "publish",
      args: { message: "hi" },
      risk: "high",
      approval: "approved",
      idempotencyKey: key,
    });
    const second = await repo.recordToolExecution({
      sessionId: session.id,
      generation: session.generation,
      planId: null,
      stepId: null,
      tool: "facebook_publish",
      action: "publish",
      args: { message: "hi" },
      risk: "high",
      approval: "approved",
      idempotencyKey: key,
    });
    assert.equal(
      second.id,
      first.id,
      "replay must return the stored execution",
    );

    // Same key in a different session never collides.
    const other = await createSession(runtime);
    const third = await repo.recordToolExecution({
      sessionId: other.session.id,
      generation: other.session.generation,
      planId: null,
      stepId: null,
      tool: "facebook_publish",
      action: "publish",
      args: {},
      risk: "high",
      approval: "approved",
      idempotencyKey: key,
    });
    assert.notEqual(third.id, first.id);

    const finished = await repo.finishToolExecution(first.id, {
      status: "succeeded",
      response: { permalink: "https://fb.com/1" },
      durationMs: 120,
    });
    assert.equal(finished.status, "succeeded");
    assert.equal(finished.response.permalink, "https://fb.com/1");
    await pool.end();
  },
);

integrationTest(
  "SSE resume via eventsAfter replays without gaps or duplicates",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session } = await createSession(runtime);
    const total = 1 + 5;
    for (const trigger of [
      "start_listening",
      "speech_available",
      "utterance_finalized",
      "intent_resolved",
      "require_approval",
    ]) {
      await runtime.transition(session.id, trigger, { actor: "operator" });
    }

    const fromStart = await runtime.eventsAfter(session.id, 0);
    assert.equal(fromStart.length, total);
    const last = fromStart[fromStart.length - 1].sequence_id;

    const afterLast = await runtime.eventsAfter(session.id, last);
    assert.equal(afterLast.length, 0, "no duplicates past the last sequence");

    const mid = await runtime.eventsAfter(session.id, 2);
    assert.equal(mid.length, total - 2);
    assert.equal(mid[0].sequence_id, 3);
    assert.equal(mid[0].payload.from, "LISTENING"); // speech_available event
    await pool.end();
  },
);
