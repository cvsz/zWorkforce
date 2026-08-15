"use strict";

const assert = require("node:assert/strict");
const express = require("express");
const test = require("node:test");

const databaseUrl = process.env.TEST_DATABASE_URL;
const integrationTest = databaseUrl ? test : test.skip;

async function createApp(pool) {
  const { createOperatorV1Router } = require("../src/api/operatorV1");
  const app = express();
  await pool.query(
    `INSERT INTO users(id, username, password_hash) VALUES
      ('10000000-0000-4000-8000-000000000001', 'admin', 'x'),
      ('10000000-0000-4000-8000-000000000002', 'editor', 'x'),
      ('10000000-0000-4000-8000-000000000003', 'viewer', 'x')
     ON CONFLICT (id) DO NOTHING`,
  );
  app.use(express.json());
  app.use((req, res, next) => {
    req.requestId = "req-test";
    next();
  });
  app.use((req, res, next) => {
    const token = (req.get("authorization") || "").replace(/^Bearer /, "");
    if (token === "admin-token")
      req.user = {
        id: "user-admin",
        userId: "10000000-0000-4000-8000-000000000001",
        role: "admin",
      };
    else if (token === "editor-token")
      req.user = {
        id: "user-editor",
        userId: "10000000-0000-4000-8000-000000000002",
        role: "editor",
      };
    else if (token === "viewer-token")
      req.user = {
        id: "user-viewer",
        userId: "10000000-0000-4000-8000-000000000003",
        role: "viewer",
      };
    else
      return res
        .status(401)
        .json({ ok: false, error: { code: "UNAUTHORIZED" } });
    return next();
  });
  app.use("/v1/operator", createOperatorV1Router({ pool }));
  const server = app.listen(0, "127.0.0.1");
  await new Promise((resolve) => server.once("listening", resolve));
  return server;
}

async function request(baseUrl, path, options = {}) {
  const response = await fetch(`${baseUrl}${path}`, options);
  return {
    status: response.status,
    body: await response.json().catch(() => null),
  };
}

async function prepareSession(runtime, sessionId) {
  for (const trigger of [
    "start_listening",
    "speech_available",
    "utterance_finalized",
    "intent_resolved",
  ]) {
    await runtime.transition(sessionId, trigger, { actor: "operator" });
  }
}

integrationTest("operator API enforces auth and roles", async () => {
  const { createPool } = require("../src/database/pool");
  const { migrate } = require("../src/database/migrate");
  const pool = createPool({ connectionString: databaseUrl, max: 3 });
  await migrate(pool);
  await pool.query("TRUNCATE operator_events, operator_sessions CASCADE");
  const server = await createApp(pool);
  const baseUrl = `http://127.0.0.1:${server.address().port}`;

  const anonymous = await request(baseUrl, "/v1/operator/sessions", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ mode: "operator" }),
  });
  assert.equal(anonymous.status, 401);

  const viewerForbidden = await request(baseUrl, "/v1/operator/sessions", {
    method: "POST",
    headers: {
      authorization: "Bearer viewer-token",
      "content-type": "application/json",
    },
    body: JSON.stringify({ mode: "operator" }),
  });
  assert.equal(viewerForbidden.status, 403);

  const invalid = await request(baseUrl, "/v1/operator/sessions", {
    method: "POST",
    headers: {
      authorization: "Bearer editor-token",
      "content-type": "application/json",
    },
    body: JSON.stringify({ mode: "not-a-mode" }),
  });
  assert.equal(invalid.status, 422);
  assert.equal(invalid.body.error.code, "VALIDATION_ERROR");

  await new Promise((resolve) => server.close(resolve));
  await pool.end();
});

