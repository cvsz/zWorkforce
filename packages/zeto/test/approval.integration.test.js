const assert = require("node:assert/strict");
const test = require("node:test");

const databaseUrl = process.env.TEST_DATABASE_URL;
const integrationTest = databaseUrl ? test : test.skip;

integrationTest(
  "approval decisions are immutable database records",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const pool = createPool({ connectionString: databaseUrl, max: 3 });
    await migrate(pool);
    await pool.query("TRUNCATE brands, ideas, assets, approvals CASCADE");
    const brand = await pool.query(
      "INSERT INTO brands(name, niche) VALUES ('zato', 'Niche Content') RETURNING id",
    );
    const asset = await pool.query(
      "INSERT INTO assets(brand_id, type, prompt_hash, status) VALUES ($1, 'image', 'qa-test', 'review') RETURNING id",
      [brand.rows[0].id],
    );
    const approval = await pool.query(
      "INSERT INTO approvals(asset_id, decision, score, breakdown) VALUES ($1, 'approved', 96, '{}') RETURNING id",
      [asset.rows[0].id],
    );
    await assert.rejects(
      () =>
        pool.query("UPDATE approvals SET decision = 'rejected' WHERE id = $1", [
          approval.rows[0].id,
        ]),
      /immutable/i,
    );
    await assert.rejects(
      () =>
        pool.query("DELETE FROM approvals WHERE id = $1", [
          approval.rows[0].id,
        ]),
      /immutable/i,
    );
    await pool.end();
  },
);

integrationTest(
  "publication transaction rejects unapproved assets and deduplicates approved commands",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const {
      PublicationRepository,
    } = require("../src/repositories/publicationRepository");
    const pool = createPool({ connectionString: databaseUrl, max: 3 });
    await migrate(pool);
    await pool.query(
      "TRUNCATE brands, assets, approvals, posts, publications, audit_events, idempotency_keys CASCADE",
    );
    const brand = await pool.query(
      "INSERT INTO brands(name, niche) VALUES ('zato', 'Niche Content') RETURNING id",
    );
    const assets = await pool.query(
      `INSERT INTO assets(brand_id, type, prompt_hash, status) VALUES
      ($1, 'image', 'approved-asset', 'approved'), ($1, 'image', 'blocked-asset', 'blocked') RETURNING id, status`,
      [brand.rows[0].id],
    );
    await pool.query(
      "INSERT INTO approvals(asset_id, decision, score, breakdown) VALUES ($1, 'approved', 96, '{}'), ($2, 'rejected', 40, '{}')",
      [assets.rows[0].id, assets.rows[1].id],
    );
    const repository = new PublicationRepository(pool);
    await assert.rejects(
      () =>
        repository.createApproved(
          {
            brandId: brand.rows[0].id,
            assetIds: [assets.rows[0].id],
            platform: "unknown-network",
          },
          {
            idempotencyKey: "unknown-provider",
            requestId: "request-unknown-provider",
            actorId: null,
          },
        ),
      /Unknown publishing provider/,
    );
    await assert.rejects(
      () =>
        repository.createApproved(
          {
            brandId: brand.rows[0].id,
            assetIds: [assets.rows[1].id],
            platform: "facebook",
            caption: "blocked",
          },
          {
            idempotencyKey: "blocked-publish",
            requestId: "request-blocked",
            actorId: null,
          },
        ),
      /approved/i,
    );
    const command = {
      brandId: brand.rows[0].id,
      assetIds: [assets.rows[0].id],
      platform: "facebook",
      caption: "Approved content",
    };
    const context = {
      idempotencyKey: "approved-publish",
      requestId: "request-approved",
      actorId: null,
    };
    const first = await repository.createApproved(command, context);
    const duplicate = await repository.createApproved(command, context);
    assert.equal(duplicate.publication.id, first.publication.id);
    const counts = await pool.query(
      "SELECT (SELECT count(*) FROM posts) AS posts, (SELECT count(*) FROM publications) AS publications",
    );
    assert.equal(Number(counts.rows[0].posts), 1);
    assert.equal(Number(counts.rows[0].publications), 1);
    await pool.end();
  },
);
