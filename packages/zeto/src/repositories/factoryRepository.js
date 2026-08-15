class FactoryRepository {
  constructor(pool) {
    this.pool = pool;
  }

  async persistIdea(runId, brandId, idea) {
    const existing = await this.pool.query(
      "SELECT * FROM ideas WHERE brand_id = $1 AND provenance->>'workflowRunId' = $2 LIMIT 1",
      [brandId, runId],
    );
    if (existing.rowCount) return existing.rows[0];
    const result = await this.pool.query(
      `INSERT INTO ideas(brand_id, title, brief, score, status, provenance)
       VALUES ($1, $2, $3, $4, 'selected', $5) RETURNING *`,
      [
        brandId,
        idea.title,
        idea.brief || "",
        idea.score,
        JSON.stringify({ workflowRunId: runId, ...(idea.provenance || {}) }),
      ],
    );
    return result.rows[0];
  }

  async persistAssetPack(brandId, ideaId, pack) {
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      for (const asset of pack.assets) {
        await client.query(
          `INSERT INTO assets(id, brand_id, idea_id, type, prompt_hash, seed, brand_delta_e,
             lufs, aspect_ratio, tags, score, status, version, provenance)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
           ON CONFLICT (brand_id, prompt_hash, version) DO NOTHING`,
          [
            asset.id,
            brandId,
            ideaId,
            asset.type,
            asset.prompt_hash,
            asset.seed || null,
            asset.brand_delta_e,
            asset.lufs,
            asset.aspect_ratio || null,
            JSON.stringify(asset.tags || []),
            asset.score,
            asset.status,
            asset.version,
            JSON.stringify({
              ...(asset.provenance || {}),
              spec: asset.spec || {},
            }),
          ],
        );
      }
      for (const caption of pack.captions) {
        await client.query(
          `INSERT INTO captions(id, brand_id, asset_id, platform, body, hook, cta,
             hashtags, alt_text, seo_description, version)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
           ON CONFLICT (asset_id, platform, version) DO NOTHING`,
          [
            caption.id,
            brandId,
            caption.asset_id,
            caption.platform,
            caption.body,
            caption.hook,
            caption.cta,
            JSON.stringify(caption.hashtags),
            caption.alt_text,
            caption.seo_description,
            caption.version,
          ],
        );
      }
      await client.query("COMMIT");
      return pack;
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async persistQa(assetIds, qa) {
    const decision = qa.route === "block" ? "rejected" : "pending";
    const status = qa.route === "block" ? "blocked" : "review";
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      for (const assetId of assetIds) {
        const existing = await client.query(
          "SELECT 1 FROM approvals WHERE asset_id = $1 AND decision = $2 AND score = $3 LIMIT 1",
          [assetId, decision, qa.score],
        );
        if (!existing.rowCount) {
          await client.query(
            `INSERT INTO approvals(asset_id, decision, score, breakdown, reasons, remediation)
             VALUES ($1,$2,$3,$4,$5,$6)`,
            [
              assetId,
              decision,
              qa.score,
              JSON.stringify(qa.breakdown),
              JSON.stringify(qa.reasons),
              JSON.stringify(qa.remediation),
            ],
          );
        }
        await client.query(
          "UPDATE assets SET score = $2, status = $3, updated_at = now() WHERE id = $1",
          [assetId, qa.score, status],
        );
      }
      await client.query("COMMIT");
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async approve(assetIds, actorId, qa, decision = "approved") {
    if (!["approved", "overridden"].includes(decision))
      throw new Error("Invalid factory approval decision");
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      for (const assetId of assetIds) {
        await client.query(
          `INSERT INTO approvals(asset_id, actor_id, decision, score, breakdown, reasons, remediation)
           VALUES ($1,$2,$3,$4,$5,$6,$7)`,
          [
            assetId,
            actorId,
            decision,
            qa.score,
            JSON.stringify(qa.breakdown),
            JSON.stringify(qa.reasons),
            JSON.stringify(qa.remediation),
          ],
        );
        await client.query(
          "UPDATE assets SET status = 'approved', updated_at = now() WHERE id = $1",
          [assetId],
        );
      }
      await client.query("COMMIT");
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }
}

module.exports = { FactoryRepository };
