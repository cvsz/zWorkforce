const transitions = {
  pending: { approve: "approved", reject: "rejected" },
  approved: { override: "overridden" },
};

function transitionApproval(state, event) {
  const next = transitions[state]?.[event];
  if (!next)
    throw new Error(`Invalid approval transition: ${state} -> ${event}`);
  return next;
}

module.exports = { transitionApproval };
