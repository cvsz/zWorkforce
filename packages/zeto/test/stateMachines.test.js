const assert = require("node:assert/strict");
const test = require("node:test");

test("approval state machine rejects bypass transitions", () => {
  const { transitionApproval } = require("../src/domain/approvalStateMachine");
  assert.equal(transitionApproval("pending", "approve"), "approved");
  assert.throws(
    () => transitionApproval("pending", "publish"),
    /invalid approval transition/i,
  );
  assert.throws(
    () => transitionApproval("rejected", "approve"),
    /invalid approval transition/i,
  );
});

test("workflow state machine permits retry but not terminal replay", () => {
  const { transitionWorkflow } = require("../src/domain/workflowStateMachine");
  assert.equal(transitionWorkflow("running", "fail"), "failed");
  assert.equal(transitionWorkflow("failed", "retry"), "running");
  assert.throws(
    () => transitionWorkflow("succeeded", "retry"),
    /invalid workflow transition/i,
  );
});
