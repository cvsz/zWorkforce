const assert = require("node:assert/strict");
const test = require("node:test");

test("calendar converts valid local slots to UTC and rejects DST gaps", () => {
  const { localSlotToUtc } = require("../src/domain/calendar");
  assert.equal(
    localSlotToUtc("2026-08-14T09:00:00", "Asia/Bangkok"),
    "2026-08-14T02:00:00.000Z",
  );
  assert.throws(
    () => localSlotToUtc("2026-03-08T02:30:00", "America/New_York"),
    /invalid local time/i,
  );
  assert.throws(
    () => localSlotToUtc("2026-08-14T09:00:00", "Mars/Olympus"),
    /timezone/i,
  );
});

test("bounded retry uses exponential delay and deterministic jitter", () => {
  const { retryDecision } = require("../src/domain/retryPolicy");
  const first = retryDecision({
    attempt: 1,
    maxAttempts: 3,
    baseMs: 1000,
    maxMs: 10000,
    random: () => 0.5,
  });
  const second = retryDecision({
    attempt: 2,
    maxAttempts: 3,
    baseMs: 1000,
    maxMs: 10000,
    random: () => 0.5,
  });
  assert.deepEqual(first, { retry: true, delayMs: 1000 });
  assert.deepEqual(second, { retry: true, delayMs: 2000 });
  assert.deepEqual(retryDecision({ attempt: 3, maxAttempts: 3 }), {
    retry: false,
    delayMs: null,
  });
});

test("best-time recommendation is derived from metrics and returns null without evidence", () => {
  const { recommendBestTime } = require("../src/domain/calendar");
  assert.equal(recommendBestTime([]), null);
  const result = recommendBestTime([
    { localHour: 9, engagements: 10, impressions: 100 },
    { localHour: 18, engagements: 30, impressions: 150 },
    { localHour: 18, engagements: 10, impressions: 50 },
  ]);
  assert.equal(result.localHour, 18);
  assert.equal(result.engagementRate, 0.2);
  assert.equal(result.sampleSize, 2);
});
