const assert = require("node:assert/strict");
const test = require("node:test");

test("monitoring classifies mentions and normalizes sentiment to 0-100", () => {
  const { analyzeMention } = require("../src/domain/monitoring");
  const complaint = analyzeMention({
    id: "m1",
    body: "This is broken and I need a refund",
    author: "customer",
  });
  assert.equal(complaint.classification, "complaint");
  assert.ok(complaint.sentiment >= 0 && complaint.sentiment <= 100);
  assert.ok(complaint.replyDraft || complaint.escalation);
  assert.equal(
    analyzeMention({ id: "m2", body: "How can I start?" }).classification,
    "question",
  );
  assert.equal(
    analyzeMention({ id: "m3", body: "Amazing guide, thank you!" })
      .classification,
    "praise",
  );
  assert.equal(
    analyzeMention({ id: "m4", body: "BUY NOW FREE CRYPTO http://spam.test" })
      .classification,
    "spam",
  );
  assert.equal(
    analyzeMention({ id: "m5", body: "Can your team help our business?" })
      .classification,
    "lead",
  );
});

test("alert evaluation covers defaults and emits stable deduplication keys", () => {
  const { evaluateAlerts } = require("../src/domain/monitoring");
  const snapshot = {
    brandId: "brand-zato",
    period: "2026-08-14T13:00Z",
    volume: 250,
    baselineVolume: 100,
    sentiment: 35,
    baselineSentiment: 70,
    viralNegativeReach: 50000,
    competitorPricingMentions: 4,
    influencerMentions: 2,
    overdueCriticalReplies: 1,
  };
  const first = evaluateAlerts(snapshot);
  const repeated = evaluateAlerts(snapshot);
  assert.deepEqual(first.map((alert) => alert.type).sort(), [
    "competitor_pricing_mention",
    "creator_influencer_mention",
    "overdue_critical_reply",
    "sentiment_deterioration",
    "viral_negative_content",
    "volume_spike",
  ]);
  assert.deepEqual(
    first.map((alert) => alert.dedupeKey),
    repeated.map((alert) => alert.dedupeKey),
  );
});
