const assert = require("node:assert/strict");
const test = require("node:test");

test("model router blocks all providers before invocation when cost cap is exceeded", async () => {
  const { ModelRouter } = require("../src/domain/modelRouter");
  let calls = 0;
  const router = new ModelRouter({
    providers: {
      expensive: async () => {
        calls += 1;
        return { output: "never" };
      },
    },
    recordCostEvent: async () => {},
    enqueueFailure: async () => {},
  });
  await assert.rejects(
    () =>
      router.execute({
        task: "caption",
        input: { prompt: "test" },
        budget: 0.01,
        routes: [{ provider: "expensive", model: "large", estimatedCost: 0.5 }],
      }),
    /cost cap/i,
  );
  assert.equal(calls, 0);
});

test("model router records failed preference and successful bounded fallback", async () => {
  const { ModelRouter } = require("../src/domain/modelRouter");
  const events = [];
  const router = new ModelRouter({
    providers: {
      primary: async () => {
        throw new Error("provider unavailable");
      },
      fallback: async () => ({
        output: { caption: "Useful niche content" },
        usage: { input: 10, output: 5 },
      }),
    },
    recordCostEvent: async (event) => events.push(event),
    enqueueFailure: async () => assert.fail("failure queue should not be used"),
  });
  const result = await router.execute({
    task: "caption",
    input: { prompt: "test" },
    budget: 1,
    routes: [
      { provider: "primary", model: "model-a", estimatedCost: 0.02 },
      { provider: "fallback", model: "model-b", estimatedCost: 0.01 },
    ],
  });
  assert.equal(result.provider, "fallback");
  assert.equal(result.retryCount, 1);
  assert.equal(events.length, 2);
  assert.equal(events[0].fallbackReason, "provider unavailable");
  assert.equal(events[1].usage.output, 5);
  assert.ok(events[1].latencyMs >= 0);
});

test("model router queues a failed job after the fallback chain is exhausted", async () => {
  const { ModelRouter } = require("../src/domain/modelRouter");
  const failures = [];
  const router = new ModelRouter({
    providers: { broken: async () => Promise.reject(new Error("down")) },
    recordCostEvent: async () => {},
    enqueueFailure: async (failure) => failures.push(failure),
  });
  await assert.rejects(
    () =>
      router.execute({
        task: "image",
        input: { prompt: "test" },
        budget: 1,
        routes: [{ provider: "broken", model: "model-x", estimatedCost: 0.1 }],
      }),
    /all model routes failed/i,
  );
  assert.equal(failures.length, 1);
  assert.equal(failures[0].task, "image");
  assert.equal(failures[0].attempts.length, 1);
});
