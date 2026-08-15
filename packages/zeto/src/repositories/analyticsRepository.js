const METRIC_NAMES = ["followers", "reach", "engagement"];

class AnalyticsRepository {
  constructor(pool) {
    this.pool = pool;
  }

  async ingestDaily({
    brandId,
    publicationId = null,
    platform,
    date,
    metrics,
  }) {
    for (const name of METRIC_NAMES) {
      if (
        metrics[name] != null &&
        (!Number.isFinite(metrics[name]) || metrics[name] < 0)
      ) {
        throw new Error(`Invalid ${name} metric`);
      }
    }
    const base = [
      brandId,
      publicationId,
      platform,
      date,
      JSON.stringify(metrics),
    ];
    const conflict = publicationId
      ? "ON CONFLICT (brand_id, publication_id, platform, metric_date) DO UPDATE"
      : "ON CONFLICT (brand_id, platform, metric_date) WHERE publication_id IS NULL DO UPDATE";
    const result = await this.pool.query(
      `INSERT INTO metrics_daily(brand_id, publication_id, platform, metric_date, metrics)
       VALUES ($1, $2, $3, $4, $5)
       ${conflict} SET metrics = EXCLUDED.metrics, updated_at = now()
       RETURNING *`,
      base,
    );
    return result.rows[0];
  }

  async controlRoom(brandId, { days = 30, now = new Date() } = {}) {
    if (!Number.isInteger(days) || days < 1 || days > 365)
      throw new Error("Invalid analytics period");
    const end = new Date(now);
    end.setUTCHours(0, 0, 0, 0);
    end.setUTCDate(end.getUTCDate() + 1);
    const currentStart = new Date(end.getTime() - days * 86400000);
    const priorStart = new Date(currentStart.getTime() - days * 86400000);
    const totals = await this.pool.query(
      `SELECT period,
         COALESCE(sum((metrics->>'followers')::numeric), 0) AS followers,
         COALESCE(sum((metrics->>'reach')::numeric), 0) AS reach,
         COALESCE(sum((metrics->>'engagement')::numeric), 0) AS engagement,
         count(*)::integer AS samples
       FROM (
         SELECT metrics,
           CASE WHEN metric_date >= $2::date THEN 'current' ELSE 'prior' END AS period
         FROM metrics_daily
         WHERE brand_id = $1 AND metric_date >= $3::date AND metric_date < $4::date
       ) periods GROUP BY period`,
      [brandId, currentStart, priorStart, end],
    );
    const periods = Object.fromEntries(
      totals.rows.map((row) => [row.period, row]),
    );
    const current = periods.current || {};
    const prior = periods.prior || {};
    const kpis = {};
    for (const metric of METRIC_NAMES) {
      const currentValue = Number(current[metric] || 0);
      const priorValue = Number(prior[metric] || 0);
      kpis[metric] = {
        current: currentValue,
        prior: priorValue,
        delta: currentValue - priorValue,
        deltaPercent: priorValue
          ? ((currentValue - priorValue) / priorValue) * 100
          : null,
      };
    }
    return {
      empty: Number(current.samples || 0) === 0,
      kpis,
      samples: {
        current: Number(current.samples || 0),
        prior: Number(prior.samples || 0),
      },
      definition: {
        source: "metrics_daily.metrics grouped by metric_date",
        periodDays: days,
        currentStart: currentStart.toISOString(),
        priorStart: priorStart.toISOString(),
        end: end.toISOString(),
        emptyState: "No provider metrics have been ingested for this period.",
      },
    };
  }
}

module.exports = { AnalyticsRepository };
