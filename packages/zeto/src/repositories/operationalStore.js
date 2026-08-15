const {
  createHash,
  randomBytes,
  randomUUID,
  pbkdf2Sync,
  timingSafeEqual,
} = require("node:crypto");
const encryption = require("../crypto");
const { readSecret } = require("../security/secrets");

const PASSWORD_ITERATIONS = 310000;
const SENSITIVE_SETTINGS = new Set([
  "facebookAccessToken",
  "facebookUserAccessToken",
  "lineNotifyToken",
  "discordWebhookUrl",
]);

function deepMerge(current, updates) {
  const result = { ...current };
  for (const [key, value] of Object.entries(updates || {})) {
    result[key] =
      value &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      typeof result[key] === "object"
        ? deepMerge(result[key], value)
        : value;
  }
  return result;
}

function transformSensitiveSettings(settings, transform) {
  return Object.fromEntries(
    Object.entries(settings || {}).map(([key, value]) => [
      key,
      SENSITIVE_SETTINGS.has(key) && value ? transform(value) : value,
    ]),
  );
}

function hashToken(token) {
  return createHash("sha256").update(token).digest("hex");
}

function encodePassword(password) {
  const salt = randomBytes(16).toString("hex");
  const hash = pbkdf2Sync(
    password,
    salt,
    PASSWORD_ITERATIONS,
    64,
    "sha512",
  ).toString("hex");
  return `pbkdf2-sha512$${PASSWORD_ITERATIONS}$${salt}$${hash}`;
}

function verifyPasswordHash(encoded, password) {
  const [algorithm, iterations, salt, expectedHex] = String(encoded).split("$");
  if (algorithm !== "pbkdf2-sha512" || !iterations || !salt || !expectedHex)
    return false;
  const actual = pbkdf2Sync(password, salt, Number(iterations), 64, "sha512");
  const expected = Buffer.from(expectedHex, "hex");
  return actual.length === expected.length && timingSafeEqual(actual, expected);
}

