const assert = require("node:assert/strict");
const test = require("node:test");

const databaseUrl = process.env.TEST_DATABASE_URL;
const integrationTest = databaseUrl ? test : test.skip;

integrationTest(
  "operational store persists settings, pages, queue, history, and hashed sessions",
  async () => {
    process.env.SECRET_ENCRYPTION_KEY =
      "operational-store-test-key-with-32-characters";
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const {
      OperationalStore,
    } = require("../src/repositories/operationalStore");
    const pool = createPool({ connectionString: databaseUrl, max: 3 });
    await migrate(pool);
    await pool.query(
      "TRUNCATE app_settings, facebook_pages, publication_queue, post_history, user_sessions, audit_events CASCADE",
    );
    await pool.query(
      `INSERT INTO roles(id, name) VALUES ('00000000-0000-0000-0000-000000000010', 'admin') ON CONFLICT(name) DO NOTHING`,
    );
    const role = await pool.query("SELECT id FROM roles WHERE name = 'admin'");
    await pool.query(
      `INSERT INTO users(id, role_id, username, password_hash)
     VALUES ('00000000-0000-0000-0000-000000000001', $1, 'operational-admin', 'test') ON CONFLICT(username) DO NOTHING`,
      [role.rows[0].id],
    );
    const store = new OperationalStore(pool);

    await store.settings.update({
      schedulerEnabled: true,
      nested: { one: 1 },
      facebookAccessToken: "default-page-secret",
    });
    await store.settings.update({ nested: { two: 2 } });
    const settings = await store.settings.get();
    assert.deepEqual(settings.nested, { one: 1, two: 2 });
    assert.equal(settings.facebookAccessToken, "default-page-secret");
    const rawSettings = await pool.query(
      "SELECT data::text AS data FROM app_settings",
    );
    assert.doesNotMatch(rawSettings.rows[0].data, /default-page-secret/);

    const page = await store.pages.add({
      name: "Zato Facebook",
      facebookPageId: "fb-page-1",
      facebookAccessToken: "provider-secret",
      enabled: true,
    });
    assert.equal(
      (await store.pages.getById(page.id)).facebookAccessToken,
      "provider-secret",
    );
    const rawPage = await pool.query(
      "SELECT access_token_encrypted FROM facebook_pages WHERE id = $1",
      [page.id],
    );
    assert.notEqual(rawPage.rows[0].access_token_encrypted, "provider-secret");

    const queued = await store.queue.add({
      pageId: page.id,
      message: "Durable content",
      status: "pending",
    });
    const reconnected = new OperationalStore(pool);
    assert.equal((await reconnected.queue.getAll(page.id))[0].id, queued.id);
    const claims = await Promise.all([
      store.queue.claimPending(page.id, "worker-one"),
      reconnected.queue.claimPending(page.id, "worker-two"),
    ]);
    assert.equal(claims.filter(Boolean).length, 1);
    assert.equal(claims.find(Boolean).id, queued.id);
    assert.equal(await store.queue.claimById(queued.id), null);
    const retryWait = await store.queue.fail(queued.id, "temporary", 0);
    assert.equal(retryWait.status, "retry_wait");
    const retried = await store.queue.retry(queued.id);
    assert.equal(retried.status, "pending");
    const reclaimed = await store.queue.claimById(queued.id);
    assert.equal(reclaimed.attempt, 2);
    await store.queue.fail(queued.id, "temporary", 0);
    await store.queue.claimById(queued.id);
    const terminal = await store.queue.fail(queued.id, "permanent", 0);
    assert.equal(terminal.status, "failed");
    const cancellable = await store.queue.add({
      pageId: page.id,
      message: "Cancel me",
      status: "pending",
    });
    assert.equal(
      (await store.queue.cancel(cancellable.id)).status,
      "cancelled",
    );
    await store.history.add({
      pageId: page.id,
      status: "queued",
      message: "Durable content",
    });
    assert.equal((await store.history.getAll(page.id, 10)).length, 1);

    const token = await store.sessions.create(
      "00000000-0000-0000-0000-000000000001",
      "admin",
    );
    assert.equal((await store.sessions.get(token)).role, "admin");
    const rawSession = await pool.query("SELECT token_hash FROM user_sessions");
    assert.notEqual(rawSession.rows[0].token_hash, token);
    await store.sessions.remove(token);
    assert.equal(await store.sessions.get(token), null);
    const pageAudit = await pool.query(
      "SELECT action, after_state FROM audit_events WHERE resource_type = 'facebook_pages' ORDER BY created_at",
    );
    assert.equal(pageAudit.rows[0].action, "facebook_pages.insert");
    assert.equal(pageAudit.rows[0].after_state.name, "Zato Facebook");
    await pool.query("TRUNCATE user_sessions, users, roles CASCADE");
    const previousPassword = process.env.ADMIN_INITIAL_PASSWORD;
    delete process.env.ADMIN_INITIAL_PASSWORD;
    await assert.rejects(
      () => store.users.seedInitialAdmin(),
      /ADMIN_INITIAL_PASSWORD/,
    );
    if (previousPassword === undefined)
      delete process.env.ADMIN_INITIAL_PASSWORD;
    else process.env.ADMIN_INITIAL_PASSWORD = previousPassword;
    await pool.end();
  },
);
