function evaluateAutopilot(context) {
  if (!context.autoPilot)
    return { allowed: false, reasons: ["human_approval_required"] };
  const reasons = [];
  if (context.killSwitch) reasons.push("emergency_kill_switch_active");
  if (!Number.isFinite(context.qaScore) || context.qaScore < 90)
    reasons.push("qa_score_below_auto_pass_threshold");
  if (!context.platformPermitted) reasons.push("platform_permission_missing");
  if (
    !Number.isFinite(context.estimatedCost) ||
    !Number.isFinite(context.remainingBudget) ||
    context.estimatedCost > context.remainingBudget
  ) {
    reasons.push("budget_cap_exceeded");
  }
  if (
    !Number.isInteger(context.postsInWindow) ||
    !Number.isInteger(context.postingFrequencyCap) ||
    context.postsInWindow >= context.postingFrequencyCap
  ) {
    reasons.push("posting_frequency_cap_reached");
  }
  if (!context.claimsSubstantiated)
    reasons.push("claim_substantiation_required");
  if (!context.copyrightCleared) reasons.push("copyright_clearance_required");
  return { allowed: reasons.length === 0, reasons };
}

module.exports = { evaluateAutopilot };
