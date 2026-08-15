"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const {
  IDLE,
  ACTIVE_STATES,
  PAUSABLE_STATES,
  RECOVERY_STATES,
  TERMINAL_STATES,
  NON_TERMINAL_STATES,
  transitionOperatorState,
  pauseRequestPolicy,
  isValidResumeState,
  isValidRecoveryTarget,
  OperatorTransitionError,
} = require("../src/domain/operatorStateMachine");

test("state groups match the spec §3.3 definitions", () => {
  assert.equal(IDLE, "IDLE");
  assert.deepEqual(ACTIVE_STATES, [
    "LISTENING",
    "TRANSCRIBING",
    "THINKING",
    "PLANNING",
    "AWAITING_APPROVAL",
    "EXECUTING",
    "VERIFYING",
    "SPEAKING",
    "DEGRADED",
  ]);
  assert.deepEqual(PAUSABLE_STATES, [
    "AWAITING_APPROVAL",
    "EXECUTING",
    "VERIFYING",
    "DEGRADED",
  ]);
  assert.deepEqual(RECOVERY_STATES, ["RECOVERING", "REAUTHORIZING"]);
  assert.deepEqual(TERMINAL_STATES, [
    "FAILED",
    "CANCELLED",
    "EMERGENCY_STOPPED",
  ]);
  for (const state of NON_TERMINAL_STATES) {
    assert.ok(
      !TERMINAL_STATES.includes(state),
      `${state} must be non-terminal`,
    );
  }
});

test("happy-path voice chain: IDLE → ... → SPEAKING → IDLE", () => {
  const flow = [
    ["IDLE", "start_listening", "LISTENING"],
    ["LISTENING", "speech_available", "TRANSCRIBING"],
    ["TRANSCRIBING", "utterance_finalized", "THINKING"],
    ["THINKING", "intent_resolved", "PLANNING"],
    ["PLANNING", "require_approval", "AWAITING_APPROVAL"],
    ["AWAITING_APPROVAL", "approve", "EXECUTING"],
    ["EXECUTING", "step_completed", "VERIFYING"],
    ["VERIFYING", "all_verified", "SPEAKING"],
    ["SPEAKING", "tts_completed", "IDLE"],
  ];
  for (const [from, trigger, to] of flow) {
    assert.equal(
      transitionOperatorState({ state: from, trigger }).to,
      to,
      `${from} -(${trigger})-> ${to}`,
    );
  }
});

test("PLANNING can auto-approve low-risk allowlisted plans to EXECUTING", () => {
  assert.equal(
    transitionOperatorState({ state: "PLANNING", trigger: "auto_approved" }).to,
    "EXECUTING",
  );
});

test("PLANNING and AWAITING_APPROVAL timeout/reject route to CANCELLED, never EMERGENCY_STOPPED", () => {
  assert.equal(
    transitionOperatorState({ state: "PLANNING", trigger: "plan_rejected" }).to,
    "CANCELLED",
  );
  assert.equal(
    transitionOperatorState({ state: "PLANNING", trigger: "plan_timeout" }).to,
    "CANCELLED",
  );
  assert.equal(
    transitionOperatorState({ state: "AWAITING_APPROVAL", trigger: "reject" })
      .to,
    "CANCELLED",
  );
  assert.equal(
    transitionOperatorState({
      state: "AWAITING_APPROVAL",
      trigger: "approval_timeout",
    }).to,
    "CANCELLED",
  );
});

test("EXECUTING retries within EXECUTING then exhausts to FAILED", () => {
  const retried = transitionOperatorState({
    state: "EXECUTING",
    trigger: "step_timeout",
    context: { attempt: 1, maxAttempts: 3 },
  });
  assert.equal(retried.to, "EXECUTING");
  assert.equal(retried.exhausted, false);

  const exhausted = transitionOperatorState({
    state: "EXECUTING",
    trigger: "step_timeout",
    context: { attempt: 3, maxAttempts: 3 },
  });
  assert.equal(exhausted.to, "FAILED");
  assert.equal(exhausted.exhausted, true);
});

test("VERIFYING retries to EXECUTING while budget remains, else FAILED", () => {
  const retry = transitionOperatorState({
    state: "VERIFYING",
    trigger: "verify_retry",
    context: { attempt: 1, maxAttempts: 3 },
  });
  assert.equal(retry.to, "EXECUTING");
  const exhausted = transitionOperatorState({
    state: "VERIFYING",
    trigger: "verify_retry",
    context: { attempt: 3, maxAttempts: 3 },
  });
  assert.equal(exhausted.to, "FAILED");
  assert.equal(
    transitionOperatorState({ state: "VERIFYING", trigger: "verify_failed" })
      .to,
    "FAILED",
  );
  assert.equal(
    transitionOperatorState({ state: "VERIFYING", trigger: "verify_timeout" })
      .to,
    "FAILED",
  );
});

