"use strict";

/**
 * Z.A.R.V.I.S. operator state machine — spec §3.3.
 *
 * State groups (no bare `any` rules):
 *   IDLE
 *   ACTIVE_STATES   = LISTENING, TRANSCRIBING, THINKING, PLANNING,
 *                     AWAITING_APPROVAL, EXECUTING, VERIFYING, SPEAKING, DEGRADED
 *   PAUSABLE_STATES = AWAITING_APPROVAL, EXECUTING, VERIFYING, DEGRADED
 *   RECOVERY_STATES = RECOVERING, REAUTHORIZING
 *   PAUSED
 *   TERMINAL_STATES = FAILED, CANCELLED, EMERGENCY_STOPPED
 *
 * Invariants enforced here:
 *   - TERMINAL_STATES have no outbound transitions.
 *   - EMERGENCY_STOPPED is reachable from any NON_TERMINAL state only via
 *     `emergency_stop`; ordinary cancellation routes to CANCELLED.
 *   - Pause is only legal from PAUSABLE_STATES ∪ RECOVERY_STATES; pause during
 *     non-pausable states is handled deterministically by `pauseRequestPolicy`.
 *   - RECOVERING resumes only a validated `resume_state` ∈ PAUSABLE_STATES;
 *     invalid checkpoints route to FAILED.
 *   - DEGRADED recovers only to the persisted `previous_state` (a prior ACTIVE
 *     state) — never guessed.
 */

const IDLE = "IDLE";

