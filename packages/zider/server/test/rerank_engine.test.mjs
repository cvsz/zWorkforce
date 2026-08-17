import assert from "node:assert/strict";
import test from "node:test";
import { RerankEngine, YouTubeSync } from "../src/rerank_engine.mjs";

test("RerankEngine ranks relevant chunks and applies threshold", () => {
  const engine = new RerankEngine({ topK: 2, minScore: 0.55 });
  const chunks = [
    { id: "c1", text: "Direct Preference Optimization algorithm for LLMs", baseScore: 0.8 },
    { id: "c2", text: "Random unrelated weather report in Seattle", baseScore: 0.2 },
    { id: "c3", text: "Optimization techniques for reinforcement learning", baseScore: 0.7 },
  ];

  const results = engine.rerankChunks("Optimization", chunks);
  assert.equal(results.length, 2);
  assert.equal(results[0].id, "c1");
});

test("YouTubeSync synchronizes playback time with subtitle cues", () => {
  const sync = new YouTubeSync();
  sync.loadTranscript([
    { start: 0, duration: 5, text: "Introduction to AI Workforces" },
    { start: 5.1, duration: 4.9, text: "Deep dive into model routers" },
  ]);

  const cue = sync.getCurrentCue(3.2);
  assert.ok(cue);
  assert.equal(cue.text, "Introduction to AI Workforces");

  const none = sync.getCurrentCue(15.0);
  assert.equal(none, null);
});