test("SPEAKING failure and timeout return to IDLE without replaying tools", () => {
  assert.equal(
    transitionOperatorState({ state: "SPEAKING", trigger: "tts_failed" }).to,
    "IDLE",
  );
  assert.equal(
    transitionOperatorState({ state: "SPEAKING", trigger: "tts_cancel" }).to,
    "IDLE",
  );
});

test("terminal states have no outbound transitions", () => {
  for (const state of TERMINAL_STATES) {
    for (const trigger of [
      "start_listening",
      "pause",
      "resume_requested",
      "cancel",
      "emergency_stop",
    ]) {
      assert.throws(
        () => transitionOperatorState({ state, trigger }),
        OperatorTransitionError,
        `${state} must reject ${trigger}`,
      );
    }
  }
});

test("kill switch routes ONLY to EMERGENCY_STOPPED from any non-terminal state", () => {
  for (const state of NON_TERMINAL_STATES) {
    const result = transitionOperatorState({
      state,
      trigger: "emergency_stop",
    });
    assert.equal(result.to, "EMERGENCY_STOPPED", `${state} emergency_stop`);
  }
});

test("pause is legal only from PAUSABLE_STATES ∪ RECOVERY_STATES", () => {
  for (const state of [...PAUSABLE_STATES, ...RECOVERY_STATES]) {
    assert.equal(
      transitionOperatorState({ state, trigger: "pause" }).to,
      "PAUSED",
      `${state} pause`,
    );
  }
  for (const state of [
    IDLE,
    "LISTENING",
    "TRANSCRIBING",
    "THINKING",
    "PLANNING",
    "SPEAKING",
  ]) {
    assert.throws(
      () => transitionOperatorState({ state, trigger: "pause" }),
      OperatorTransitionError,
      `${state} must reject direct pause`,
    );
  }
});

test("pause from a pausable state checkpoints previous_state and resume_state", () => {
  const result = transitionOperatorState({
    state: "EXECUTING",
    trigger: "pause",
  });
  assert.equal(result.to, "PAUSED");
  assert.equal(result.checkpoint.previousState, "EXECUTING");
  assert.equal(result.checkpoint.resumeState, "EXECUTING");
});

test("pause from RECOVERY_STATES preserves the original resume_state", () => {
  const fromRecovering = transitionOperatorState({
    state: "RECOVERING",
    trigger: "pause",
    context: { resumeState: "EXECUTING" },
  });
  assert.equal(fromRecovering.to, "PAUSED");
  assert.equal(fromRecovering.checkpoint.previousState, "RECOVERING");
  assert.equal(fromRecovering.checkpoint.resumeState, "EXECUTING");

  const fromReauth = transitionOperatorState({
    state: "REAUTHORIZING",
    trigger: "pause",
    context: { resumeState: "AWAITING_APPROVAL" },
  });
  assert.equal(fromReauth.checkpoint.previousState, "REAUTHORIZING");
  assert.equal(fromReauth.checkpoint.resumeState, "AWAITING_APPROVAL");
});

test("resume drives PAUSED → REAUTHORIZING → RECOVERING → persisted resume_state", () => {
  const paused = transitionOperatorState({
    state: "EXECUTING",
    trigger: "pause",
  });
  const resumeState = paused.checkpoint.resumeState;
  const reauth = transitionOperatorState({
    state: "PAUSED",
    trigger: "resume_requested",
    context: { resumeState },
  });
  assert.equal(reauth.to, "REAUTHORIZING");
  assert.equal(reauth.checkpoint.resumeState, resumeState);

  const recovering = transitionOperatorState({
    state: "REAUTHORIZING",
    trigger: "reauth_granted",
    context: { resumeState },
  });
  assert.equal(recovering.to, "RECOVERING");
  assert.equal(recovering.checkpoint.resumeState, resumeState);

  const completed = transitionOperatorState({
    state: "RECOVERING",
    trigger: "checkpoint_validated",
    context: { resumeState },
  });
  assert.equal(completed.to, "EXECUTING");
  assert.equal(completed.checkpoint.resumeState, "EXECUTING");
});

test("invalid resume_state routes RECOVERING to FAILED (checkpoint corrupt)", () => {
  for (const invalid of [
    undefined,
    null,
    "PLANNING",
    "THINKING",
    "RECOVERING",
    "IDLE",
  ]) {
    const result = transitionOperatorState({
      state: "RECOVERING",
      trigger: "checkpoint_validated",
      context: { resumeState: invalid },
    });
    assert.equal(result.to, "FAILED", `resume_state=${invalid}`);
    assert.equal(result.checkpointCorrupt, true);
  }
});

