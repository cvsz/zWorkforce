const { Pool } = require("pg");

function createPool(options = {}) {
  const connectionString = options.connectionString || process.env.DATABASE_URL;
  if (!connectionString) throw new Error("DATABASE_URL is required");
  const pool = new Pool({
    connectionString,
    max: options.max || Number(process.env.DB_POOL_MAX || 10),
    idleTimeoutMillis: Number(process.env.DB_IDLE_TIMEOUT_MS || 30000),
    connectionTimeoutMillis: Number(process.env.DB_CONNECT_TIMEOUT_MS || 5000),
    statement_timeout: Number(process.env.DB_STATEMENT_TIMEOUT_MS || 30000),
    application_name: "zeto",
  });
  pool.on("error", (error) =>
    console.error("[database] idle client error", error),
  );
  return pool;
}

module.exports = { createPool };
