/**
 * AI Auto-Poster for Zeto
 * ──────────────────────────────────────────────────────────────────────────────
 * Posts AI-generated "learn how to" content to Facebook every ~3 hours with
 * randomized timing to appear organic (±0-30 min jitter per cycle).
 */

const db = require("./db");
const { generateContent } = require("./contentGenerator");
const fbController = require("./fbController");
const { evaluateAutopilot } = require("./domain/autopilotPolicy");

// ── Jitter ─────────────────────────────────────────────────────────────────────
const JITTER_MAX_MS = 30 * 60 * 1000; // 30 minutes
const randomJitter = () => Math.floor(Math.random() * JITTER_MAX_MS);

// ── AI Auto-Post job ──────────────────────────────────────────────────────────

/**
 * Run one AI generation + Facebook post cycle.
 */
async function runAiAutoPost(opts = {}) {
  const pageIdContext = opts.pageId || "default";
  const settings = await db.settings.get();
  const aiSettings = settings.aiAutoPoster || {};

  if (settings.killSwitch || settings.autopilotKillSwitch) {
    return { blocked: true, reasons: ["emergency_kill_switch_active"] };
  }

  const options = {
    tag: opts.tag || aiSettings.topicTag || undefined,
    format: opts.format || aiSettings.postFormat || undefined,
    withImage:
      opts.withImage !== undefined
        ? opts.withImage
        : aiSettings.withImage !== false,
    provider: opts.provider || aiSettings.provider || "auto",
    dryRun: opts.dryRun || false,
    pageId: pageIdContext,
  };

  console.log(`[ai-autoposter:${pageIdContext}] Generating content...`, {
    tag: options.tag,
    format: options.format,
    provider: options.provider,
  });

  let generated;
  try {
    generated = await generateContent(options);
    console.log(
      `[ai-autoposter:${pageIdContext}] Generated (${generated.provider}): topic=${generated.topic.tag}, format=${generated.format}`,
    );
  } catch (e) {
    const msg = `Content generation failed: ${e.message}`;
    console.error(`[ai-autoposter:${pageIdContext}]`, msg);
    await db.history.add({
      type: "ai-auto",
      status: "error",
      error: msg,
      source: `[ai-autoposter:${pageIdContext}]`,
      pageId: pageIdContext,
    });
    throw e;
  }

  if (options.dryRun) {
    console.log(`[ai-autoposter:${pageIdContext}] DRY RUN — not posting`);
    return { dryRun: true, generated };
  }

  // Approval can be bypassed only when every autonomous safety gate passes.
  const requireApproval = aiSettings.requireApproval !== false;
  const autopilot = evaluateAutopilot({
    autoPilot: !requireApproval && aiSettings.autoPilot === true,
    killSwitch: settings.killSwitch || settings.autopilotKillSwitch,
    qaScore: generated.qaScore,
    platformPermitted: aiSettings.platformPermitted === true,
    estimatedCost: generated.estimatedCost,
    remainingBudget: aiSettings.remainingBudget,
    postsInWindow: aiSettings.postsInWindow,
    postingFrequencyCap: aiSettings.postingFrequencyCap,
    claimsSubstantiated: generated.claimsSubstantiated === true,
    copyrightCleared: generated.copyrightCleared === true,
  });

  if (requireApproval || !autopilot.allowed) {
    console.log(
      `[ai-autoposter:${pageIdContext}] Route to queue pending_review: approval flow is active.`,
    );
    const queued = await db.queue.add({
      message: generated.message,
      imageUrl: generated.imageUrl || null,
      type: generated.imageUrl ? "photo" : "text",
      source: requireApproval
        ? "ai-autoposter-approval"
        : "ai-autoposter-policy-blocked",
      topic: generated.topic,
      format: generated.format,
      aiProvider: generated.provider,
      status: "pending_review",
      pageId: pageIdContext,
    });

    await db.history.add({
      type: "ai-auto",
      message: generated.message.substring(0, 120),
      status: "pending_review",
      source: `[ai-autoposter:${pageIdContext}]`,
      topic: generated.topic.tag,
      queueId: queued.id,
      pageId: pageIdContext,
    });

    // Send Line / Discord Notifications (Non-blocking)
    const { sendNotification } = require("./notification");
    const previewMessage = `📢 [Zeto:${pageIdContext}] New AI content generated & awaiting approval!\n\nTopic: ${generated.topic.emoji} ${generated.topic.th}\nFormat: ${generated.format}\nProvider: ${generated.provider}\n\n"${generated.message.substring(0, 150)}..."\n\nApprove via dashboard: https://${process.env.PRIMARY_DOMAIN || "localhost"}/settings`;
    sendNotification(previewMessage, generated.imageUrl).catch((err) => {
      console.error(
        `[ai-autoposter:${pageIdContext}] Notification delivery failed:`,
        err.message,
      );
    });

    return {
      queued: true,
      pendingApproval: true,
      queueId: queued.id,
      policyReasons: autopilot.reasons,
      generated,
    };
  }

  if (!(await fbController.isConfigured(pageIdContext))) {
    console.log(
      `[ai-autoposter:${pageIdContext}] Not posting — Facebook credentials not configured. Saving to queue instead.`,
    );
    const queued = await db.queue.add({
      message: generated.message,
      imageUrl: generated.imageUrl || null,
      type: generated.imageUrl ? "photo" : "text",
      source: "ai-autoposter",
      topic: generated.topic,
      format: generated.format,
      aiProvider: generated.provider,
      status: "pending",
      pageId: pageIdContext,
    });
    await db.history.add({
      type: "ai-auto",
      message: generated.message.substring(0, 120),
      status: "queued",
      source: `[ai-autoposter:${pageIdContext}]`,
      topic: generated.topic.tag,
      queueId: queued.id,
      pageId: pageIdContext,
    });
    return { queued: true, queueId: queued.id, generated };
  }

  const queued = await db.queue.add({
    message: generated.message,
    imageUrl: generated.imageUrl || null,
    type: generated.imageUrl ? "photo" : "text",
    source: "ai-autoposter-approved",
    topic: generated.topic,
    format: generated.format,
    aiProvider: generated.provider,
    status: "pending",
    pageId: pageIdContext,
  });
  return {
    queued: true,
    autoPilotApproved: true,
    queueId: queued.id,
    generated,
  };
}