function mapPage(row) {
  if (!row) return null;
  return {
    id: row.id,
    facebookPageId: row.facebook_page_id,
    name: row.name,
    facebookAccessToken: encryption.decrypt(row.access_token_encrypted),
    facebookUserAccessToken: encryption.decrypt(
      row.user_access_token_encrypted,
    ),
    enabled: row.enabled,
    ...row.metadata,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function mapQueue(row) {
  if (!row) return null;
  return {
    id: row.id,
    pageId: row.page_id || "default",
    message: row.message,
    imageUrl: row.image_url,
    link: row.link,
    source: row.source,
    status: row.status,
    postId: row.provider_post_id,
    permalink: row.permalink,
    error: row.error,
    attempt: row.attempt,
    maxAttempts: row.max_attempts,
    availableAt: row.available_at,
    ...row.metadata,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

class OperationalStore {
  constructor(pool) {
    this.pool = pool;
    this.settings = {
      get: async () => {
        const result = await pool.query(
          "SELECT data FROM app_settings WHERE singleton = true",
        );
        return transformSensitiveSettings(
          result.rows[0]?.data || {},
          encryption.decrypt,
        );
      },
      update: async (updates) => {
        const client = await pool.connect();
        try {
          await client.query("BEGIN");
          const current = await client.query(
            "SELECT data FROM app_settings WHERE singleton = true FOR UPDATE",
          );
          const plaintext = transformSensitiveSettings(
            current.rows[0]?.data || {},
            encryption.decrypt,
          );
          const merged = deepMerge(plaintext, updates);
          const stored = transformSensitiveSettings(merged, encryption.encrypt);
          await client.query(
            `INSERT INTO app_settings(singleton, data) VALUES (true, $1)
             ON CONFLICT(singleton) DO UPDATE SET data = EXCLUDED.data, updated_at = now()`,
            [JSON.stringify(stored)],
          );
          await client.query("COMMIT");
          return merged;
        } catch (error) {
          await client.query("ROLLBACK");
          throw error;
        } finally {
          client.release();
        }
      },
    };
    this.pages = {
      getAll: async () =>
        (
          await pool.query("SELECT * FROM facebook_pages ORDER BY created_at")
        ).rows.map(mapPage),
      getById: async (id) =>
        mapPage(
          (
            await pool.query(
              "SELECT * FROM facebook_pages WHERE id::text = $1 OR facebook_page_id = $1",
              [id],
            )
          ).rows[0],
        ),
      add: async (page) =>
        mapPage(
          (
            await pool.query(
              `INSERT INTO facebook_pages(facebook_page_id, name, access_token_encrypted, user_access_token_encrypted, enabled, metadata)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
              [
                page.facebookPageId,
                page.name,
                encryption.encrypt(page.facebookAccessToken),
                encryption.encrypt(page.facebookUserAccessToken),
                page.enabled !== false,
                JSON.stringify(page.metadata || {}),
              ],
            )
          ).rows[0],
        ),
      update: async (id, updates) =>
        mapPage(
          (
            await pool.query(
              `UPDATE facebook_pages SET
                facebook_page_id = COALESCE($2, facebook_page_id), name = COALESCE($3, name),
                access_token_encrypted = COALESCE($4, access_token_encrypted),
                user_access_token_encrypted = COALESCE($5, user_access_token_encrypted),
                enabled = COALESCE($6, enabled), updated_at = now()
               WHERE id::text = $1 OR facebook_page_id = $1 RETURNING *`,
              [
                id,
                updates.facebookPageId,
                updates.name,
                updates.facebookAccessToken
                  ? encryption.encrypt(updates.facebookAccessToken)
                  : null,
                updates.facebookUserAccessToken
                  ? encryption.encrypt(updates.facebookUserAccessToken)
                  : null,
                updates.enabled,
              ],
            )
          ).rows[0],
        ),
      remove: async (id) =>
        mapPage(
          (
            await pool.query(
              "DELETE FROM facebook_pages WHERE id::text = $1 OR facebook_page_id = $1 RETURNING *",
              [id],
            )
          ).rows[0],
        ),
    };
    this.queue = {
      getAll: async (pageId = null) =>
        (
          await pool.query(
            `SELECT * FROM publication_queue WHERE ($1::text IS NULL OR page_id::text = $1) ORDER BY created_at DESC`,
            [pageId && pageId !== "default" ? pageId : null],
          )
        ).rows.map(mapQueue),
      getById: async (id) =>
        mapQueue(
          (
            await pool.query("SELECT * FROM publication_queue WHERE id = $1", [
              id,
            ])
          ).rows[0],
        ),
      getPending: async (pageId = null) =>
        this.#queueByStatus("pending", pageId),
      getPendingReview: async (pageId = null) =>
        this.#queueByStatus("pending_review", pageId),
      claimPending: async (pageId = null, workerId = "scheduler") =>
        mapQueue(
          (
            await pool.query(
              `WITH candidate AS (
                 SELECT id FROM publication_queue
                 WHERE status IN ('pending','retry_wait') AND available_at <= now()
                   AND ($1::text IS NULL OR page_id::text = $1)
                 ORDER BY available_at, created_at FOR UPDATE SKIP LOCKED LIMIT 1
               )
               UPDATE publication_queue SET status = 'publishing', attempt = attempt + 1,
                 metadata = metadata || jsonb_build_object('workerId', $2::text), updated_at = now()
               FROM candidate WHERE publication_queue.id = candidate.id RETURNING publication_queue.*`,
              [pageId && pageId !== "default" ? pageId : null, workerId],
            )
          ).rows[0],
        ),
      claimById: async (id) =>
        mapQueue(
          (
            await pool.query(
              `UPDATE publication_queue SET status = 'publishing', attempt = attempt + 1, updated_at = now()
               WHERE id = $1 AND status IN ('pending','retry_wait') AND available_at <= now()
               RETURNING *`,
              [id],
            )
          ).rows[0],
        ),
      add: async (item) =>
        mapQueue(
          (
            await pool.query(
              `INSERT INTO publication_queue(page_id, message, image_url, link, source, status, metadata)
               VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *`,
              [
                item.pageId && item.pageId !== "default" ? item.pageId : null,
                item.message,
                item.imageUrl || null,
                item.link || null,
                item.source || null,
                item.status || "pending",
                JSON.stringify(item.metadata || {}),
              ],
            )
          ).rows[0],
        ),
      remove: async (id) =>
        mapQueue(
          (
            await pool.query(
              "DELETE FROM publication_queue WHERE id = $1 RETURNING *",
              [id],
            )
          ).rows[0],
        ),
      updateStatus: async (id, status, meta = {}) =>
        mapQueue(
          (
            await pool.query(
              `UPDATE publication_queue SET status = $2, provider_post_id = COALESCE($3, provider_post_id),
                permalink = COALESCE($4, permalink), error = COALESCE($5, error), metadata = metadata || $6::jsonb,
                updated_at = now() WHERE id = $1 RETURNING *`,
              [
                id,
                status,
                meta.postId || null,
                meta.permalink || null,
                meta.error || null,
                JSON.stringify(meta),
              ],
            )
          ).rows[0],
        ),
      fail: async (id, error, retryDelayMs = 0) =>
        mapQueue(
          (
            await pool.query(
              `UPDATE publication_queue SET
                 status = CASE WHEN attempt < max_attempts THEN 'retry_wait' ELSE 'failed' END,
                 error = $2,
                 available_at = CASE WHEN attempt < max_attempts
                   THEN now() + ($3 * interval '1 millisecond') ELSE available_at END,
                 updated_at = now()
               WHERE id = $1 AND status = 'publishing' RETURNING *`,
              [id, error, retryDelayMs],
            )
          ).rows[0],
        ),
      retry: async (id) =>
        mapQueue(
          (
            await pool.query(
              `UPDATE publication_queue SET status = 'pending', error = NULL,
                 available_at = now(), updated_at = now()
               WHERE id = $1 AND status IN ('failed','error','retry_wait') RETURNING *`,
              [id],
            )
          ).rows[0],
        ),
      cancel: async (id) =>
        mapQueue(
          (
            await pool.query(
              `UPDATE publication_queue SET status = 'cancelled', updated_at = now()
               WHERE id = $1 AND status IN ('pending_review','pending','retry_wait') RETURNING *`,
              [id],
            )
          ).rows[0],
        ),
      approve: async (id, message = null) =>
        mapQueue(
          (
            await pool.query(
              `UPDATE publication_queue SET status = 'pending', message = COALESCE($2, message), updated_at = now()
               WHERE id = $1 AND status = 'pending_review' RETURNING *`,
              [id, message],
            )
          ).rows[0],
        ),
      clear: async (pageId = null) => {
        await pool.query(
          `UPDATE publication_queue SET status = 'cancelled', updated_at = now()
           WHERE status IN ('pending_review','pending','retry_wait')
             AND ($1::text IS NULL OR page_id::text = $1)`,
          [pageId && pageId !== "default" ? pageId : null],
        );
      },
    };
    this.history = {
      getAll: async (pageId = null, limit = 50) =>
        (
          await pool.query(
            `SELECT * FROM post_history WHERE ($1::text IS NULL OR page_id::text = $1)
             ORDER BY created_at DESC LIMIT $2`,
            [pageId && pageId !== "default" ? pageId : null, limit],
          )
        ).rows.map((row) => ({
          id: row.id,
          pageId: row.page_id || "default",
          status: row.status,
          message: row.message,
          source: row.source,
          postId: row.provider_post_id,
          error: row.error,
          ...row.metadata,
          createdAt: row.created_at,
        })),
      add: async (entry) => {
        const result = await pool.query(
          `INSERT INTO post_history(page_id, status, message, source, provider_post_id, error, metadata)
           VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *`,
          [
            entry.pageId && entry.pageId !== "default" ? entry.pageId : null,
            entry.status,
            entry.message || null,
            entry.source || null,
            entry.postId || null,
            entry.error || null,
            JSON.stringify(entry.metadata || {}),
          ],
        );
        return result.rows[0];
      },
    };
    this.schedules = {
      getAll: async (pageId = null) =>
        (
          await pool.query(
            `SELECT * FROM operational_schedules WHERE ($1::text IS NULL OR page_id::text = $1) ORDER BY created_at`,
            [pageId && pageId !== "default" ? pageId : null],
          )
        ).rows.map(this.#mapSchedule),
      add: async (item) =>
        this.#mapSchedule(
          (
            await pool.query(
              `INSERT INTO operational_schedules(page_id, name, cron, message, image_url, enabled)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
              [
                item.pageId && item.pageId !== "default" ? item.pageId : null,
                item.name,
                item.cron,
                item.message,
                item.imageUrl || null,
                item.enabled !== false,
              ],
            )
          ).rows[0],
        ),
      update: async (id, updates) =>
        this.#mapSchedule(
          (
            await pool.query(
              `UPDATE operational_schedules SET name = COALESCE($2, name), cron = COALESCE($3, cron),
               message = COALESCE($4, message), image_url = COALESCE($5, image_url), enabled = COALESCE($6, enabled), updated_at = now()
               WHERE id = $1 RETURNING *`,
              [
                id,
                updates.name,
                updates.cron,
                updates.message,
                updates.imageUrl,
                updates.enabled,
              ],
            )
          ).rows[0],
        ),
      remove: async (id) =>
        this.#mapSchedule(
          (
            await pool.query(
              "DELETE FROM operational_schedules WHERE id = $1 RETURNING *",
              [id],
            )
          ).rows[0],
        ),
    };
    this.sessions = {
      create: async (userId, role) => {
        const token = randomBytes(32).toString("hex");
        await pool.query(
          `INSERT INTO user_sessions(token_hash, user_id, role, expires_at)
           VALUES ($1, $2, $3, now() + ($4::text || ' seconds')::interval)`,
          [
            hashToken(token),
            userId,
            role,
            Number(process.env.SESSION_TTL_SECONDS || 43200),
          ],
        );
        return token;
      },
      get: async (token) => {
        if (!token) return null;
        const result = await pool.query(
          "SELECT user_id, role, created_at, expires_at FROM user_sessions WHERE token_hash = $1 AND expires_at > now()",
          [hashToken(token)],
        );
        const row = result.rows[0];
        return row
          ? {
              userId: row.user_id,
              role: row.role,
              createdAt: row.created_at,
              expiresAt: row.expires_at,
            }
          : null;
      },
      remove: async (token) =>
        (
          await pool.query("DELETE FROM user_sessions WHERE token_hash = $1", [
            hashToken(token),
          ])
        ).rowCount > 0,
    };
    this.users = {
      getByUsername: async (username) => {
        const result = await pool.query(
          `SELECT u.id, u.username, u.password_hash, r.name AS role FROM users u
           JOIN roles r ON r.id = u.role_id WHERE lower(u.username) = lower($1) AND u.status = 'active'`,
          [username],
        );
        return result.rows[0] || null;
      },
      verifyPassword: (user, password) =>
        verifyPasswordHash(user.password_hash, password),
      seedInitialAdmin: async () => {
        const password = readSecret("ADMIN_INITIAL_PASSWORD");
        const username = process.env.ADMIN_INITIAL_USERNAME || "admin";
        const count = await pool.query(
          "SELECT count(*)::int AS count FROM users",
        );
        if (count.rows[0].count > 0) return;
        if (!password)
          throw new Error(
            "ADMIN_INITIAL_PASSWORD is required for a fresh database",
          );
        const client = await pool.connect();
        try {
          await client.query("BEGIN");
          const role = await client.query(
            `INSERT INTO roles(name, permissions) VALUES ('admin', '["*"]')
             ON CONFLICT(name) DO UPDATE SET name = EXCLUDED.name RETURNING id`,
          );
          await client.query(
            "INSERT INTO users(id, role_id, username, password_hash) VALUES ($1, $2, $3, $4)",
            [randomUUID(), role.rows[0].id, username, encodePassword(password)],
          );
          await client.query("COMMIT");
        } catch (error) {
          await client.query("ROLLBACK");
          throw error;
        } finally {
          client.release();
        }
      },
    };
  }

  async #queueByStatus(status, pageId) {
    return (
      await this.pool.query(
        `SELECT * FROM publication_queue WHERE status = $1 AND ($2::text IS NULL OR page_id::text = $2)
         ORDER BY created_at FOR UPDATE SKIP LOCKED`,
        [status, pageId && pageId !== "default" ? pageId : null],
      )
    ).rows.map(mapQueue);
  }

  #mapSchedule(row) {
    if (!row) return null;
    return {
      id: row.id,
      pageId: row.page_id || "default",
      name: row.name,
      cron: row.cron,
      message: row.message,
      imageUrl: row.image_url,
      enabled: row.enabled,
      ...row.metadata,
      createdAt: row.created_at,
      updatedAt: row.updated_at,
    };
  }
}

module.exports = { OperationalStore, encodePassword, verifyPasswordHash };
