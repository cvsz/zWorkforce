const { evaluateAlerts } = require("../domain/monitoring");

const RULE_TYPES = [
  "volume_spike",
  "sentiment_deterioration",
  "viral_negative_content",
  "competitor_pricing_mention",
  "creator_influencer_mention",
  "overdue_critical_reply",
];

class AlertRepository {
  constructor(pool) {
    this.pool = pool;
  }

  async evaluate(snapshot) {
    const active = evaluateAlerts(snapshot);
    const byType = new Map(active.map((alert) => [alert.type, alert]));
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const stored = [];
      for (const type of RULE_TYPES) {
        const candidate = byType.get(type);
        let alert = null;
        if (candidate) {
          alert = (
            await client.query(
              `INSERT INTO alerts(brand_id, type, dedupe_key, severity, payload)
               VALUES ($1, $2, $3, $4, $5)
               ON CONFLICT(brand_id, dedupe_key) DO UPDATE SET
                 severity = EXCLUDED.severity, payload = EXCLUDED.payload, updated_at = now()
               RETURNING *`,
              [
                snapshot.brandId,
                type,
                candidate.dedupeKey,
                candidate.severity,
                JSON.stringify(candidate.evidence),
              ],
            )
          ).rows[0];
          stored.push(alert);
        }
        const evaluationKey = `${snapshot.brandId}:${type}:${snapshot.period}`;
        await client.query(
          `INSERT INTO alert_evaluations(
             brand_id, alert_id, rule_type, dedupe_key, predicted_positive
           ) VALUES ($1, $2, $3, $4, $5)
           ON CONFLICT(dedupe_key) DO UPDATE SET
             alert_id = EXCLUDED.alert_id,
             predicted_positive = EXCLUDED.predicted_positive,
             updated_at = now()`,
          [
            snapshot.brandId,
            alert?.id || null,
            type,
            evaluationKey,
            Boolean(candidate),
          ],
        );
      }
      await client.query("COMMIT");
      return stored;
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async label(alertId, actualPositive, actorId, notes = null) {
    const result = await this.pool.query(
      `UPDATE alert_evaluations SET actual_positive = $2, actor_id = $3,
         notes = $4, updated_at = now() WHERE alert_id = $1 RETURNING *`,
      [alertId, actualPositive, actorId, notes],
    );
    if (!result.rowCount) throw new Error("Alert evaluation not found");
    return result.rows[0];
  }

  async quality(brandId = null) {
    const result = await this.pool.query(
      `SELECT
         count(*) FILTER (WHERE actual_positive IS NOT NULL)::integer AS labelled,
         count(*) FILTER (WHERE predicted_positive AND actual_positive)::integer AS true_positive,
         count(*) FILTER (WHERE predicted_positive AND NOT actual_positive)::integer AS false_positive,
         count(*) FILTER (WHERE NOT predicted_positive AND actual_positive)::integer AS false_negative
       FROM alert_evaluations WHERE ($1::uuid IS NULL OR brand_id = $1)`,
      [brandId],
    );
    const row = result.rows[0];
    const tp = row.true_positive;
    const fp = row.false_positive;
    const fn = row.false_negative;
    return {
      labelled: row.labelled,
      truePositive: tp,
      falsePositive: fp,
      precision: tp + fp ? tp / (tp + fp) : null,
      falseNegative: fn,
      recall: tp + fn ? tp / (tp + fn) : null,
    };
  }
}

module.exports = { AlertRepository };
