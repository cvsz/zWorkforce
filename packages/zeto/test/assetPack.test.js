const assert = require("node:assert/strict");
const test = require("node:test");

test("one idea produces a complete versioned M01-M05 draft asset pack", () => {
  const { createDraftAssetPack } = require("../src/domain/assetPackFactory");
  const pack = createDraftAssetPack({
    brand: "zato",
    idea: {
      title: "Three ways to validate niche-content demand",
      pillar: "practical education",
      persona: "new niche creator",
      pain: "uncertain audience demand",
      hook: "Validate before you spend",
      score: 88,
    },
    palette: ["#ffffff", "#e9d5ff"],
    platforms: ["facebook", "instagram"],
    image: {
      prompt: "clean editorial demand-validation checklist",
      negativePrompt: "clutter, illegible text",
      aspectRatio: "4:5",
      seed: "42",
    },
    video: {
      template: "reel",
      shots: [
        { start: 0, end: 3, description: "Hook" },
        { start: 3, end: 12, description: "Three validation steps" },
        { start: 12, end: 15, description: "CTA" },
      ],
    },
    audio: {
      mood: "confident",
      bpm: 108,
      lufs: -14,
      useCase: "short-form",
      license: "generated",
    },
    caption: {
      hook: "Validate your niche first.",
      body: "Use interviews, search intent, and a small test offer.",
      cta: "Which signal will you test?",
      hashtags: ["#NicheContent"],
    },
  });

  assert.equal(pack.idea.score, 88);
  assert.equal(pack.assets.length, 4);
  assert.ok(
    pack.assets.every(
      (asset) => asset.version === 1 && asset.status === "draft",
    ),
  );
  const image = pack.assets.find((asset) => asset.type === "image");
  assert.match(image.prompt_hash, /^[a-f0-9]{64}$/);
  assert.deepEqual(image.provenance.palette, ["#ffffff", "#e9d5ff"]);
  const video = pack.assets.find((asset) => asset.type === "video");
  assert.equal(video.spec.shots.at(-1).end, 15);
  const audio = pack.assets.find((asset) => asset.type === "audio");
  assert.equal(audio.provenance.license, "generated");
  assert.equal(pack.captions.length, 2);
  assert.ok(
    pack.captions.every(
      (caption) => caption.alt_text && caption.seo_description,
    ),
  );
});

test("asset pack rejects unsafe aspect ratios, audio, timelines, and caption overflow", () => {
  const { createDraftAssetPack } = require("../src/domain/assetPackFactory");
  const base = {
    brand: "zato",
    idea: {
      title: "Idea",
      pillar: "education",
      persona: "creator",
      pain: "time",
      hook: "Learn",
      score: 80,
    },
    palette: ["#ffffff"],
    platforms: ["facebook"],
    image: {
      prompt: "prompt",
      negativePrompt: "negative",
      aspectRatio: "7:3",
      seed: "1",
    },
    video: {
      template: "reel",
      shots: [{ start: 0, end: 3, description: "Hook" }],
    },
    audio: {
      mood: "calm",
      bpm: 100,
      lufs: -14,
      useCase: "reel",
      license: "generated",
    },
    caption: { hook: "Hook", body: "Body", cta: "CTA", hashtags: [] },
  };
  assert.throws(() => createDraftAssetPack(base), /aspect ratio/i);
  assert.throws(
    () =>
      createDraftAssetPack({
        ...base,
        image: { ...base.image, aspectRatio: "4:5" },
        audio: { ...base.audio, license: "unknown" },
      }),
    /generated audio/i,
  );
  assert.throws(
    () =>
      createDraftAssetPack({
        ...base,
        image: { ...base.image, aspectRatio: "4:5" },
        video: {
          template: "reel",
          shots: [{ start: 2, end: 1, description: "bad" }],
        },
      }),
    /shot timeline/i,
  );
});