integrationTest(
  "session lifecycle, pause/resume, cancel, emergency stop via API",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const pool = createPool({ connectionString: databaseUrl, max: 3 });
    await migrate(pool);
    await pool.query("TRUNCATE operator_events, operator_sessions CASCADE");
    const server = await createApp(pool);
    const baseUrl = `http://127.0.0.1:${server.address().port}`;
    const auth = {
      authorization: "Bearer editor-token",
      "content-type": "application/json",
    };

    const created = await request(baseUrl, "/v1/operator/sessions", {
      method: "POST",
      headers: auth,
      body: JSON.stringify({ mode: "operator", capabilities: ["queue.read"] }),
    });
    assert.equal(created.status, 201);
    const sessionId = created.body.data.session.id;
    assert.equal(created.body.data.session.state, "IDLE");
    assert.equal(created.body.data.sequence_id, 1);

    const command = await request(
      baseUrl,
      `/v1/operator/sessions/${sessionId}/commands`,
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ text: "post to facebook" }),
      },
    );
    assert.equal(command.status, 201);
    assert.ok(command.body.data.command_id);
    assert.equal(command.body.data.plan_id, null);

    // Drive to EXECUTING via the runtime service directly (planner is a later slice).
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    await prepareSession(runtime, sessionId);
    await runtime.transition(sessionId, "auto_approved", { actor: "operator" });
    assert.equal((await runtime.getSession(sessionId)).state, "EXECUTING");

    const paused = await request(
      baseUrl,
      `/v1/operator/sessions/${sessionId}/pause`,
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ reason: "operator break" }),
      },
    );
    assert.equal(paused.status, 200);
    assert.equal(paused.body.data.state, "PAUSED");

    const resumed = await request(
      baseUrl,
      `/v1/operator/sessions/${sessionId}/resume`,
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({}),
      },
    );
    assert.equal(resumed.status, 200);
    assert.equal(resumed.body.data.state, "EXECUTING");

    const cancelled = await request(
      baseUrl,
      `/v1/operator/sessions/${sessionId}/cancel`,
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ reason: "operator reject" }),
      },
    );
    assert.equal(cancelled.status, 200);
    assert.equal(cancelled.body.data.status, "cancelling");

    // Emergency stop requires admin.
    const emergencyForbidden = await request(
      baseUrl,
      `/v1/operator/sessions/${sessionId}/emergency-stop`,
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ reason: "blocked" }),
      },
    );
    assert.equal(emergencyForbidden.status, 403);

    await new Promise((resolve) => server.close(resolve));
    await pool.end();
  },
);

integrationTest(
  "GET /v1/operator/sessions/:id returns the session snapshot for restore",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const pool = createPool({ connectionString: databaseUrl, max: 3 });
    await migrate(pool);
    await pool.query("TRUNCATE operator_events, operator_sessions CASCADE");
    const server = await createApp(pool);
    const baseUrl = `http://127.0.0.1:${server.address().port}`;
    const auth = {
      authorization: "Bearer editor-token",
      "content-type": "application/json",
    };

    const created = await request(baseUrl, "/v1/operator/sessions", {
      method: "POST",
      headers: auth,
      body: JSON.stringify({ mode: "operator" }),
    });
    const sessionId = created.body.data.session.id;

    const snapshot = await request(
      baseUrl,
      `/v1/operator/sessions/${sessionId}`,
      {
        headers: { authorization: "Bearer viewer-token" },
      },
    );
    assert.equal(snapshot.status, 200);
    assert.equal(snapshot.body.data.id, sessionId);
    assert.equal(snapshot.body.data.state, "IDLE");
    assert.equal(snapshot.body.data.generation, 1);
    assert.equal(snapshot.body.data.lastSequenceId, 1);

    const missing = await request(
      baseUrl,
      "/v1/operator/sessions/00000000-0000-4000-8000-0000000000ff",
      { headers: { authorization: "Bearer viewer-token" } },
    );
    assert.equal(missing.status, 404);

    const invalid = await request(baseUrl, "/v1/operator/sessions/not-a-uuid", {
      headers: { authorization: "Bearer viewer-token" },
    });
    assert.equal(invalid.status, 422);

    await new Promise((resolve) => server.close(resolve));
    await pool.end();
  },
);

