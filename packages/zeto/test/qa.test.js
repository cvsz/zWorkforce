const assert = require("node:assert/strict");
const test = require("node:test");

const dimensions = [
  "brand_palette",
  "font_policy",
  "logo_rule",
  "claim_substantiation",
  "platform_policy",
  "copyright_clearance",
  "text_length",
  "safe_margins",
  "alt_text",
  "hashtag_risk",
  "sentiment_risk",
  "cta_presence",
];

test("QA returns a visible 12-point breakdown and requires review without AUTO_PILOT", () => {
  const { evaluateArtifact } = require("../src/domain/qaScorer");
  const result = evaluateArtifact(
    Object.fromEntries(dimensions.map((name) => [name, { passed: true }])),
    { autoPilot: false },
  );
  assert.equal(result.score, 100);
  assert.equal(result.route, "human_review");
  assert.equal(result.breakdown.length, 12);
  assert.deepEqual(result.reasons, []);
});

test("QA auto-passes scores of at least 90 only with AUTO_PILOT", () => {
  const { evaluateArtifact } = require("../src/domain/qaScorer");
  const checks = Object.fromEntries(
    dimensions.map((name) => [name, { passed: true }]),
  );
  checks.cta_presence = {
    passed: false,
    reason: "CTA missing",
    remediation: "Add a clear CTA",
  };
  const result = evaluateArtifact(checks, { autoPilot: true });
  assert.equal(result.score, 92);
  assert.equal(result.route, "auto_pass");
  assert.deepEqual(result.reasons, ["CTA missing"]);
  assert.deepEqual(result.remediation, ["Add a clear CTA"]);
});

test("QA blocks scores below 70 and rejects incomplete check sets", () => {
  const { evaluateArtifact } = require("../src/domain/qaScorer");
  const checks = Object.fromEntries(
    dimensions.map((name, index) => [
      name,
      index < 8
        ? {
            passed: false,
            reason: `${name} failed`,
            remediation: `Fix ${name}`,
          }
        : { passed: true },
    ]),
  );
  const result = evaluateArtifact(checks, { autoPilot: true });
  assert.equal(result.route, "block");
  assert.ok(result.score < 70);
  assert.equal(result.reasons.length, 8);
  assert.throws(
    () => evaluateArtifact({ brand_palette: { passed: true } }),
    /all 12 QA dimensions/i,
  );
});