const ACTIVE_STATES = Object.freeze([
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

const PAUSABLE_STATES = Object.freeze([
  "AWAITING_APPROVAL",
  "EXECUTING",
  "VERIFYING",
  "DEGRADED",
]);

const RECOVERY_STATES = Object.freeze(["RECOVERING", "REAUTHORIZING"]);

const TERMINAL_STATES = Object.freeze([
  "FAILED",
  "CANCELLED",
  "EMERGENCY_STOPPED",
]);

const NON_TERMINAL_STATES = Object.freeze([
  IDLE,
  ...ACTIVE_STATES,
  ...RECOVERY_STATES,
  "PAUSED",
]);

const ALL_STATES = Object.freeze([...NON_TERMINAL_STATES, ...TERMINAL_STATES]);

// Sentinel targets resolved from the persisted checkpoint at runtime.
const RESUME_STATE = Symbol("resume_state");
const PREVIOUS_STATE = Symbol("previous_state");

// Static transition table. Dynamic targets (RESUME_STATE / PREVIOUS_STATE) are
// resolved by transitionOperatorState from the checkpoint context.
const TRANSITIONS = {
  IDLE: { start_listening: "LISTENING" },
  LISTENING: {
    speech_available: "TRANSCRIBING",
    no_speech: "IDLE",
    stt_timeout: "IDLE", // STT first-token budget exceeded, retries exhausted
    listening_idle_timeout: "IDLE",
    mic_cancel: "IDLE", // deterministic pause-cancel (mic capture aborted)
  },
  TRANSCRIBING: {
    utterance_finalized: "THINKING",
    stt_failed: "DEGRADED",
    stt_cancel: "IDLE", // deterministic pause-cancel (STT aborted)
  },
  THINKING: {
    intent_resolved: "PLANNING",
    intent_timeout: "FAILED", // intent budget 3s, re-route exhausted
  },
  PLANNING: {
    require_approval: "AWAITING_APPROVAL",
    auto_approved: "EXECUTING",
    plan_rejected: "CANCELLED",
    plan_timeout: "CANCELLED",
  },
  AWAITING_APPROVAL: {
    approve: "EXECUTING",
    policy_override: "EXECUTING",
    reject: "CANCELLED",
    approval_timeout: "CANCELLED",
  },
  EXECUTING: {
    step_completed: "VERIFYING",
    step_failed: "FAILED", // non-retryable error
    step_timeout: "EXECUTING", // retried within EXECUTING; exhausted → FAILED
  },
  VERIFYING: {
    all_verified: "SPEAKING",
    verify_retry: "EXECUTING", // postcondition unmet, retry budget left
    verify_failed: "FAILED", // postcondition unmet, retries exhausted
    verify_timeout: "FAILED",
  },
  SPEAKING: {
    tts_completed: "IDLE",
    tts_failed: "IDLE",
    tts_cancel: "IDLE", // deterministic pause-cancel (TTS aborted)
  },
  DEGRADED: {
    recovered: PREVIOUS_STATE,
    degrade_failed: "FAILED",
  },
  PAUSED: {
    resume_requested: "REAUTHORIZING",
    cancel: "CANCELLED",
    session_timeout: "CANCELLED",
  },
  REAUTHORIZING: {
    reauth_granted: "RECOVERING",
    reauth_denied: "CANCELLED",
    reauth_timeout: "CANCELLED",
  },
  RECOVERING: {
    checkpoint_validated: RESUME_STATE,
    checkpoint_invalid: "FAILED",
    recovery_timeout: "FAILED",
  },
};

class OperatorTransitionError extends Error {
  constructor(message, details) {
    super(message);
    this.name = "OperatorTransitionError";
    this.code = "INVALID_TRANSITION";
    if (details) this.details = details;
  }
}

function isActive(state) {
  return ACTIVE_STATES.includes(state);
}

function isPausable(state) {
  return PAUSABLE_STATES.includes(state);
}

function isRecovery(state) {
  return RECOVERY_STATES.includes(state);
}

function isTerminal(state) {
  return TERMINAL_STATES.includes(state);
}

function isNonTerminal(state) {
  return NON_TERMINAL_STATES.includes(state);
}

function isKnownState(state) {
  return ALL_STATES.includes(state);
}

/** resume_state must be a PAUSABLE state; anything else is a corrupt checkpoint. */
function isValidResumeState(resumeState) {
  return isPausable(resumeState);
}

/** DEGRADED recovers to a prior ACTIVE state, never to another DEGRADED. */
function isValidRecoveryTarget(previousState) {
  return isActive(previousState) && previousState !== "DEGRADED";
}

/**
 * Deterministic pause policy for non-pausable states (spec §3.3). Returns:
 *   { behavior: "pause" }            — legal pause (pausable / recovery states)
 *   { behavior: "defer" }            — THINKING / PLANNING: apply at next pausable state
 *   { behavior: "cancel", to }       — LISTENING / TRANSCRIBING / SPEAKING → IDLE
 *   { behavior: "none" }             — IDLE or terminal (no-op)
 */
function pauseRequestPolicy(state) {
  if (state === IDLE || isTerminal(state)) return { behavior: "none" };
  if (isPausable(state) || isRecovery(state)) return { behavior: "pause" };
  switch (state) {
    case "LISTENING":
      return { behavior: "cancel", to: IDLE, trigger: "mic_cancel" };
    case "TRANSCRIBING":
      return { behavior: "cancel", to: IDLE, trigger: "stt_cancel" };
    case "SPEAKING":
      return { behavior: "cancel", to: IDLE, trigger: "tts_cancel" };
    case "THINKING":
    case "PLANNING":
      return { behavior: "defer" };
    default:
      return { behavior: "none" };
  }
}

/**
 * Compute the persisted checkpoint contract for a transition.
 *   previous_state — the state the session entered from.
 *   resume_state   — target on resume; must be ∈ PAUSABLE_STATES when recovered.
 *                    Pause from RECOVERY_STATES preserves the original value;
 *                    it is never recomputed from the recovery state.
 */
function nextCheckpoint(from, to, current = {}) {
  const checkpoint = { previousState: from, resumeState: null };
  if (to === "PAUSED") {
    checkpoint.resumeState = isPausable(from)
      ? from
      : isRecovery(from)
        ? (current.resumeState ?? null)
        : null;
  } else if (to === "DEGRADED") {
    checkpoint.resumeState = current.resumeState ?? null;
  } else if (isRecovery(to)) {
    checkpoint.resumeState = current.resumeState ?? null;
  } else if (isPausable(to) && from === "RECOVERING") {
    checkpoint.resumeState = to; // resumed into a pausable state
  }
  return checkpoint;
}

/**
 * Guarded transition. `context` may carry `{ previousState, resumeState,
 * attempt, maxAttempts }` for dynamic targets and retry bookkeeping.
 * Returns `{ to, checkpoint, exhausted? }` or throws OperatorTransitionError.
 */
function transitionOperatorState({ state, trigger, context = {} }) {
  if (!isKnownState(state)) {
    throw new OperatorTransitionError(`Unknown operator state: ${state}`, {
      state,
    });
  }
  if (isTerminal(state)) {
    throw new OperatorTransitionError(
      `No outbound transitions from terminal state ${state}`,
      { state, trigger },
    );
  }
  if (trigger === "emergency_stop") {
    // Reachable from any NON_TERMINAL state — but only via this trigger.
    return {
      to: "EMERGENCY_STOPPED",
      checkpoint: nextCheckpoint(state, "EMERGENCY_STOPPED", context),
    };
  }
  if (trigger === "pause") {
    if (!isPausable(state) && !isRecovery(state)) {
      throw new OperatorTransitionError(
        `Pause is not legal from ${state}; use pauseRequestPolicy`,
        { state },
      );
    }
    return {
      to: "PAUSED",
      checkpoint: nextCheckpoint(state, "PAUSED", context),
    };
  }
  if (trigger === "cancel") {
    if (state === "PAUSED" || isActive(state) || isRecovery(state)) {
      return {
        to: "CANCELLED",
        checkpoint: nextCheckpoint(state, "CANCELLED", context),
      };
    }
    throw new OperatorTransitionError(`Cancel is not legal from ${state}`, {
      state,
    });
  }
  if (trigger === "hard_failure") {
    if (isActive(state) || isRecovery(state)) {
      return {
        to: "FAILED",
        checkpoint: nextCheckpoint(state, "FAILED", context),
      };
    }
    throw new OperatorTransitionError(
      `Hard failure is not legal from ${state}`,
      {
        state,
      },
    );
  }
  if (trigger === "degrade") {
    if (isActive(state)) {
      return {
        to: "DEGRADED",
        checkpoint: nextCheckpoint(state, "DEGRADED", context),
      };
    }
    throw new OperatorTransitionError(`Degrade is not legal from ${state}`, {
      state,
    });
  }

  const table = TRANSITIONS[state];
  if (!table || !(trigger in table)) {
    throw new OperatorTransitionError(
      `Invalid transition: ${state} -> ${trigger}`,
      {
        state,
        trigger,
      },
    );
  }
  const target = table[trigger];

  if (target === RESUME_STATE) {
    if (!isValidResumeState(context.resumeState)) {
      return {
        to: "FAILED",
        checkpoint: nextCheckpoint(state, "FAILED", context),
        checkpointCorrupt: true,
      };
    }
    return {
      to: context.resumeState,
      checkpoint: nextCheckpoint(state, context.resumeState, context),
    };
  }
  if (target === PREVIOUS_STATE) {
    if (!isValidRecoveryTarget(context.previousState)) {
      return {
        to: "FAILED",
        checkpoint: nextCheckpoint(state, "FAILED", context),
        recoveryTargetInvalid: true,
      };
    }
    return {
      to: context.previousState,
      checkpoint: nextCheckpoint(state, context.previousState, context),
    };
  }
  if (trigger === "step_timeout" && target === "EXECUTING") {
    const attempt = context.attempt ?? 0;
    const maxAttempts = context.maxAttempts ?? 3;
    const exhausted = attempt >= maxAttempts;
    return {
      to: exhausted ? "FAILED" : "EXECUTING",
      checkpoint: nextCheckpoint(
        state,
        exhausted ? "FAILED" : "EXECUTING",
        context,
      ),
      exhausted,
    };
  }
  if (trigger === "verify_retry") {
    const attempt = context.attempt ?? 0;
    const maxAttempts = context.maxAttempts ?? 3;
    const exhausted = attempt >= maxAttempts;
    return {
      to: exhausted ? "FAILED" : "EXECUTING",
      checkpoint: nextCheckpoint(
        state,
        exhausted ? "FAILED" : "EXECUTING",
        context,
      ),
      exhausted,
    };
  }
  return {
    to: target,
    checkpoint: nextCheckpoint(state, target, context),
  };
}

module.exports = {
  IDLE,
  ACTIVE_STATES,
  PAUSABLE_STATES,
  RECOVERY_STATES,
  TERMINAL_STATES,
  NON_TERMINAL_STATES,
  ALL_STATES,
  OperatorTransitionError,
  transitionOperatorState,
  pauseRequestPolicy,
  nextCheckpoint,
  isValidResumeState,
  isValidRecoveryTarget,
  isActive,
  isPausable,
  isRecovery,
  isTerminal,
  isNonTerminal,
  isKnownState,
};
