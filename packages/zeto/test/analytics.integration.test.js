const assert = require("node:assert/strict");
const test = require("node:test");

const databaseUrl = process.env.TEST_DATABASE_URL;
const integrationTest = databaseUrl ? test : test.skip;

integrationTest(
  "daily metrics produce reproducible current and prior-period analytics",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const {
      AnalyticsRepository,
    } = require("../src/repositories/analyticsRepository");
    const pool = createPool({ connectionString: databaseUrl, max: 2 });
    await migrate(pool);
    await pool.query("TRUNCATE brands, metrics_daily CASCADE");
    const brand = (
      await pool.query(
        "INSERT INTO brands(name, niche) VALUES ('zato', 'Niche Content') RETURNING id",
      )
    ).rows[0];
    const analytics = new AnalyticsRepository(pool);
    const now = new Date();
    const yesterday = new Date(now.getTime() - 86400000)
      .toISOString()
      .slice(0, 10);
    const prior = new Date(now.getTime() - 8 * 86400000)
      .toISOString()
      .slice(0, 10);
    await analytics.ingestDaily({
      brandId: brand.id,
      platform: "facebook",
      date: yesterday,
      metrics: { reach: 100, engagement: 25, followers: 10 },
    });
    await analytics.ingestDaily({
      brandId: brand.id,
      platform: "facebook",
      date: prior,
      metrics: { reach: 50, engagement: 5, followers: 4 },
    });

    const report = await analytics.controlRoom(brand.id, { days: 7, now });
    assert.equal(report.empty, false);
    assert.equal(report.kpis.reach.current, 100);
    assert.equal(report.kpis.reach.prior, 50);
    assert.equal(report.kpis.reach.deltaPercent, 100);
    assert.equal(report.kpis.engagement.current, 25);
    assert.equal(report.definition.periodDays, 7);
    assert.match(report.definition.source, /metrics_daily/);
    await pool.end();
  },
);

integrationTest(
  "mention ingestion persists sentiment and complaint escalation SLA",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const {
      MonitoringRepository,
    } = require("../src/repositories/monitoringRepository");
    const pool = createPool({ connectionString: databaseUrl, max: 2 });
    await migrate(pool);
    await pool.query("TRUNCATE brands, mentions CASCADE");
    const brand = (
      await pool.query(
        "INSERT INTO brands(name, niche) VALUES ('zato', 'Niche Content') RETURNING id",
      )
    ).rows[0];
    const monitoring = new MonitoringRepository(pool);
    const result = await monitoring.ingest({
      brandId: brand.id,
      platform: "facebook",
      externalId: `mention-${Date.now()}`,
      body: "Terrible, broken and not working",
      occurredAt: new Date().toISOString(),
    });
    assert.equal(result.mention.classification, "complaint");
    assert.equal(Number(result.sentiment.score), 0);
    assert.equal(result.escalation.severity, "critical");
    assert.ok(result.escalation.reply_draft);
    assert.ok(new Date(result.escalation.due_at) > new Date());
    await pool.end();
  },
);

integrationTest(
  "alerts deduplicate and labelled outcomes produce precision evidence",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const { AlertRepository } = require("../src/repositories/alertRepository");
    const pool = createPool({ connectionString: databaseUrl, max: 2 });
    await migrate(pool);
    await pool.query("TRUNCATE brands, alerts CASCADE");
    const brand = (
      await pool.query(
        "INSERT INTO brands(name, niche) VALUES ('zato', 'Niche Content') RETURNING id",
      )
    ).rows[0];
    const alerts = new AlertRepository(pool);
    const snapshot = {
      brandId: brand.id,
      period: "2026-08-14T14",
      volume: 20,
      baselineVolume: 5,
      sentiment: 60,
      baselineSentiment: 60,
      viralNegativeReach: 0,
      competitorPricingMentions: 0,
      influencerMentions: 0,
      overdueCriticalReplies: 0,
    };
    const first = await alerts.evaluate(snapshot);
    const replay = await alerts.evaluate(snapshot);
    assert.equal(first.length, 1);
    assert.equal(replay[0].id, first[0].id);
    await alerts.label(first[0].id, true, null, "confirmed spike");
    const quality = await alerts.quality();
    assert.deepEqual(quality, {
      labelled: 1,
      truePositive: 1,
      falsePositive: 0,
      precision: 1,
      falseNegative: 0,
      recall: 1,
    });
    await pool.end();
  },
);
