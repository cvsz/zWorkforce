"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const databaseUrl = process.env.TEST_DATABASE_URL;
const integrationTest = databaseUrl ? test : test.skip;

async function freshPool() {
  const { createPool } = require("../src/database/pool");
  const { migrate } = require("../src/database/migrate");
  const pool = createPool({ connectionString: databaseUrl, max: 3 });
  await migrate(pool);
  await pool.query(
    "TRUNCATE operator_events, operator_commands, operator_plan_steps, operator_plans, tool_executions, verification_evidence, operator_sessions, operator_sequence_run_steps, operator_sequence_runs, operator_sequence_steps, operator_sequences, publication_queue CASCADE",
  );
  return pool;
}

async function createSession(runtime) {
  return runtime.createSession({
    mode: "operator",
    capabilities: ["queue.read"],
  });
}

async function seedQueue(pool) {
  await pool.query(
    `INSERT INTO publication_queue(message, status) VALUES
      ('first', 'pending'),
      ('second', 'pending'),
      ('third', 'published')`,
  );
}

integrationTest(
  "sequence CRUD persists and returns steps in order",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });

    const created = await runtime.createSequence({
      name: "morning-brief",
      mode: "operator",
      steps: [
        { id: "s1", intent: "queue.read", args: { status: "pending" } },
        { id: "s2", intent: "session.status", args: {} },
      ],
    });
    assert.ok(created.id);
    assert.equal(created.name, "morning-brief");
    assert.equal(created.steps.length, 2);
    assert.equal(created.steps[0].id, "s1");
    assert.equal(created.steps[1].id, "s2");

    const listed = await runtime.listSequences();
    assert.ok(listed.some((seq) => seq.id === created.id));
    assert.equal(listed.find((seq) => seq.id === created.id).stepCount, 2);

    const fetched = await runtime.getSequence(created.id);
    assert.equal(fetched.steps.length, 2);

    const updated = await runtime.updateSequence(created.id, {
      name: "morning-brief-v2",
      mode: "operator",
      steps: [{ id: "s1", intent: "session.status", args: {} }],
    });
    assert.equal(updated.name, "morning-brief-v2");
    assert.equal(updated.steps.length, 1);

    const deleted = await runtime.deleteSequence(created.id);
    assert.equal(deleted.deleted, true);
    assert.equal(await runtime.getSequence(created.id), null);
    await pool.end();
  },
);

integrationTest(
  "running a sequence executes steps sequentially with s<N>.result chaining",
  async () => {
    const pool = await freshPool();
    await seedQueue(pool);
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session } = await createSession(runtime);

    const sequence = await runtime.createSequence({
      name: "queue-brief",
      mode: "operator",
      steps: [
        { id: "s1", intent: "queue.read", args: { status: "pending" } },
        { id: "s2", intent: "session.status", args: { input: "s1.result" } },
      ],
    });

    const { run, events } = await runtime.runSequence({
      sequenceId: sequence.id,
      sessionId: session.id,
    });
    assert.equal(run.status, "succeeded");
    assert.equal(run.dryRun, false);
    assert.equal(run.currentStep, null);

    const eventTypes = events.map((event) => event.type);
    assert.ok(eventTypes.includes("input.received"));
    assert.ok(eventTypes.includes("step.started"));
    assert.ok(eventTypes.includes("step.finished"));
    assert.ok(!eventTypes.includes("step.failed"));

    const runDetail = await runtime.getSequenceRun(run.id);
    assert.equal(runDetail.steps.length, 2);
    assert.equal(runDetail.steps[0].status, "succeeded");
    assert.equal(runDetail.steps[0].result.count, 2);
    // s2 received s1.result as its `input` arg (chaining worked).
    assert.equal(runDetail.steps[1].status, "succeeded");
    assert.equal(runDetail.steps[1].result.state, "IDLE");
    assert.equal(runDetail.steps[1].result.id, session.id);
    await pool.end();
  },
);

integrationTest(
  "unsupported intent stops the run at the failing step and offers resume",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session } = await createSession(runtime);

    const sequence = await runtime.createSequence({
      name: "flaky",
      mode: "operator",
      steps: [
        { id: "s1", intent: "queue.read", args: {} },
        { id: "s2", intent: "browser_navigate", args: {} },
        { id: "s3", intent: "session.status", args: {} },
      ],
    });

    const { run, events } = await runtime.runSequence({
      sequenceId: sequence.id,
      sessionId: session.id,
    });
    assert.equal(run.status, "failed");
    assert.equal(run.currentStep, "s2");
    assert.match(run.error.message, /Unsupported intent "browser_navigate"/);

    const runDetail = await runtime.getSequenceRun(run.id);
    assert.equal(runDetail.steps[0].status, "succeeded");
    assert.equal(runDetail.steps[1].status, "failed");
    assert.equal(runDetail.steps[2].status, "queued", "later steps must stop");

    const eventTypes = events.map((event) => event.type);
    assert.ok(eventTypes.includes("step.failed"));
    await pool.end();
  },
);

