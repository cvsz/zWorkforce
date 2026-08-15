const assert = require("node:assert/strict");
const express = require("express");
const test = require("node:test");

const databaseUrl = process.env.TEST_DATABASE_URL;
const integrationTest = databaseUrl ? test : test.skip;

async function request(baseUrl, path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, options);
  return {
    status: response.status,
    headers: response.headers,
    body: await response.json(),
  };
}

integrationTest(
  "v1 enforces auth, validation, request IDs, and idempotency",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const { createV1Router } = require("../src/api/v1");
    const pool = createPool({ connectionString: databaseUrl, max: 3 });
    await migrate(pool);
    await pool.query("TRUNCATE brands, audit_events, idempotency_keys CASCADE");
    const app = express();
    app.use(express.json());
    app.use(
      "/v1",
      createV1Router({
        pool,
        authenticate: async (token) =>
          token === "editor-token" ? { id: null, role: "editor" } : null,
      }),
    );
    const server = app.listen(0, "127.0.0.1");
    await new Promise((resolve) => server.once("listening", resolve));
    const baseUrl = `http://127.0.0.1:${server.address().port}`;

    const unauthorized = await request(baseUrl, "/v1/brands");
    assert.equal(unauthorized.status, 401);
    assert.equal(unauthorized.body.error.code, "UNAUTHORIZED");
    assert.ok(unauthorized.body.requestId);

    const invalid = await request(baseUrl, "/v1/brands", {
      method: "POST",
      headers: {
        authorization: "Bearer editor-token",
        "idempotency-key": "zato-1",
      },
      body: JSON.stringify({ name: "" }),
    });
    assert.equal(invalid.status, 422);
    assert.equal(invalid.body.error.code, "VALIDATION_ERROR");
    assert.ok(Array.isArray(invalid.body.error.details));

    const missingKey = await request(baseUrl, "/v1/brands", {
      method: "POST",
      headers: {
        authorization: "Bearer editor-token",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        name: "zato",
        niche: "Niche Content",
        colors: ["#ffffff", "#e9d5ff"],
      }),
    });
    assert.equal(missingKey.status, 400);
    assert.equal(missingKey.body.error.code, "IDEMPOTENCY_KEY_REQUIRED");

    const created = await request(baseUrl, "/v1/brands", {
      method: "POST",
      headers: {
        authorization: "Bearer editor-token",
        "content-type": "application/json",
        "idempotency-key": "zato-1",
        "x-request-id": "client-request-1",
      },
      body: JSON.stringify({
        name: "zato",
        niche: "Niche Content",
        colors: ["#ffffff", "#e9d5ff"],
      }),
    });
    assert.equal(created.status, 201);
    assert.equal(created.body.data.name, "zato");
    assert.equal(created.body.requestId, "client-request-1");
    assert.equal(created.body.data.secret_ref, undefined);

    const listed = await request(baseUrl, "/v1/brands?limit=1", {
      headers: { authorization: "Bearer editor-token" },
    });
    assert.equal(listed.status, 200);
    assert.equal(listed.body.data.length, 1);
    assert.equal(listed.body.pagination.limit, 1);

    const workflow = await request(baseUrl, "/v1/workflows", {
      method: "POST",
      headers: {
        authorization: "Bearer editor-token",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        brandId: created.body.data.id,
        name: "factory",
        steps: [
          { key: "m01", owner: "ops" },
          { key: "m10", owner: "qa" },
        ],
      }),
    });
    assert.equal(workflow.status, 201);
    const run = await request(
      baseUrl,
      `/v1/workflows/${workflow.body.data.id}/runs`,
      {
        method: "POST",
        headers: {
          authorization: "Bearer editor-token",
          "content-type": "application/json",
          "idempotency-key": "factory-run-1",
        },
        body: JSON.stringify({ input: { topic: "launch" } }),
      },
    );
    assert.equal(run.status, 202);
    const replay = await request(
      baseUrl,
      `/v1/workflows/${workflow.body.data.id}/runs`,
      {
        method: "POST",
        headers: {
          authorization: "Bearer editor-token",
          "content-type": "application/json",
          "idempotency-key": "factory-run-1",
        },
        body: JSON.stringify({ input: { topic: "launch" } }),
      },
    );
    assert.equal(replay.body.data.id, run.body.data.id);
    const runRead = await request(
      baseUrl,
      `/v1/workflow-runs/${run.body.data.id}`,
      { headers: { authorization: "Bearer editor-token" } },
    );
    assert.equal(runRead.body.data.steps.length, 2);

    await new Promise((resolve) => server.close(resolve));
    await pool.end();
  },
);

integrationTest("v1 publishes an OpenAPI contract", async () => {
  const { createPool } = require("../src/database/pool");
  const { createV1Router } = require("../src/api/v1");
  const pool = createPool({ connectionString: databaseUrl, max: 1 });
  const app = express();
  app.use(
    "/v1",
    createV1Router({
      pool,
      authenticate: async () => ({ id: null, role: "viewer" }),
    }),
  );
  const server = app.listen(0, "127.0.0.1");
  await new Promise((resolve) => server.once("listening", resolve));
  const response = await request(
    `http://127.0.0.1:${server.address().port}`,
    "/v1/openapi.json",
    {
      headers: { authorization: "Bearer anything" },
    },
  );
  assert.equal(response.status, 200);
  assert.equal(response.body.openapi, "3.1.0");
  assert.ok(response.body.paths["/v1/brands"]);
  await new Promise((resolve) => server.close(resolve));
  await pool.end();
});
