const transitions = {
  queued: { start: "running", cancel: "cancelled" },
  running: {
    succeed: "succeeded",
    fail: "failed",
    pause: "paused",
    cancel: "cancelled",
  },
  paused: { resume: "running", cancel: "cancelled" },
  failed: { retry: "running", cancel: "cancelled" },
};

function transitionWorkflow(state, event) {
  const next = transitions[state]?.[event];
  if (!next)
    throw new Error(`Invalid workflow transition: ${state} -> ${event}`);
  return next;
}

module.exports = { transitionWorkflow };