test("DEGRADED recovers to persisted previous_state, never guessed", () => {
  const result = transitionOperatorState({
    state: "DEGRADED",
    trigger: "recovered",
    context: { previousState: "EXECUTING" },
  });
  assert.equal(result.to, "EXECUTING");
  const invalid = transitionOperatorState({
    state: "DEGRADED",
    trigger: "recovered",
    context: { previousState: "DEGRADED" },
  });
  assert.equal(invalid.to, "FAILED");
});

test("degrade is legal from ACTIVE states only", () => {
  assert.equal(
    transitionOperatorState({ state: "EXECUTING", trigger: "degrade" }).to,
    "DEGRADED",
  );
  assert.throws(
    () => transitionOperatorState({ state: IDLE, trigger: "degrade" }),
    OperatorTransitionError,
  );
  assert.throws(
    () => transitionOperatorState({ state: "PAUSED", trigger: "degrade" }),
    OperatorTransitionError,
  );
});

test("hard_failure routes ACTIVE ∪ RECOVERY to FAILED only", () => {
  assert.equal(
    transitionOperatorState({ state: "EXECUTING", trigger: "hard_failure" }).to,
    "FAILED",
  );
  assert.equal(
    transitionOperatorState({ state: "RECOVERING", trigger: "hard_failure" })
      .to,
    "FAILED",
  );
  assert.throws(
    () => transitionOperatorState({ state: IDLE, trigger: "hard_failure" }),
    OperatorTransitionError,
  );
});

test("cancel is legal from PAUSED and ACTIVE ∪ RECOVERY, not from IDLE", () => {
  assert.equal(
    transitionOperatorState({ state: "PAUSED", trigger: "cancel" }).to,
    "CANCELLED",
  );
  assert.equal(
    transitionOperatorState({ state: "AWAITING_APPROVAL", trigger: "cancel" })
      .to,
    "CANCELLED",
  );
  assert.throws(
    () => transitionOperatorState({ state: IDLE, trigger: "cancel" }),
    OperatorTransitionError,
  );
});

test("pauseRequestPolicy is deterministic per non-pausable state", () => {
  assert.deepEqual(pauseRequestPolicy("LISTENING"), {
    behavior: "cancel",
    to: "IDLE",
    trigger: "mic_cancel",
  });
  assert.deepEqual(pauseRequestPolicy("TRANSCRIBING"), {
    behavior: "cancel",
    to: "IDLE",
    trigger: "stt_cancel",
  });
  assert.deepEqual(pauseRequestPolicy("SPEAKING"), {
    behavior: "cancel",
    to: "IDLE",
    trigger: "tts_cancel",
  });
  assert.deepEqual(pauseRequestPolicy("THINKING"), { behavior: "defer" });
  assert.deepEqual(pauseRequestPolicy("PLANNING"), { behavior: "defer" });
  for (const state of PAUSABLE_STATES) {
    assert.deepEqual(pauseRequestPolicy(state), { behavior: "pause" });
  }
  for (const state of RECOVERY_STATES) {
    assert.deepEqual(pauseRequestPolicy(state), { behavior: "pause" });
  }
  assert.deepEqual(pauseRequestPolicy(IDLE), { behavior: "none" });
  assert.deepEqual(pauseRequestPolicy("FAILED"), { behavior: "none" });
});

test("deterministic pause-cancel transitions to IDLE create no checkpoint", () => {
  for (const [state, trigger] of [
    ["LISTENING", "mic_cancel"],
    ["TRANSCRIBING", "stt_cancel"],
    ["SPEAKING", "tts_cancel"],
  ]) {
    const result = transitionOperatorState({ state, trigger });
    assert.equal(result.to, "IDLE");
    assert.equal(result.checkpoint.resumeState, null);
  }
});

test("checkpoint validation helpers enforce the contract", () => {
  assert.equal(isValidResumeState("EXECUTING"), true);
  assert.equal(isValidResumeState("AWAITING_APPROVAL"), true);
  assert.equal(isValidResumeState("THINKING"), false);
  assert.equal(isValidResumeState("RECOVERING"), false);
  assert.equal(isValidResumeState(null), false);
  assert.equal(isValidRecoveryTarget("EXECUTING"), true);
  assert.equal(isValidRecoveryTarget("DEGRADED"), false);
  assert.equal(isValidRecoveryTarget("IDLE"), false);
});

test("unknown states and triggers are rejected", () => {
  assert.throws(
    () => transitionOperatorState({ state: "UNKNOWN", trigger: "x" }),
    OperatorTransitionError,
  );
  assert.throws(
    () => transitionOperatorState({ state: "IDLE", trigger: "not_a_trigger" }),
    OperatorTransitionError,
  );
});
