const DIMENSIONS = [
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

function evaluateArtifact(checks, { autoPilot = false } = {}) {
  if (!checks || DIMENSIONS.some((dimension) => !checks[dimension])) {
    throw new Error("All 12 QA dimensions are required");
  }
  const breakdown = DIMENSIONS.map((dimension) => {
    const check = checks[dimension];
    return {
      dimension,
      passed: check.passed === true,
      points: check.passed === true ? 100 / DIMENSIONS.length : 0,
      reason: check.reason || null,
      remediation: check.remediation || null,
    };
  });
  const score = Math.round(
    breakdown.reduce((total, item) => total + item.points, 0),
  );
  const failed = breakdown.filter((item) => !item.passed);
  const route =
    score < 70
      ? "block"
      : score >= 90 && autoPilot
        ? "auto_pass"
        : "human_review";
  return {
    score,
    route,
    breakdown,
    reasons: failed.map((item) => item.reason).filter(Boolean),
    remediation: failed.map((item) => item.remediation).filter(Boolean),
  };
}

module.exports = { DIMENSIONS, evaluateArtifact };
