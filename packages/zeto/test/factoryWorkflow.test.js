const assert = require("node:assert/strict");
const test = require("node:test");
const { DIMENSIONS } = require("../src/domain/qaScorer");
const {
  FACTORY_STEPS,
  defaultFactoryHandlers,
} = require("../src/domain/factoryWorkflow");

function input() {
  return {
    brand: require("../config/brands/zato.json"),
    idea: { title: "Validate a niche", score: 91, persona: "creator" },
    palette: ["#ffffff", "#e9d5ff"],
    platforms: ["facebook"],
    image: {
      prompt: "editorial checklist",
      negativePrompt: "clutter",
      aspectRatio: "4:5",
      seed: "42",
    },
    video: {
      template: "reel",
      shots: [{ start: 0, end: 5, description: "Hook" }],
    },
    audio: {
      mood: "clear",
      bpm: 100,
      lufs: -14,
      useCase: "reel",
      license: "generated",
    },
    caption: {
      hook: "Validate first",
      body: "Test demand.",
      cta: "Start today.",
      hashtags: ["#NicheContent"],
    },
    qaChecks: Object.fromEntries(
      DIMENSIONS.map((key) => [key, { passed: true }]),
    ),
    autoPilot: false,
    platformPermitted: true,
    estimatedCost: 0.2,
    remainingBudget: 1,
    postsInWindow: 0,
    postingFrequencyCap: 3,
    claimsSubstantiated: true,
    copyrightCleared: true,
  };
}

const databaseUrl = process.env.TEST_DATABASE_URL;
const integrationTest = databaseUrl ? test : test.skip;

test("canonical factory definition orders every module and approval checkpoint", () => {
  assert.deepEqual(
    FACTORY_STEPS.map((step) => step.key),
    [
      "M01_STRATEGY",
      "M02_IMAGE",
      "M03_VIDEO",
      "M04_AUDIO",
      "M05_CAPTION",
      "M10_QA",
      "APPROVAL",
      "M06_PUBLISH",
      "M07_MONITOR",
      "M08_REPORT",
    ],
  );
});

test("M01-M10 handlers carry a complete asset pack into a durable approval pause", async () => {
  const handlers = defaultFactoryHandlers();
  let artifact = input();
  for (const step of FACTORY_STEPS.slice(0, 6))
    artifact = await handlers[step.key](artifact);
  assert.equal(artifact.assetPack.assets.length, 4);
  assert.equal(artifact.qa.score, 100);
  const approval = await handlers.APPROVAL(artifact);
  assert.equal(approval.blocked, true);
  assert.equal(approval.reason.code, "HUMAN_APPROVAL_REQUIRED");
});

test("publishing checks the emergency kill switch at execution time", async () => {
  const handlers = defaultFactoryHandlers();
  await assert.rejects(
    () =>
      handlers.M06_PUBLISH(
        { ...input(), completedModules: [] },
        { killSwitch: () => true, publish: async () => ({}) },
      ),
    (error) => error.code === "KILL_SWITCH_ACTIVE" && error.retryable === false,
  );
});

integrationTest(
  "factory run persists artifacts and traces, pauses for approval, then queues once",
  async () => {
    const { createPool } = require("../src/database/pool");
    const { migrate } = require("../src/database/migrate");
    const {
      FactoryWorkflowService,
    } = require("../src/services/factoryWorkflowService");
    const pool = createPool({ connectionString: databaseUrl, max: 3 });
    await migrate(pool);
    await pool.query("TRUNCATE brands CASCADE");
    const brand = await pool.query(
      "INSERT INTO brands(name, niche, colors) VALUES ('zato', 'Niche Content', '[\"#ffffff\",\"#e9d5ff\"]') RETURNING id",
    );
    const service = new FactoryWorkflowService({
      pool,
      killSwitch: () => false,
    });
    const command = {
      ...input(),
      brandId: brand.rows[0].id,
      platform: "facebook",
      publicationKind: "image",
      alertSnapshot: null,
    };
    const paused = await service.start(command, {
      idempotencyKey: "factory-e2e-1",
      requestId: "factory-request-1",
    });
    assert.equal(paused.status, "running");
    assert.equal(
      paused.steps.find((step) => step.step_key === "APPROVAL").status,
      "blocked",
    );
    assert.equal(paused.spans.length, 7);
    assert.equal(
      paused.spans.every((span) => span.trace_id === paused.trace_id),
      true,
    );

    const completed = await service.approve(paused.id, {
      decision: "approved",
      actorId: null,
    });
    assert.equal(completed.status, "succeeded");
    assert.deepEqual(completed.output.completedModules, [
      "M02",
      "M03",
      "M04",
      "M05",
      "M10",
      "M06",
      "M07",
      "M08",
    ]);
    const counts = await pool.query(
      `SELECT
        (SELECT count(*) FROM ideas) ideas,
        (SELECT count(*) FROM assets) assets,
        (SELECT count(*) FROM publications) publications,
        (SELECT count(*) FROM workflow_spans WHERE workflow_run_id = $1) spans`,
      [paused.id],
    );
    assert.deepEqual(
      Object.fromEntries(
        Object.entries(counts.rows[0]).map(([key, value]) => [
          key,
          Number(value),
        ]),
      ),
      { ideas: 1, assets: 4, publications: 1, spans: 11 },
    );
    const replay = await service.start(command, {
      idempotencyKey: "factory-e2e-1",
      requestId: "factory-request-replay",
    });
    assert.equal(replay.id, completed.id);
    assert.equal(
      Number(
        (await pool.query("SELECT count(*) FROM publications")).rows[0].count,
      ),
      1,
    );
    await pool.end();
  },
);
