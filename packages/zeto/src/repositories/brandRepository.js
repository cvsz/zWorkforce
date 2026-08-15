const crypto = require("node:crypto");

class BrandRepository {
  constructor(pool) {
    this.pool = pool;
  }

  async list({ limit = 50, cursor = null } = {}) {
    const values = [limit + 1];
    let cursorClause = "";
    if (cursor) {
      values.push(cursor);
      cursorClause = "WHERE id > $2";
    }
    const result = await this.pool.query(
      `SELECT id, name, niche, colors, timezone, status, created_at, updated_at
       FROM brands ${cursorClause} ORDER BY id LIMIT $1`,
      values,
    );
    const hasMore = result.rows.length > limit;
    const rows = result.rows.slice(0, limit);
    return { rows, nextCursor: hasMore ? rows.at(-1).id : null };
  }

  async create(input, context) {
    if (!context?.idempotencyKey || !context?.requestId)
      throw new Error("idempotencyKey and requestId are required");
    const requestHash = crypto
      .createHash("sha256")
      .update(JSON.stringify(input))
      .digest("hex");
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const reserved = await client.query(
        `INSERT INTO idempotency_keys(key, scope, request_hash)
         VALUES ($1, 'brands.create', $2) ON CONFLICT DO NOTHING RETURNING key`,
        [context.idempotencyKey, requestHash],
      );
      if (!reserved.rowCount) {
        const existing = await client.query(
          "SELECT request_hash, response FROM idempotency_keys WHERE key = $1 FOR UPDATE",
          [context.idempotencyKey],
        );
        if (existing.rows[0].request_hash !== requestHash)
          throw new Error("Idempotency key reused with different input");
        await client.query("COMMIT");
        return existing.rows[0].response;
      }
      const created = await client.query(
        `INSERT INTO brands(name, niche, colors, timezone) VALUES ($1, $2, $3, $4) RETURNING *`,
        [
          input.name,
          input.niche,
          JSON.stringify(input.colors || []),
          input.timezone || "UTC",
        ],
      );
      const brand = created.rows[0];
      await client.query(
        `INSERT INTO audit_events(actor_id, action, resource_type, resource_id, request_id, after_state)
         VALUES ($1, 'brand.created', 'brand', $2, $3, $4)`,
        [context.actorId, brand.id, context.requestId, JSON.stringify(brand)],
      );
      await client.query(
        "UPDATE idempotency_keys SET resource_id = $2, response = $3 WHERE key = $1",
        [context.idempotencyKey, brand.id, JSON.stringify(brand)],
      );
      await client.query("COMMIT");
      return brand;
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }
}

module.exports = { BrandRepository };