integrationTest(
  "plan approve/reject endpoints enforce approval state",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const pool = createPool({ connectionString: databaseUrl, max: 3 });
    await migrate(pool);
    await pool.query(
      "TRUNCATE operator_events, operator_commands, operator_plan_steps, operator_plans, operator_sessions CASCADE",
    );
    const server = await createApp(pool);
    const baseUrl = `http://127.0.0.1:${server.address().port}`;
    const auth = {
      authorization: "Bearer editor-token",
      "content-type": "application/json",
    };

    const created = await request(baseUrl, "/v1/operator/sessions", {
      method: "POST",
      headers: auth,
      body: JSON.stringify({ mode: "operator" }),
    });
    const sessionId = created.body.data.session.id;

    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    await prepareSession(runtime, sessionId);
    const { plan } = await runtime.createPlan({
      sessionId,
      intent: "publish",
      policyVerdict: "approval_required",
      estimatedCost: 0.5,
      steps: [
        { stepId: "s1", tool: "facebook_publish", args: {}, risk: "high" },
      ],
    });

    const view = await request(baseUrl, `/v1/operator/plans/${plan.id}`, {
      headers: { authorization: "Bearer viewer-token" },
    });
    assert.equal(view.status, 200);
    assert.equal(view.body.data.status, "pending");
    assert.equal(view.body.data.steps.length, 1);

    const approved = await request(
      baseUrl,
      `/v1/operator/plans/${plan.id}/approve`,
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ decision: "approved" }),
      },
    );
    assert.equal(approved.status, 200);
    assert.equal(approved.body.data.plan.status, "approved");
    assert.equal(approved.body.data.session.state, "EXECUTING");

    // Rejecting an already-approved plan is rejected.
    const second = await request(
      baseUrl,
      `/v1/operator/plans/${plan.id}/reject`,
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ reason: "too late" }),
      },
    );
    assert.equal(second.status, 400);

    await new Promise((resolve) => server.close(resolve));
    await pool.end();
  },
);

integrationTest(
  "SSE endpoint replays persisted events in order via Last-Event-ID",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const pool = createPool({ connectionString: databaseUrl, max: 3 });
    await migrate(pool);
    await pool.query("TRUNCATE operator_events, operator_sessions CASCADE");
    const server = await createApp(pool);
    const baseUrl = `http://127.0.0.1:${server.address().port}`;
    const auth = {
      authorization: "Bearer editor-token",
      "content-type": "application/json",
    };

    const created = await request(baseUrl, "/v1/operator/sessions", {
      method: "POST",
      headers: auth,
      body: JSON.stringify({ mode: "operator" }),
    });
    const sessionId = created.body.data.session.id;

    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    await prepareSession(runtime, sessionId);

    // Open the stream with Last-Event-ID: 0 (from start), then close after replay.
    const controller = new AbortController();
    const response = await fetch(
      `${baseUrl}/v1/operator/sessions/${sessionId}/events`,
      {
        headers: { authorization: "Bearer viewer-token", "last-event-id": "0" },
        signal: controller.signal,
      },
    );
    assert.equal(response.status, 200);
    assert.match(response.headers.get("content-type"), /text\/event-stream/);
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let text = "";
    const deadline = Date.now() + 5000;
    while (
      text.split("event: session.state_changed").length - 1 < 4 &&
      Date.now() < deadline
    ) {
      const { value, done } = await reader.read();
      if (done) break;
      text += decoder.decode(value, { stream: true });
    }
    controller.abort();

    const events = text
      .split("\n\n")
      .filter((block) => block.includes("data: "))
      .map((block) => JSON.parse(block.slice(block.indexOf("data: ") + 6)));
    assert.ok(
      events.length >= 5,
      `expected at least 5 events, got ${events.length}`,
    );
    const stateChanges = events.filter(
      (event) => event.type === "session.state_changed",
    );
    assert.equal(stateChanges.length, 4);
    const sequences = events.map((event) => event.sequence_id);
    for (let index = 1; index < sequences.length; index += 1) {
      assert.equal(
        sequences[index] - sequences[index - 1],
        1,
        "no gaps in replay",
      );
    }
    assert.equal(events[0].type, "session.started");
    assert.equal(stateChanges[0].from, "IDLE");
    assert.equal(stateChanges[0].to, "LISTENING");

    // Resume: Last-Event-ID of 2 replays only events after it.
    const resumeController = new AbortController();
    const resumeResponse = await fetch(
      `${baseUrl}/v1/operator/sessions/${sessionId}/events?lastEventId=2`,
      {
        headers: { authorization: "Bearer viewer-token" },
        signal: resumeController.signal,
      },
    );
    const resumeReader = resumeResponse.body.getReader();
    let resumeText = "";
    const resumeDeadline = Date.now() + 5000;
    while (
      resumeText.split("data: ").length - 1 < 3 &&
      Date.now() < resumeDeadline
    ) {
      const { value, done } = await resumeReader.read();
      if (done) break;
      resumeText += decoder.decode(value, { stream: true });
    }
    resumeController.abort();
    const resumeEvents = resumeText
      .split("\n\n")
      .filter((block) => block.includes("data: "))
      .map((block) => JSON.parse(block.slice(block.indexOf("data: ") + 6)));
    assert.ok(resumeEvents.length > 0);
    assert.ok(
      resumeEvents.every((event) => event.sequence_id > 2),
      "resume must not duplicate events with sequence_id <= 2",
    );

    await new Promise((resolve) => server.close(resolve));
    await pool.end();
  },
);

