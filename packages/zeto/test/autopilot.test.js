const assert = require("node:assert/strict");
const test = require("node:test");

const safeContext = {
  autoPilot: true,
  killSwitch: false,
  qaScore: 95,
  platformPermitted: true,
  estimatedCost: 0.2,
  remainingBudget: 1,
  postsInWindow: 2,
  postingFrequencyCap: 5,
  claimsSubstantiated: true,
  copyrightCleared: true,
};

test("AUTO-PILOT permits publishing only when every guardrail passes", () => {
  const { evaluateAutopilot } = require("../src/domain/autopilotPolicy");
  assert.deepEqual(evaluateAutopilot(safeContext), {
    allowed: true,
    reasons: [],
  });
  for (const [field, unsafe] of [
    ["killSwitch", true],
    ["qaScore", 89],
    ["platformPermitted", false],
    ["remainingBudget", 0.1],
    ["postsInWindow", 5],
    ["claimsSubstantiated", false],
    ["copyrightCleared", false],
  ]) {
    const result = evaluateAutopilot({ ...safeContext, [field]: unsafe });
    assert.equal(result.allowed, false, field);
    assert.ok(result.reasons.length > 0, field);
  }
});

test("human mode still requires an approval checkpoint", () => {
  const { evaluateAutopilot } = require("../src/domain/autopilotPolicy");
  const result = evaluateAutopilot({ ...safeContext, autoPilot: false });
  assert.equal(result.allowed, false);
  assert.deepEqual(result.reasons, ["human_approval_required"]);
});