// ── Cron schedule calculation ──────────────────────────────────────────────────

const AI_AUTOPOSTER_CRON = "0 0,3,6,9,12,15,18,21 * * *"; // every 3h on the hour

/**
 * The actual job wrapper — applies jitter before posting.
 */
async function aiAutoPostWithJitter(opts = {}) {
  const settings = await db.settings.get();
  const aiSettings = settings.aiAutoPoster || {};

  if (!aiSettings.enabled) {
    console.log("[ai-autoposter] Disabled in settings — skipping.");
    return;
  }

  const jitter = randomJitter();
  console.log(
    `[ai-autoposter] Waiting ${Math.round(jitter / 60000)}m jitter before posting...`,
  );

  await new Promise((resolve) => setTimeout(resolve, jitter));

  const pages = await db.pages.getAll();
  const enabledPages = pages.filter((p) => p.enabled !== false);
  if (enabledPages.length === 0) {
    try {
      await runAiAutoPost({ ...opts, pageId: "default" });
    } catch (error) {
      console.error("[ai-autoposter] Default page run failed:", error.message);
    }
    return;
  }

  for (const page of enabledPages) {
    try {
      await runAiAutoPost({ ...opts, pageId: page.id });
    } catch (e) {
      console.error(`[ai-autoposter] Failed for page ${page.id}:`, e.message);
    }
  }
}

module.exports = {
  runAiAutoPost,
  aiAutoPostWithJitter,
  AI_AUTOPOSTER_CRON,
};
