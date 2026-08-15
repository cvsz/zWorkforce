"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");
const {
  isKnownIntent,
  intentRisk,
  isHighRiskStep,
  resolveStepArgs,
} = require("../src/domain/operatorSequences");
const {
  sequenceSchema,
  sequenceRunSchema,
} = require("../src/domain/operatorContracts");

test("sequenceSchema validates the §4.3 sequence shape", () => {
  const parsed = sequenceSchema.parse({
    name: "morning-brief",
    mode: "operator",
    steps: [
      { id: "s1", intent: "queue.read", args: { status: "pending" } },
      { id: "s2", intent: "session.status", args: {} },
    ],
    dryRun: false,
  });
  assert.equal(parsed.name, "morning-brief");
  assert.equal(parsed.mode, "operator");
  assert.equal(parsed.dryRun, false);
  assert.equal(parsed.steps.length, 2);
  assert.equal(parsed.steps[0].id, "s1");
});

test("sequenceSchema rejects duplicate step ids", () => {
  assert.throws(() =>
    sequenceSchema.parse({
      name: "dup",
      steps: [
        { id: "s1", intent: "queue.read" },
        { id: "s1", intent: "session.status" },
      ],
    }),
  );
});

test("sequenceSchema rejects empty or oversized sequences", () => {
  assert.throws(() => sequenceSchema.parse({ name: "empty", steps: [] }));
  assert.throws(() =>
    sequenceSchema.parse({
      name: "huge",
      steps: Array.from({ length: 51 }, (_, i) => ({
        id: `s${i}`,
        intent: "queue.read",
      })),
    }),
  );
});

test("sequenceRunSchema accepts dry_run, session, resume and confirm fields", () => {
  const parsed = sequenceRunSchema.parse({
    dryRun: true,
    sessionId: "00000000-0000-4000-8000-000000000001",
    resumeRunId: "00000000-0000-4000-8000-000000000002",
    confirmReplay: true,
  });
  assert.equal(parsed.dryRun, true);
  assert.equal(parsed.confirmReplay, true);
});

test("built-in intent registry covers the read-only slice intents", () => {
  assert.ok(isKnownIntent("queue.read"));
  assert.ok(isKnownIntent("session.status"));
  assert.ok(isKnownIntent("events.recent"));
  assert.equal(isKnownIntent("browser_navigate"), false);
  assert.equal(intentRisk("queue.read"), "none");
});

test("isHighRiskStep flags declared and derived high risk", () => {
  assert.equal(isHighRiskStep({ intent: "queue.read" }), false);
  assert.equal(isHighRiskStep({ intent: "queue.read", risk: "high" }), true);
  assert.equal(
    isHighRiskStep({ intent: "queue.read", risk: "critical" }),
    true,
  );
  assert.equal(isHighRiskStep({ intent: "unknown", risk: "medium" }), false);
});

test("resolveStepArgs substitutes s<N>.result at any depth", () => {
  const results = {
    s1: { count: 3, items: ["a"] },
    s2: { text: "hello" },
  };
  const args = {
    input: "s1.result",
    nested: { text: "s2.result" },
    list: ["s1.result", "literal"],
    untouched: "plain",
  };
  const resolved = resolveStepArgs(args, results, "s3");
  assert.deepEqual(resolved, {
    input: { count: 3, items: ["a"] },
    nested: { text: { text: "hello" } },
    list: [{ count: 3, items: ["a"] }, "literal"],
    untouched: "plain",
  });
});

test("resolveStepArgs errors when referencing an uncompleted step", () => {
  assert.throws(
    () => resolveStepArgs({ input: "s2.result" }, { s1: { ok: true } }, "s3"),
    /s2\.result before that step completed/,
  );
});

test("resolveStepArgs leaves non-reference strings untouched", () => {
  const resolved = resolveStepArgs(
    { text: "s1.result is great" },
    { s1: { ok: true } },
    "s3",
  );
  assert.equal(resolved.text, "s1.result is great");
});
