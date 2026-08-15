const assert = require("node:assert/strict");
const test = require("node:test");

const databaseUrl = process.env.TEST_DATABASE_URL;
const integrationTest = databaseUrl ? test : test.skip;

integrationTest("migrations create the complete Phase 1 schema", async () => {
  const { createPool } = require("../src/database/pool");
  const { migrate } = require("../src/database/migrate");
  const pool = createPool({ connectionString: databaseUrl, max: 3 });

  await migrate(pool);
  const result = await pool.query(
    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename",
  );
  const actual = new Set(result.rows.map((row) => row.tablename));
  const required = [
    "alert_evaluations",
    "alerts",
    "app_settings",
    "approvals",
    "asset_variants",
    "assets",
    "audit_events",
    "brand_kits",
    "brands",
    "captions",
    "competitors",
    "cost_events",
    "ideas",
    "idempotency_keys",
    "jobs",
    "mentions",
    "metrics_daily",
    "mention_escalations",
    "migrations",
    "model_routes",
    "posts",
    "post_history",
    "provider_credentials",
    "publications",
    "publication_queue",
    "roles",
    "schedules",
    "sentiment_scores",
    "facebook_pages",
    "operational_schedules",
    "user_sessions",
    "users",
    "workflow_runs",
    "workflow_steps",
    "workflows",
    "operator_sessions",
    "operator_commands",
    "operator_events",
    "operator_plans",
    "operator_plan_steps",
    "operator_sequences",
    "operator_sequence_steps",
    "operator_sequence_runs",
    "operator_sequence_run_steps",
    "tool_executions",
    "verification_evidence",
  ];

  for (const table of required)
    assert.ok(actual.has(table), `missing table ${table}`);
  await pool.end();
});

integrationTest(
  "idempotent brand mutation writes exactly one audit event",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const { BrandRepository } = require("../src/repositories/brandRepository");
    const pool = createPool({ connectionString: databaseUrl, max: 3 });
    await migrate(pool);
    await pool.query("TRUNCATE brands, audit_events, idempotency_keys CASCADE");
    const repository = new BrandRepository(pool);
    const input = {
      name: "zato",
      niche: "Niche Content",
      colors: ["#ffffff", "#e9d5ff"],
    };

    const first = await repository.create(input, {
      actorId: null,
      idempotencyKey: "brand-zato-v1",
      requestId: "request-one",
    });
    const repeated = await repository.create(input, {
      actorId: null,
      idempotencyKey: "brand-zato-v1",
      requestId: "request-two",
    });

    assert.equal(repeated.id, first.id);
    assert.equal(repeated.name, "zato");
    const audit = await pool.query(
      "SELECT action, request_id FROM audit_events WHERE resource_type = 'brand'",
    );
    assert.equal(audit.rowCount, 1);
    assert.equal(audit.rows[0].action, "brand.created");
    assert.equal(audit.rows[0].request_id, "request-one");
    await pool.end();
  },
);

integrationTest(
  "durable jobs survive reconnect and are claimed once",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const { JobRepository } = require("../src/repositories/jobRepository");
    let pool = createPool({ connectionString: databaseUrl, max: 3 });
    await migrate(pool);
    await pool.query("TRUNCATE jobs CASCADE");
    const created = await new JobRepository(pool).enqueue({
      type: "generate",
      owner: "M02",
      payload: { brand: "zato" },
      idempotencyKey: "generate-zato-1",
    });
    await pool.end();

    pool = createPool({ connectionString: databaseUrl, max: 3 });
    const jobs = new JobRepository(pool);
    const claimed = await jobs.claim("worker-test");
    const secondClaim = await jobs.claim("worker-other");
    assert.equal(claimed.id, created.id);
    assert.equal(claimed.status, "running");
    assert.equal(secondClaim, null);
    await pool.end();
  },
);

