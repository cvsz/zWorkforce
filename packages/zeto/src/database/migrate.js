const crypto = require("node:crypto");
const fs = require("node:fs/promises");
const path = require("node:path");

const migrationsDir = path.join(__dirname, "migrations");

async function migrate(pool) {
  const client = await pool.connect();
  try {
    await client.query("SELECT pg_advisory_lock(hashtext('zeto:migrations'))");
    await client.query(`CREATE TABLE IF NOT EXISTS migrations (
      version text PRIMARY KEY,
      checksum text NOT NULL,
      applied_at timestamptz NOT NULL DEFAULT now()
    )`);
    const files = (await fs.readdir(migrationsDir))
      .filter((file) => file.endsWith(".sql"))
      .sort();
    for (const version of files) {
      const sql = await fs.readFile(path.join(migrationsDir, version), "utf8");
      const checksum = crypto.createHash("sha256").update(sql).digest("hex");
      const existing = await client.query(
        "SELECT checksum FROM migrations WHERE version = $1",
        [version],
      );
      if (existing.rowCount) {
        if (existing.rows[0].checksum !== checksum)
          throw new Error(`Migration checksum mismatch: ${version}`);
        continue;
      }
      await client.query("BEGIN");
      try {
        await client.query(sql);
        await client.query(
          "INSERT INTO migrations(version, checksum) VALUES ($1, $2)",
          [version, checksum],
        );
        await client.query("COMMIT");
      } catch (error) {
        await client.query("ROLLBACK");
        throw error;
      }
    }
  } finally {
    await client
      .query("SELECT pg_advisory_unlock(hashtext('zeto:migrations'))")
      .catch(() => {});
    client.release();
  }
}

if (require.main === module) {
  const { createPool } = require("./pool");
  const pool = createPool();
  migrate(pool)
    .then(() => console.log("Database migrations complete"))
    .finally(() => pool.end());
}

module.exports = { migrate };
