"use strict";

/**
 * M12 Z.A.R.V.I.S. Sequence Builder domain — spec §4.3.
 *
 * A sequence is a named, ordered list of steps. Steps run sequentially; each
 * step's output is addressable as `s<N>.result` inside later steps' args
 * (spec §4.3 execution semantics). Steps are idempotent per run via a scoped
 * idempotency key. Partial failure stops the run and offers resume; replay
 * after failure requires operator confirmation for high-risk steps.
 *
 * This slice ships a small set of built-in, read-only intents grounded in real
 * persisted state (the tool gateway slice will register the full catalog).
 * Unsupported intents fail loudly — never silently (§6.1).
 */

/** Built-in read-only intents available to sequences in this slice. */
const BUILTIN_INTENTS = Object.freeze({
  "queue.read": {
    description: "Read the persisted publication queue (status-filterable)",
    risk: "none",
  },
  "session.status": {
    description: "Current operator session snapshot (state, mode, generation)",
    risk: "none",
  },
  "events.recent": {
    description: "Recent canonical events for the operator session",
    risk: "none",
  },
});

const HIGH_RISK = Object.freeze(["high", "critical"]);

function isKnownIntent(intent) {
  return Object.prototype.hasOwnProperty.call(BUILTIN_INTENTS, intent);
}

function intentRisk(intent) {
  return BUILTIN_INTENTS[intent]?.risk ?? "none";
}

function isHighRiskStep(step) {
  const risk = step.risk ?? intentRisk(step.intent);
  return HIGH_RISK.includes(risk);
}

/**
 * Resolve `s<N>.result` references inside a step's args using the results of
 * previously completed steps (spec §4.3: "step outputs addressable
 * (`s<N>.result`)"). References are matched exactly (`s1.result`) at any depth
 * inside args; referencing a step that has not completed yet is a hard error.
 */
function resolveStepArgs(args, resultsById, stepId) {
  const stepRef = /^s(\d+)\.result$/;

  function walk(value) {
    if (typeof value === "string") {
      const match = stepRef.exec(value);
      if (!match) return value;
      const key = `s${match[1]}`;
      if (!Object.prototype.hasOwnProperty.call(resultsById, key)) {
        throw new Error(
          `Step ${stepId} references ${key}.result before that step completed`,
        );
      }
      return resultsById[key];
    }
    if (Array.isArray(value)) return value.map(walk);
    if (value && typeof value === "object") {
      const out = {};
      for (const [k, v] of Object.entries(value)) out[k] = walk(v);
      return out;
    }
    return value;
  }

  return walk(args);
}

module.exports = {
  BUILTIN_INTENTS,
  HIGH_RISK,
  isKnownIntent,
  intentRisk,
  isHighRiskStep,
  resolveStepArgs,
};