integrationTest(
  "jobs heartbeat, retry, cancel, and dead-letter safely",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const { JobRepository } = require("../src/repositories/jobRepository");
    const pool = createPool({ connectionString: databaseUrl, max: 2 });
    await migrate(pool);
    await pool.query("TRUNCATE jobs CASCADE");
    const jobs = new JobRepository(pool);

    const retryJob = await jobs.enqueue({
      type: "publish",
      owner: "m06",
      idempotencyKey: `retry-${Date.now()}`,
      maxAttempts: 2,
      timeoutMs: 1000,
    });
    const claimed = await jobs.claim("worker-1");
    assert.equal(claimed.id, retryJob.id);
    assert.equal(
      (await jobs.heartbeat(claimed.id, "worker-1")).status,
      "running",
    );
    assert.equal(
      (await jobs.fail(claimed.id, "worker-1", { code: "TEMP" }, 0)).status,
      "retry_wait",
    );
    const secondClaim = await jobs.claim("worker-2");
    assert.equal(secondClaim.attempt, 2);
    assert.equal(
      (await jobs.fail(secondClaim.id, "worker-2", { code: "TEMP" }, 0)).status,
      "failed",
    );

    const cancelJob = await jobs.enqueue({
      type: "report",
      owner: "m08",
      idempotencyKey: `cancel-${Date.now()}`,
    });
    assert.equal((await jobs.cancel(cancelJob.id)).status, "cancelled");
    assert.equal(await jobs.claim("worker-3"), null);
    await pool.end();
  },
);

integrationTest(
  "workflow runs resume successful steps and account for cost",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const {
      WorkflowRepository,
    } = require("../src/repositories/workflowRepository");
    const pool = createPool({ connectionString: databaseUrl, max: 2 });
    await migrate(pool);
    await pool.query("TRUNCATE brands, workflows, workflow_runs CASCADE");
    const brand = (
      await pool.query(
        "INSERT INTO brands(name, niche) VALUES ('zato', 'Niche Content') RETURNING id",
      )
    ).rows[0];
    const workflows = new WorkflowRepository(pool);
    const workflow = await workflows.createDefinition({
      brandId: brand.id,
      name: "factory",
      steps: [
        { key: "m01", owner: "ops" },
        { key: "m10", owner: "qa", maxAttempts: 2 },
      ],
    });
    const run = await workflows.start(
      workflow.id,
      { topic: "launch" },
      `factory-run-${Date.now()}`,
    );

    const first = await workflows.claimNext(run.id, "worker-1");
    assert.equal(first.step_key, "m01");
    assert.equal(await workflows.claimNext(run.id, "worker-2"), null);
    await workflows.succeed(first.id, "worker-1", { ideaId: "idea-1" }, 0.125);
    const second = await workflows.claimNext(run.id, "worker-2");
    assert.equal(second.step_key, "m10");
    assert.deepEqual(second.input, { ideaId: "idea-1" });
    await workflows.fail(second.id, "worker-2", { code: "TEMP" }, 0);
    const retried = await workflows.claimNext(run.id, "worker-3");
    assert.equal(retried.attempt, 2);
    await workflows.succeed(retried.id, "worker-3", { qaScore: 95 }, 0.25);

    const complete = await workflows.getRun(run.id);
    assert.equal(complete.status, "succeeded");
    assert.equal(Number(complete.cost), 0.375);
    assert.deepEqual(complete.output, { qaScore: 95 });
    assert.deepEqual(
      complete.steps.map((step) => step.status),
      ["succeeded", "succeeded"],
    );
    const stuckRun = await workflows.start(
      workflow.id,
      { topic: "stuck" },
      `stuck-run-${Date.now()}`,
    );
    const stuckStep = await workflows.claimNext(stuckRun.id, "lost-worker");
    await pool.query(
      "UPDATE workflow_steps SET heartbeat_at = now() - interval '10 minutes' WHERE id = $1",
      [stuckStep.id],
    );
    const recovered = await workflows.requeueStuck(new Date());
    assert.equal(
      recovered.find((step) => step.id === stuckStep.id).status,
      "retry_wait",
    );
    await pool.end();
  },
);
