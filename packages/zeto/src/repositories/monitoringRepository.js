const { analyzeMention } = require("../domain/monitoring");

class MonitoringRepository {
  constructor(pool) {
    this.pool = pool;
  }

  async ingest(input) {
    const analysis = analyzeMention(input);
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const mention = (
        await client.query(
          `INSERT INTO mentions(brand_id, platform, external_id, body, classification, occurred_at, metadata)
           VALUES ($1, $2, $3, $4, $5, $6, $7)
           ON CONFLICT(platform, external_id) DO UPDATE SET
             body = EXCLUDED.body, classification = EXCLUDED.classification,
             occurred_at = EXCLUDED.occurred_at, metadata = EXCLUDED.metadata, updated_at = now()
           RETURNING *`,
          [
            input.brandId,
            input.platform,
            input.externalId,
            input.body,
            analysis.classification,
            input.occurredAt,
            JSON.stringify(input.metadata || {}),
          ],
        )
      ).rows[0];
      const sentiment = (
        await client.query(
          `INSERT INTO sentiment_scores(mention_id, score, model, rationale)
           VALUES ($1, $2, 'rules-v1', $3)
           ON CONFLICT(mention_id, model) DO UPDATE SET score = EXCLUDED.score,
             rationale = EXCLUDED.rationale, updated_at = now() RETURNING *`,
          [
            mention.id,
            analysis.sentiment,
            `classification:${analysis.classification}`,
          ],
        )
      ).rows[0];
      let escalation = null;
      if (analysis.escalation) {
        escalation = (
          await client.query(
            `INSERT INTO mention_escalations(
               mention_id, severity, reply_draft, handoff, due_at
             ) VALUES ($1, $2, $3, $4, now() + ($5 * interval '1 minute'))
             ON CONFLICT(mention_id) DO UPDATE SET
               severity = EXCLUDED.severity, reply_draft = EXCLUDED.reply_draft,
               handoff = EXCLUDED.handoff, due_at = EXCLUDED.due_at, updated_at = now()
             RETURNING *`,
            [
              mention.id,
              analysis.escalation.severity,
              analysis.replyDraft || null,
              analysis.escalation.handoff || null,
              analysis.escalation.slaMinutes,
            ],
          )
        ).rows[0];
      }
      await client.query("COMMIT");
      return { mention, sentiment, escalation };
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }
}

module.exports = { MonitoringRepository };
