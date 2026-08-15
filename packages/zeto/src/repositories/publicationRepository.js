const crypto = require("node:crypto");
const {
  createDefaultProviderRegistry,
} = require("../providers/providerRegistry");

class PublicationRepository {
  constructor(
    pool,
    { providerRegistry = createDefaultProviderRegistry() } = {},
  ) {
    this.pool = pool;
    this.providerRegistry = providerRegistry;
  }

  async createApproved(command, context) {
    if (!context?.idempotencyKey || !context?.requestId)
      throw new Error("idempotencyKey and requestId are required");
    if (!Array.isArray(command.assetIds) || command.assetIds.length === 0)
      throw new Error("At least one asset is required");
    const provider = this.providerRegistry.get(command.platform);
    const requestHash = crypto
      .createHash("sha256")
      .update(JSON.stringify(command))
      .digest("hex");
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const reserved = await client.query(
        `INSERT INTO idempotency_keys(key, scope, request_hash)
         VALUES ($1, 'publications.create', $2) ON CONFLICT DO NOTHING RETURNING key`,
        [context.idempotencyKey, requestHash],
      );
      if (!reserved.rowCount) {
        const existing = await client.query(
          "SELECT scope, request_hash, response FROM idempotency_keys WHERE key = $1 FOR UPDATE",
          [context.idempotencyKey],
        );
        if (
          existing.rows[0].scope !== "publications.create" ||
          existing.rows[0].request_hash !== requestHash
        ) {
          throw new Error("Idempotency key reused with different input");
        }
        await client.query("COMMIT");
        return existing.rows[0].response;
      }

      const assets = await client.query(
        "SELECT id, status, type FROM assets WHERE brand_id = $1 AND id = ANY($2::uuid[]) FOR UPDATE",
        [command.brandId, command.assetIds],
      );
      if (assets.rowCount !== new Set(command.assetIds).size)
        throw new Error("Every publication asset must exist");
      const approvals = await client.query(
        `SELECT DISTINCT ON (asset_id) asset_id, decision FROM approvals
         WHERE asset_id = ANY($1::uuid[]) ORDER BY asset_id, created_at DESC, id DESC`,
        [command.assetIds],
      );
      const decisions = new Map(
        approvals.rows.map((row) => [row.asset_id, row.decision]),
      );
      const publishable = assets.rows.every(
        (asset) =>
          asset.status === "approved" &&
          ["approved", "overridden"].includes(decisions.get(asset.id)),
      );
      if (!publishable)
        throw new Error(
          "Every publication asset must have current approved state",
        );
      const requestedKinds = new Set(
        command.kind
          ? [command.kind]
          : assets.rows.map((asset) =>
              asset.type === "video" ? "video" : "image",
            ),
      );
      for (const kind of requestedKinds) {
        if (!provider.capabilities()[kind]) {
          throw new Error(
            `${command.platform} does not support ${kind} publications`,
          );
        }
      }

      const postResult = await client.query(
        `INSERT INTO posts(brand_id, asset_ids, caption, hashtags, platform, slot, status)
         VALUES ($1, $2, $3, $4, $5, $6, 'queued') RETURNING *`,
        [
          command.brandId,
          JSON.stringify(command.assetIds),
          command.caption || "",
          JSON.stringify(command.hashtags || []),
          command.platform,
          command.slot || null,
        ],
      );
      const publicationResult = await client.query(
        `INSERT INTO publications(post_id, provider, idempotency_key)
         VALUES ($1, $2, $3) RETURNING *`,
        [postResult.rows[0].id, command.platform, context.idempotencyKey],
      );
      const response = {
        post: postResult.rows[0],
        publication: publicationResult.rows[0],
      };
      await client.query(
        `INSERT INTO audit_events(actor_id, action, resource_type, resource_id, request_id, after_state)
         VALUES ($1, 'publication.queued', 'publication', $2, $3, $4)`,
        [
          context.actorId,
          response.publication.id,
          context.requestId,
          JSON.stringify(response),
        ],
      );
      await client.query(
        "UPDATE idempotency_keys SET resource_id = $2, response = $3 WHERE key = $1",
        [
          context.idempotencyKey,
          response.publication.id,
          JSON.stringify(response),
        ],
      );
      await client.query("COMMIT");
      return response;
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }
}

module.exports = { PublicationRepository };