integrationTest(
  "sequence endpoints enforce roles and run/dry-run via the API",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const pool = createPool({ connectionString: databaseUrl, max: 3 });
    await migrate(pool);
    await pool.query(
      "TRUNCATE operator_events, operator_commands, operator_plan_steps, operator_plans, operator_sessions, operator_sequence_run_steps, operator_sequence_runs, operator_sequence_steps, operator_sequences CASCADE",
    );
    const server = await createApp(pool);
    const baseUrl = `http://127.0.0.1:${server.address().port}`;
    const auth = {
      authorization: "Bearer editor-token",
      "content-type": "application/json",
    };

    // Viewer may list but not create.
    const list = await request(baseUrl, "/v1/operator/sequences", {
      headers: { authorization: "Bearer viewer-token" },
    });
    assert.equal(list.status, 200);
    assert.deepEqual(list.body.data, []);

    const forbidden = await request(baseUrl, "/v1/operator/sequences", {
      method: "POST",
      headers: {
        authorization: "Bearer viewer-token",
        "content-type": "application/json",
      },
      body: JSON.stringify({
        name: "morning-brief",
        mode: "operator",
        steps: [{ id: "s1", intent: "queue.read", args: {} }],
      }),
    });
    assert.equal(forbidden.status, 403);

    const created = await request(baseUrl, "/v1/operator/sequences", {
      method: "POST",
      headers: auth,
      body: JSON.stringify({
        name: "morning-brief",
        mode: "operator",
        steps: [{ id: "s1", intent: "queue.read", args: {} }],
      }),
    });
    assert.equal(created.status, 201);
    const sequenceId = created.body.data.id;
    assert.equal(created.body.data.steps.length, 1);

    const fetched = await request(
      baseUrl,
      `/v1/operator/sequences/${sequenceId}`,
      { headers: { authorization: "Bearer viewer-token" } },
    );
    assert.equal(fetched.status, 200);
    assert.equal(fetched.body.data.steps[0].intent, "queue.read");

    // Dry-run returns a run_id; the run is inspectable.
    const session = await request(baseUrl, "/v1/operator/sessions", {
      method: "POST",
      headers: auth,
      body: JSON.stringify({ mode: "operator" }),
    });
    const sessionId = session.body.data.session.id;
    const run = await request(
      baseUrl,
      `/v1/operator/sequences/${sequenceId}/run`,
      {
        method: "POST",
        headers: auth,
        body: JSON.stringify({ dryRun: true, sessionId }),
      },
    );
    assert.equal(run.status, 201);
    assert.ok(run.body.data.run_id);
    assert.equal(run.body.data.status, "succeeded");

    const runDetail = await request(
      baseUrl,
      `/v1/operator/sequence-runs/${run.body.data.run_id}`,
      { headers: { authorization: "Bearer viewer-token" } },
    );
    assert.equal(runDetail.status, 200);
    assert.equal(runDetail.body.data.steps[0].status, "succeeded");

    // Validation: empty steps is rejected with 422.
    const invalid = await request(baseUrl, "/v1/operator/sequences", {
      method: "POST",
      headers: auth,
      body: JSON.stringify({ name: "empty", steps: [] }),
    });
    assert.equal(invalid.status, 422);

    await new Promise((resolve) => server.close(resolve));
    await pool.end();
  },
);
