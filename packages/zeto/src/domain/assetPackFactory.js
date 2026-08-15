const { createHash, randomUUID } = require("node:crypto");

const ASPECT_RATIOS = new Set(["1:1", "4:5", "9:16", "16:9"]);
const CAPTION_LIMITS = {
  facebook: 63206,
  instagram: 2200,
  tiktok: 2200,
  youtube: 5000,
  x: 280,
  linkedin: 3000,
};

function hash(value) {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function baseAsset(type, promptHash, extra = {}) {
  return {
    id: randomUUID(),
    type,
    prompt_hash: promptHash,
    tags: [],
    score: 0,
    status: "draft",
    version: 1,
    ...extra,
  };
}

function createDraftAssetPack(input) {
  if (!ASPECT_RATIOS.has(input.image.aspectRatio))
    throw new Error("Unsupported image aspect ratio");
  if (input.audio.license !== "generated")
    throw new Error("Only generated audio is allowed");
  if (
    !Number.isFinite(input.audio.lufs) ||
    input.audio.lufs < -24 ||
    input.audio.lufs > -6
  ) {
    throw new Error("Audio LUFS must be between -24 and -6");
  }
  if (
    !Number.isFinite(input.audio.bpm) ||
    input.audio.bpm < 30 ||
    input.audio.bpm > 300
  ) {
    throw new Error("Audio BPM must be between 30 and 300");
  }
  if (
    !Array.isArray(input.video.shots) ||
    input.video.shots.length === 0 ||
    input.video.shots.some(
      (shot, index) =>
        !Number.isFinite(shot.start) ||
        !Number.isFinite(shot.end) ||
        shot.start < 0 ||
        shot.end <= shot.start ||
        (index > 0 && shot.start < input.video.shots[index - 1].end),
    )
  ) {
    throw new Error("Invalid video shot timeline");
  }
  if (!input.caption.hook || !input.caption.cta)
    throw new Error("Caption hook and CTA are required");

  const image = baseAsset("image", hash(input.image), {
    seed: input.image.seed,
    brand_delta_e: null,
    aspect_ratio: input.image.aspectRatio,
    spec: {
      prompt: input.image.prompt,
      negative_prompt: input.image.negativePrompt,
    },
    provenance: { palette: input.palette, seed: input.image.seed },
  });
  const video = baseAsset("video", hash(input.video), {
    aspect_ratio: "9:16",
    spec: { ...input.video, captions_required: true, cta_required: true },
    provenance: { template: input.video.template },
  });
  const audio = baseAsset("audio", hash(input.audio), {
    lufs: input.audio.lufs,
    tags: [input.audio.mood, `${input.audio.bpm}bpm`, input.audio.useCase],
    spec: input.audio,
    provenance: { license: input.audio.license, generated: true },
  });
  const captionText =
    `${input.caption.hook}\n\n${input.caption.body}\n\n${input.caption.cta}\n${input.caption.hashtags.join(" ")}`.trim();
  const captionAsset = baseAsset("caption", hash(input.caption), {
    spec: input.caption,
    provenance: { source_idea: input.idea.title },
  });
  const captions = input.platforms.map((platform) => {
    const limit = CAPTION_LIMITS[platform];
    if (!limit) throw new Error(`Unsupported caption platform: ${platform}`);
    if (captionText.length > limit)
      throw new Error(`${platform} caption exceeds character limit`);
    return {
      id: randomUUID(),
      asset_id: captionAsset.id,
      platform,
      body: captionText,
      hook: input.caption.hook,
      cta: input.caption.cta,
      hashtags: input.caption.hashtags,
      alt_text: `${input.idea.title}: ${input.image.prompt}`,
      seo_description: `${input.idea.title} for ${input.idea.persona}`,
      version: 1,
    };
  });
  return {
    id: randomUUID(),
    brand: input.brand,
    idea: { ...input.idea, status: "selected", version: 1 },
    assets: [image, video, audio, captionAsset],
    captions,
    approval_required: true,
    created_at: new Date().toISOString(),
  };
}

module.exports = { createDraftAssetPack };