integrationTest(
  "resume skips succeeded steps and re-runs from the failed step",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session } = await createSession(runtime);

    // Force a failure on the first run by referencing a step output (s9) that
    // never completes; resume must re-run the failed step and stop again.
    const bad = await runtime.createSequence({
      name: "resumable-bad",
      mode: "operator",
      steps: [
        { id: "s1", intent: "queue.read", args: {} },
        { id: "s2", intent: "session.status", args: { input: "s9.result" } },
      ],
    });
    const first = await runtime.runSequence({
      sequenceId: bad.id,
      sessionId: session.id,
    });
    assert.equal(first.run.status, "failed");
    assert.equal(first.run.currentStep, "s2");
    assert.match(first.run.error.message, /s9\.result/);

    // Resume now fails again with the same arg reference (deterministic),
    // proving resume re-runs the failed step and stops.
    const resumed = await runtime.runSequence({
      sequenceId: bad.id,
      sessionId: session.id,
      resumeRunId: first.run.id,
    });
    assert.equal(resumed.run.status, "failed");
    assert.equal(resumed.run.currentStep, "s2");
    assert.equal(resumed.run.id, first.run.id, "resume reuses the same run");

    const detail = await runtime.getSequenceRun(first.run.id);
    assert.equal(detail.steps[0].status, "succeeded", "s1 result reused");
    assert.equal(detail.steps[1].status, "failed");
    await pool.end();
  },
);

integrationTest("high-risk replay requires operator confirmation", async () => {
  const pool = await freshPool();
  const {
    OperatorRuntimeService,
  } = require("../src/services/operatorRuntimeService");
  const runtime = new OperatorRuntimeService({ pool });
  const { session } = await createSession(runtime);

  const sequence = await runtime.createSequence({
    name: "risky",
    mode: "operator",
    steps: [
      { id: "s1", intent: "queue.read", args: {} },
      {
        id: "s2",
        intent: "session.status",
        args: { input: "s9.result" },
        risk: "high",
      },
    ],
  });
  const first = await runtime.runSequence({
    sequenceId: sequence.id,
    sessionId: session.id,
  });
  assert.equal(first.run.status, "failed");

  await assert.rejects(
    runtime.runSequence({
      sequenceId: sequence.id,
      sessionId: session.id,
      resumeRunId: first.run.id,
    }),
    /requires operator confirmation/,
  );

  const confirmed = await runtime.runSequence({
    sequenceId: sequence.id,
    sessionId: session.id,
    resumeRunId: first.run.id,
    confirmReplay: true,
  });
  assert.equal(confirmed.run.status, "failed", "replay re-runs and stops");
  await pool.end();
});

integrationTest(
  "dry-run executes the same read-only steps but flags the run",
  async () => {
    const pool = await freshPool();
    await seedQueue(pool);
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    const { session } = await createSession(runtime);

    const sequence = await runtime.createSequence({
      name: "dry",
      mode: "operator",
      steps: [{ id: "s1", intent: "queue.read", args: { status: "pending" } }],
    });
    const { run } = await runtime.runSequence({
      sequenceId: sequence.id,
      sessionId: session.id,
      dryRun: true,
    });
    assert.equal(run.status, "succeeded");
    assert.equal(run.dryRun, true);
    await pool.end();
  },
);

integrationTest(
  "run resolves the actor's latest session when none is supplied",
  async () => {
    const pool = await freshPool();
    const {
      OperatorRuntimeService,
    } = require("../src/services/operatorRuntimeService");
    const runtime = new OperatorRuntimeService({ pool });
    await createSession(runtime);

    const sequence = await runtime.createSequence({
      name: "auto-session",
      mode: "operator",
      steps: [{ id: "s1", intent: "session.status", args: {} }],
    });
    const { run, session } = await runtime.runSequence({
      sequenceId: sequence.id,
      actorId: null,
    });
    assert.equal(run.status, "succeeded");
    assert.ok(session.id);
    await pool.end();
  },
);
