const axios = require("axios");
const db = require("./db");
const https = require("https");
const fs = require("fs");
const FormData = require("form-data");
const { assertSafeRemoteUrl } = require("./security/remoteUrlGuard");
const { assertImageFile } = require("./security/uploadValidation");
const { readSecret } = require("./security/secrets");
const {
  FacebookPublishingProvider,
} = require("./providers/facebookPublishingProvider");

const facebookProvider = new FacebookPublishingProvider();

const getPageContext = (arg) => {
  let pageId = null;
  if (arg && typeof arg === "object") {
    pageId =
      arg.headers?.["x-page-id"] || arg.query?.pageId || arg.body?.pageId;
  } else if (typeof arg === "string") {
    pageId = arg;
  }
  return pageId || "default";
};

const getAccessToken = async (context = null) => {
  const pageId = getPageContext(context);
  if (pageId && pageId !== "default") {
    const page = await db.pages.getById(pageId);
    if (page && page.facebookAccessToken) return page.facebookAccessToken;
  }
  const settings = await db.settings.get();
  if (
    settings.facebookAccessToken &&
    !settings.facebookAccessToken.includes("placeholder")
  ) {
    return settings.facebookAccessToken;
  }
  return readSecret("FACEBOOK_ACCESS_TOKEN");
};

const getPageId = async (context = null) => {
  const pageId = getPageContext(context);
  if (pageId && pageId !== "default") {
    const page = await db.pages.getById(pageId);
    if (page && page.facebookPageId) return page.facebookPageId;
  }
  const settings = await db.settings.get();
  return settings.facebookPageId || process.env.FACEBOOK_PAGE_ID;
};

const isConfigured = async (context = null) => {
  const pId = await getPageId(context);
  const token = await getAccessToken(context);
  return pId && token && !token.includes("placeholder");
};

const FB_VERSION = process.env.FB_API_VERSION || "v19.0";
const fbAxios = axios.create({
  baseURL: `https://graph.facebook.com/${FB_VERSION}`,
  httpsAgent:
    process.env.NODE_ENV !== "production"
      ? new https.Agent({ rejectUnauthorized: false })
      : undefined,
  timeout: 15000,
});

/** Helper: safe error response */
const fbError = (res, status, msg, raw) => {
  console.error(`[fbController] ${msg}`, raw || "");
  return res.status(status).json({
    ok: false,
    error: {
      code: "FB_API_ERROR",
      message: msg,
      detail: raw?.message || String(raw || ""),
    },
  });
};

const sanitizeSettings = (settings) => {
  const {
    facebookAccessToken,
    facebookUserAccessToken,
    lineNotifyToken,
    discordWebhookUrl,
    ...safe
  } = settings || {};
  return {
    ...safe,
    hasFacebookAccessToken: Boolean(facebookAccessToken),
    hasFacebookUserAccessToken: Boolean(facebookUserAccessToken),
    hasLineNotifyToken: Boolean(lineNotifyToken),
    hasDiscordWebhook: Boolean(discordWebhookUrl),
  };
};

const sanitizePage = (page) => {
  if (!page) return page;
  const { facebookAccessToken, facebookUserAccessToken, ...safe } = page;
  return {
    ...safe,
    hasAccessToken: Boolean(facebookAccessToken),
    hasUserAccessToken: Boolean(facebookUserAccessToken),
  };
};

/**
 * POST /api/facebook/post-message
 * Body: { message, link? }
 */
const postMessage = async (req, res) => {
  const { message, link } = req.body;
  if (!message || !message.trim()) {
    return res.status(400).json({
      ok: false,
      error: { code: "MISSING_MESSAGE", message: "message is required" },
    });
  }
  if (!(await isConfigured(req))) {
    return res.status(503).json({
      ok: false,
      error: {
        code: "NOT_CONFIGURED",
        message: "Facebook credentials are not configured",
      },
    });
  }

  const token = await getAccessToken(req);
  const pageId = await getPageId(req);
  const pageIdContext = getPageContext(req);

  try {
    const result = await facebookProvider.publish(
      { pageId, accessToken: token },
      {
        kind: "text",
        text: message.trim(),
        link,
        idempotencyKey:
          req.get("idempotency-key") || req.id || "legacy-request",
      },
    );

    await db.history.add({
      type: "text",
      message: message.trim(),
      postId: result.providerPublicationId,
      status: "success",
      pageId: pageIdContext,
    });

    return res.status(200).json({
      ok: true,
      data: {
        id: result.providerPublicationId,
        permalink: result.permalink,
        rateLimit: result.rateLimit,
      },
    });
  } catch (error) {
    const raw = error.response?.data?.error || error.message;
    await db.history.add({
      type: "text",
      message: message.trim(),
      status: "error",
      error: String(raw),
      pageId: pageIdContext,
    });
    return fbError(res, 500, raw?.message || "Failed to post message", raw);
  }
};

/**
 * POST /api/facebook/post-photo
 * Body: { url, message? } OR multipart with file
 */
const postPhoto = async (req, res) => {
  const { url, message } = req.body;
  const hasUpload = req.file;

  if (!url && !hasUpload) {
    return res.status(400).json({
      ok: false,
      error: {
        code: "MISSING_PHOTO",
        message: "url or file upload is required",
      },
    });
  }
  if (url) {
    try {
      await assertSafeRemoteUrl(url);
    } catch {
      return res.status(422).json({
        ok: false,
        error: {
          code: "UNSAFE_REMOTE_URL",
          message: "Remote URL is not allowed",
        },
      });
    }
  }
  if (hasUpload) {
    try {
      await assertImageFile(req.file.path);
    } catch {
      await fs.promises.unlink(req.file.path).catch(() => {});
      return res.status(422).json({
        ok: false,
        error: {
          code: "INVALID_IMAGE",
          message: "File is not a supported image",
        },
      });
    }
  }
  if (!(await isConfigured(req))) {
    if (hasUpload) await fs.promises.unlink(req.file.path).catch(() => {});
    return res.status(503).json({
      ok: false,
      error: {
        code: "NOT_CONFIGURED",
        message: "Facebook credentials are not configured",
      },
    });
  }

  const token = await getAccessToken(req);
  const pageId = await getPageId(req);
  const pageIdContext = getPageContext(req);

  try {
    let response;
    if (hasUpload) {
      // Upload from local file using form-data
      const form = new FormData();
      form.append(
        "source",
        fs.createReadStream(req.file.path),
        req.file.originalname,
      );
      if (message) form.append("message", message);
      response = await fbAxios.post(`/${pageId}/photos`, form, {
        headers: {
          ...form.getHeaders(),
          authorization: `Bearer ${token}`,
        },
        httpsAgent:
          process.env.NODE_ENV !== "production"
            ? new https.Agent({ rejectUnauthorized: false })
            : undefined,
      });
    } else {
      const result = await facebookProvider.publish(
        { pageId, accessToken: token },
        {
          kind: "image",
          mediaUrl: url,
          text: message || "",
          idempotencyKey:
            req.get("idempotency-key") || req.id || "legacy-request",
        },
      );
      response = {
        data: { id: result.providerPublicationId, permalink: result.permalink },
      };
    }

    // Upload to Google Drive if configured (Non-blocking)
    const { uploadToGoogleDrive } = require("./googleDrive");
    const sourceForDrive = hasUpload ? null : url;
    if (sourceForDrive) {
      uploadToGoogleDrive(
        sourceForDrive,
        `fb-photo-${response.data.id}.png`,
      ).catch((e) => {
        console.error(
          "[fbController] Non-blocking Google Drive upload failure:",
          e.message,
        );
      });
    }

    await db.history.add({
      type: "photo",
      message: message || "",
      status: "success",
      postId: response.data.id,
      pageId: pageIdContext,
    });

    return res.status(200).json({ ok: true, data: response.data });
  } catch (error) {
    const raw = error.response?.data?.error || error.message;
    await db.history.add({
      type: "photo",
      status: "error",
      error: String(raw),
      pageId: pageIdContext,
    });
    return fbError(res, 500, raw?.message || "Failed to post photo", raw);
  } finally {
    if (hasUpload) await fs.promises.unlink(req.file.path).catch(() => {});
  }
};

/**
 * GET /api/facebook/posts
 * Query: ?limit=10&fields=message,created_time,story
 */
const getPosts = async (req, res) => {
  if (!(await isConfigured(req))) {
    return res.status(503).json({
      ok: false,
      error: {
        code: "NOT_CONFIGURED",
        message: "Facebook credentials are not configured",
      },
    });
  }

  const token = await getAccessToken(req);
  const pageId = await getPageId(req);

  try {
    const limit = Math.min(parseInt(req.query.limit || "10", 10), 50);
    const fields =
      req.query.fields ||
      "message,created_time,story,full_picture,permalink_url";

    const response = await fbAxios.get(`/${pageId}/feed`, {
      params: { access_token: token, limit, fields },
    });

    return res.status(200).json({ ok: true, data: response.data });
  } catch (error) {
    const raw = error.response?.data?.error || error.message;
    return fbError(res, 500, raw?.message || "Failed to fetch posts", raw);
  }
};

/**
 * DELETE /api/facebook/posts/:postId
 */
const deletePost = async (req, res) => {
  const { postId } = req.params;
  if (!postId) {
    return res.status(400).json({
      ok: false,
      error: { code: "MISSING_ID", message: "postId is required" },
    });
  }
  if (!(await isConfigured(req))) {
    return res.status(503).json({
      ok: false,
      error: {
        code: "NOT_CONFIGURED",
        message: "Facebook credentials are not configured",
      },
    });
  }

  const token = await getAccessToken(req);
  const pageId = await getPageId(req);
  const pageIdContext = getPageContext(req);

  try {
    await facebookProvider.delete({ pageId, accessToken: token }, postId);

    await db.history.add({
      type: "delete",
      postId,
      status: "success",
      pageId: pageIdContext,
    });
    return res
      .status(200)
      .json({ ok: true, message: "Post deleted successfully" });
  } catch (error) {
    const raw = error.response?.data?.error || error.message;
    return fbError(res, 500, raw?.message || "Failed to delete post", raw);
  }
};

/**
 * GET /api/facebook/insights
 * Fetch page insights: fan count, followers, engagement
 */
const getInsights = async (req, res) => {
  if (!(await isConfigured(req))) {
    return res.status(200).json({
      ok: true,
      configured: false,
      data: { name: "Not Connected", fan_count: 0, followers_count: 0 },
    });
  }

  const token = await getAccessToken(req);
  const pageId = await getPageId(req);

  try {
    const [pageRes, insightsRes] = await Promise.allSettled([
      fbAxios.get(`/${pageId}`, {
        params: {
          fields: "fan_count,followers_count,name,about,category,picture",
          access_token: token,
        },
      }),
      fbAxios.get(`/${pageId}/insights`, {
        params: {
          metric: "page_impressions,page_engaged_users,page_post_engagements",
          period: "day",
          access_token: token,
        },
      }),
    ]);

    const pageData = pageRes.status === "fulfilled" ? pageRes.value.data : {};
    const insightsData =
      insightsRes.status === "fulfilled" ? insightsRes.value.data : {};

    return res.status(200).json({
      ok: true,
      configured: true,
      data: pageData,
      insights: insightsData,
    });
  } catch (error) {
    const raw = error.response?.data?.error || error.message;
    return fbError(res, 500, raw?.message || "Failed to fetch insights", raw);
  }
};

/**
 * GET /api/facebook/insights/history
 * Returns 30-day historical metrics: impressions, engaged_users, post_engagements
 * Query: ?days=30
 */
const getInsightsHistory = async (req, res) => {
  if (!(await isConfigured(req))) {
    return res.status(200).json({
      ok: true,
      configured: false,
      data: {
        labels: [],
        impressions: [],
        engagedUsers: [],
        postEngagements: [],
      },
    });
  }

  const token = await getAccessToken(req);
  const pageId = await getPageId(req);
  const days = Math.min(parseInt(req.query.days || "30", 10), 90);

  // Calculate since/until unix timestamps
  const until = Math.floor(Date.now() / 1000);
  const since = until - days * 24 * 60 * 60;

  try {
    const response = await fbAxios.get(`/${pageId}/insights`, {
      params: {
        metric: "page_impressions,page_engaged_users,page_post_engagements",
        period: "day",
        since,
        until,
        access_token: token,
      },
    });

    const metricsRaw = response.data?.data || [];

    // Parse metric arrays into labeled series
    const findMetric = (name) => {
      const m = metricsRaw.find((x) => x.name === name);
      return m ? m.values || [] : [];
    };

    const impressionsValues = findMetric("page_impressions");
    const engagedValues = findMetric("page_engaged_users");
    const postEngagementsValues = findMetric("page_post_engagements");

    // Use impressions as the label source (all metrics share same timeline)
    const labels = impressionsValues.map((v) => {
      const d = new Date(v.end_time);
      return `${d.getMonth() + 1}/${d.getDate()}`;
    });

    return res.status(200).json({
      ok: true,
      configured: true,
      data: {
        labels,
        impressions: impressionsValues.map((v) => v.value || 0),
        engagedUsers: engagedValues.map((v) => v.value || 0),
        postEngagements: postEngagementsValues.map((v) => v.value || 0),
      },
    });
  } catch (error) {
    const raw = error.response?.data?.error || error.message;
    return fbError(
      res,
      500,
      raw?.message || "Failed to fetch insights history",
      raw,
    );
  }
};

/**
 * GET /api/facebook/posts/top
 * Returns Top 5 posts ranked by total engagement (likes + comments + shares)
 * Query: ?limit=20 (pool of posts to rank from)
 */
const getTopPosts = async (req, res) => {
  if (!(await isConfigured(req))) {
    return res.status(200).json({ ok: true, configured: false, data: [] });
  }

  const token = await getAccessToken(req);
  const pageId = await getPageId(req);
  const pool = Math.min(parseInt(req.query.limit || "25", 10), 50);

  try {
    const response = await fbAxios.get(`/${pageId}/feed`, {
      params: {
        access_token: token,
        limit: pool,
        fields:
          "id,message,story,created_time,permalink_url,full_picture,likes.summary(true),comments.summary(true),shares",
      },
    });

    const posts = response.data?.data || [];

    // Compute engagement score per post
    const ranked = posts
      .map((post) => {
        const likes = post.likes?.summary?.total_count || 0;
        const comments = post.comments?.summary?.total_count || 0;
        const shares = post.shares?.count || 0;
        const engagement = likes + comments + shares;
        return {
          id: post.id,
          message: post.message || post.story || "(No text)",
          createdTime: post.created_time,
          permalink: post.permalink_url || null,
          thumbnail: post.full_picture || null,
          likes,
          comments,
          shares,
          engagement,
        };
      })
      .sort((a, b) => b.engagement - a.engagement)
      .slice(0, 5);

    return res.status(200).json({ ok: true, configured: true, data: ranked });
  } catch (error) {
    const raw = error.response?.data?.error || error.message;
    return fbError(res, 500, raw?.message || "Failed to fetch top posts", raw);
  }
};

/**
 * GET /api/facebook/config
 */
const getConfig = async (req, res) => {
  const settings = await db.settings.get();
  const token = await getAccessToken(req);
  const pageId = await getPageId(req);
  const pageIdContext = getPageContext(req);
  const queue = await db.queue.getAll(pageIdContext);
  const pending = await db.queue.getPending(pageIdContext);

  return res.status(200).json({
    ok: true,
    data: {
      pageId: pageId || null,
      hasAccessToken: !!token && !token.includes("placeholder"),
      schedulerEnabled: settings.schedulerEnabled,
      defaultCron: settings.defaultCron,
      queueLength: queue.length,
      pendingCount: pending.length,
    },
  });
};

// ── Token Management & Auto-Refresh API ──────────────────────────────────────

/**
 * POST /api/facebook/exchange-token
 * Body: { shortLivedToken }
 */
const exchangeToken = async (req, res) => {
  const { shortLivedToken } = req.body;
  if (!shortLivedToken) {
    return res.status(400).json({
      ok: false,
      error: {
        code: "MISSING_TOKEN",
        message: "shortLivedToken is required",
      },
    });
  }

  const appId = process.env.FACEBOOK_APP_ID;
  const appSecret = readSecret("FACEBOOK_APP_SECRET");
  const pageId = await getPageId(req);
  const pageIdContext = getPageContext(req);

  if (!appId || !appSecret) {
    return res.status(503).json({
      ok: false,
      error: {
        code: "APP_CREDENTIALS_MISSING",
        message:
          "FACEBOOK_APP_ID and FACEBOOK_APP_SECRET are not configured on the server environment",
      },
    });
  }

  try {
    console.log(
      "[fbController] Exchanging short-lived user token for long-lived user token...",
    );
    const userTokenRes = await fbAxios.get("/oauth/access_token", {
      params: {
        grant_type: "fb_exchange_token",
        client_id: appId,
        client_secret: appSecret,
        fb_exchange_token: shortLivedToken,
      },
    });

    const longLivedUserToken = userTokenRes.data.access_token;
    if (!longLivedUserToken) {
      throw new Error("Failed to retrieve long-lived user access token");
    }

    console.log("[fbController] Fetching long-lived page access tokens...");
    const accountsRes = await fbAxios.get("/me/accounts", {
      params: {
        access_token: longLivedUserToken,
        limit: 100,
      },
    });

    const pagesList = accountsRes.data.data || [];
    const targetPage = pagesList.find((p) => p.id === pageId);

    if (!targetPage) {
      return res.status(404).json({
        ok: false,
        error: {
          code: "PAGE_NOT_FOUND",
          message: `The configured Facebook Page ID (${pageId}) was not found in the accounts list for this user token. Available pages: ${pagesList.map((p) => p.name).join(", ")}`,
        },
      });
    }

    const pageAccessToken = targetPage.access_token;

    // Save tokens in DB Settings or Page configuration
    if (pageIdContext && pageIdContext !== "default") {
      await db.pages.update(pageIdContext, {
        facebookAccessToken: pageAccessToken,
        facebookUserAccessToken: longLivedUserToken,
        facebookTokenRefreshedAt: new Date().toISOString(),
      });
    } else {
      await db.settings.update({
        facebookAccessToken: pageAccessToken,
        facebookUserAccessToken: longLivedUserToken,
        facebookTokenRefreshedAt: new Date().toISOString(),
        facebookTokenExpiresAt: userTokenRes.data.expires_in
          ? new Date(
              Date.now() + userTokenRes.data.expires_in * 1000,
            ).toISOString()
          : null,
      });
    }

    console.log(
      "[fbController] Successfully exchanged and saved page access token.",
    );
    return res.status(200).json({
      ok: true,
      message: "Token exchanged and saved successfully",
      data: {
        pageName: targetPage.name,
        pageId: targetPage.id,
        refreshedAt: new Date().toISOString(),
      },
    });
  } catch (error) {
    const raw = error.response?.data?.error || error.message;
    return fbError(
      res,
      500,
      "Token exchange flow failed: " + (raw?.message || error.message),
      raw,
    );
  }
};

/**
 * POST /api/facebook/refresh-token
 */
const refreshToken = async (req, res) => {
  const pageIdContext = getPageContext(req);
  let savedUserToken;

  if (pageIdContext && pageIdContext !== "default") {
    const p = await db.pages.getById(pageIdContext);
    savedUserToken = p?.facebookUserAccessToken;
  } else {
    savedUserToken = (await db.settings.get()).facebookUserAccessToken;
  }

  const pageId = await getPageId(req);

  if (!savedUserToken) {
    return res.status(400).json({
      ok: false,
      error: {
        code: "NO_SAVED_USER_TOKEN",
        message:
          "No saved Long-Lived User Token found. Please authenticate via OAuth flow first.",
      },
    });
  }

  try {
    console.log(
      "[fbController] Refreshing Page Token using stored User Token...",
    );
    const accountsRes = await fbAxios.get("/me/accounts", {
      params: {
        access_token: savedUserToken,
        limit: 100,
      },
    });

    const pagesList = accountsRes.data.data || [];
    const targetPage = pagesList.find((p) => p.id === pageId);

    if (!targetPage) {
      return res.status(404).json({
        ok: false,
        error: {
          code: "PAGE_NOT_FOUND",
          message: `Facebook Page ID ${pageId} not found in accounts listing during refresh.`,
        },
      });
    }

    if (pageIdContext && pageIdContext !== "default") {
      await db.pages.update(pageIdContext, {
        facebookAccessToken: targetPage.access_token,
        facebookTokenRefreshedAt: new Date().toISOString(),
      });
    } else {
      await db.settings.update({
        facebookAccessToken: targetPage.access_token,
        facebookTokenRefreshedAt: new Date().toISOString(),
      });
    }

    console.log("[fbController] Page Token refreshed successfully.");
    return res.status(200).json({
      ok: true,
      message: "Page token refreshed successfully",
      data: {
        pageName: targetPage.name,
        refreshedAt: new Date().toISOString(),
      },
    });
  } catch (error) {
    const raw = error.response?.data?.error || error.message;
    return fbError(
      res,
      500,
      "Page token refresh failed: " + (raw?.message || error.message),
      raw,
    );
  }
};

/**
 * GET /api/queue
 */
const getQueue = async (req, res) => {
  return res
    .status(200)
    .json({ ok: true, data: await db.queue.getAll(getPageContext(req)) });
};

/**
 * GET /api/queue/pending-review
 */
const getPendingReview = async (req, res) => {
  return res.status(200).json({
    ok: true,
    data: await db.queue.getPendingReview(getPageContext(req)),
  });
};

/**
 * POST /api/queue/:id/approve
 */
const approveQueueItem = async (req, res) => {
  const { id } = req.params;
  const { message } = req.body;
  const approved = await db.queue.approve(id, message);
  if (!approved) {
    return res.status(404).json({
      ok: false,
      error: { code: "NOT_FOUND", message: "Queue item not found" },
    });
  }
  await db.history.add({
    type: "queue-approval",
    message: message || approved.message,
    status: "success",
    source: "[approval]",
    pageId: approved.pageId,
  });
  return res.status(200).json({ ok: true, data: approved });
};

/**
 * POST /api/queue
 */
const addToQueue = async (req, res) => {
  const { message, imageUrl, scheduledAt, status } = req.body;
  if (!message || !message.trim()) {
    return res.status(400).json({
      ok: false,
      error: { code: "MISSING_MESSAGE", message: "message is required" },
    });
  }
  if (imageUrl) {
    try {
      await assertSafeRemoteUrl(imageUrl);
    } catch {
      return res.status(422).json({
        ok: false,
        error: {
          code: "UNSAFE_REMOTE_URL",
          message: "Remote URL is not allowed",
        },
      });
    }
  }

  const entry = await db.queue.add({
    message: message.trim(),
    imageUrl: imageUrl || null,
    scheduledAt: scheduledAt || null,
    type: imageUrl ? "photo" : "text",
    status: status || "pending",
    pageId: getPageContext(req),
  });

  return res.status(201).json({ ok: true, data: entry });
};

/**
 * DELETE /api/queue/:id
 */
const removeFromQueue = async (req, res) => {
  const { id } = req.params;
  const cancelled = await db.queue.cancel(id);
  if (!cancelled) {
    return res.status(404).json({
      ok: false,
      error: { code: "NOT_FOUND", message: "Queue item not found" },
    });
  }
  return res.status(200).json({ ok: true, data: cancelled });
};

const retryQueueItem = async (req, res) => {
  const retried = await db.queue.retry(req.params.id);
  if (!retried) {
    return res.status(409).json({
      ok: false,
      error: {
        code: "NOT_RETRYABLE",
        message: "Queue item is not in a retryable state",
      },
    });
  }
  return res.status(200).json({ ok: true, data: retried });
};

/**
 * DELETE /api/queue
 */
const clearQueue = async (req, res) => {
  await db.queue.clear(getPageContext(req));
  return res.status(200).json({ ok: true, message: "Queue cleared" });
};

/**
 * POST /api/queue/:id/publish
 */
const publishQueueItem = async (req, res) => {
  const { id } = req.params;
  const candidate = await db.queue.getById(id);
  if (!candidate) {
    return res.status(404).json({
      ok: false,
      error: { code: "NOT_FOUND", message: "Queue item not found" },
    });
  }
  if (!(await isConfigured(candidate.pageId))) {
    return res.status(503).json({
      ok: false,
      error: {
        code: "NOT_CONFIGURED",
        message: "Facebook credentials are not configured",
      },
    });
  }

  const item = await db.queue.claimById(id);
  if (!item) {
    return res.status(409).json({
      ok: false,
      error: {
        code: "NOT_PUBLISHABLE",
        message: "Queue item is already claimed or no longer pending",
      },
    });
  }

  const token = await getAccessToken(item.pageId);
  const pageId = await getPageId(item.pageId);

  try {
    if (item.imageUrl) await assertSafeRemoteUrl(item.imageUrl);
    const published = await facebookProvider.publish(
      { pageId, accessToken: token },
      {
        kind: item.imageUrl ? "image" : "text",
        mediaUrl: item.imageUrl,
        text: item.message,
        idempotencyKey: `queue:${item.id}`,
      },
    );
    const response = {
      data: {
        id: published.providerPublicationId,
        permalink: published.permalink,
      },
    };

    await db.queue.updateStatus(id, "published", {
      publishedAt: new Date().toISOString(),
      postId: response.data.id,
    });
    await db.history.add({
      type: item.type,
      message: item.message,
      status: "success",
      postId: response.data.id,
      pageId: item.pageId,
    });

    return res
      .status(200)
      .json({ ok: true, data: { queueItem: item, postResult: response.data } });
  } catch (error) {
    const raw = error.response?.data?.error || error.message;
    await db.queue.updateStatus(id, "error", { error: String(raw) });
    return fbError(
      res,
      500,
      raw?.message || "Failed to publish queue item",
      raw,
    );
  }
};

// ── History API ───────────────────────────────────────────────────────────────

const getHistory = async (req, res) => {
  const limit = parseInt(req.query.limit || "50", 10);
  return res.status(200).json({
    ok: true,
    data: await db.history.getAll(getPageContext(req), limit),
  });
};

// ── Scheduler API ─────────────────────────────────────────────────────────────

const getSchedules = async (req, res) => {
  return res
    .status(200)
    .json({ ok: true, data: await db.schedules.getAll(getPageContext(req)) });
};

const addSchedule = async (req, res) => {
  const { name, cron, message } = req.body;
  if (!name || !cron || !message) {
    return res.status(400).json({
      ok: false,
      error: {
        code: "VALIDATION_ERROR",
        message: "name, cron, and message are required",
      },
    });
  }

  const entry = await db.schedules.add({
    name,
    cron,
    message,
    imageUrl: req.body.imageUrl || null,
    pageId: getPageContext(req),
  });
  return res.status(201).json({ ok: true, data: entry });
};

const updateSchedule = async (req, res) => {
  const { id } = req.params;
  const updated = await db.schedules.update(id, req.body);
  if (!updated) {
    return res.status(404).json({
      ok: false,
      error: { code: "NOT_FOUND", message: "Schedule not found" },
    });
  }
  return res.status(200).json({ ok: true, data: updated });
};

const removeSchedule = async (req, res) => {
  const { id } = req.params;
  const removed = await db.schedules.remove(id);
  if (!removed) {
    return res.status(404).json({
      ok: false,
      error: { code: "NOT_FOUND", message: "Schedule not found" },
    });
  }
  return res.status(200).json({ ok: true, data: removed });
};

// ── Settings API ──────────────────────────────────────────────────────────────

const getSettings = async (req, res) => {
  return res
    .status(200)
    .json({ ok: true, data: sanitizeSettings(await db.settings.get()) });
};

const updateSettings = async (req, res) => {
  const allowed = [
    "defaultCron",
    "schedulerEnabled",
    "autoPostTemplate",
    "maxQueueSize",
    "facebookPageId",
    "facebookAccessToken",
  ];
  const updates = {};
  for (const k of allowed) {
    if (req.body[k] !== undefined) updates[k] = req.body[k];
  }
  const updated = await db.settings.update(updates);
  return res.status(200).json({ ok: true, data: sanitizeSettings(updated) });
};

// ── Pages API ─────────────────────────────────────────────────────────────

const getPages = async (req, res) => {
  return res
    .status(200)
    .json({ ok: true, data: (await db.pages.getAll()).map(sanitizePage) });
};

const addPage = async (req, res) => {
  const { facebookPageId, facebookAccessToken, name } = req.body;
  if (!facebookPageId || !facebookAccessToken) {
    return res.status(400).json({
      ok: false,
      error: {
        code: "VALIDATION_ERROR",
        message: "facebookPageId and facebookAccessToken are required",
      },
    });
  }

  let pageName = name || "Facebook Page";
  try {
    const response = await fbAxios.get(`/${facebookPageId}`, {
      params: { fields: "name", access_token: facebookAccessToken },
    });
    if (response.data?.name) pageName = response.data.name;
  } catch (err) {
    console.warn(
      `[fbController] Failed to fetch page details from FB API: ${err.message}`,
    );
  }

  const entry = await db.pages.add({
    facebookPageId,
    facebookAccessToken,
    name: pageName,
  });

  return res.status(201).json({ ok: true, data: sanitizePage(entry) });
};

const updatePage = async (req, res) => {
  const { id } = req.params;
  const updated = await db.pages.update(id, req.body);
  if (!updated) {
    return res.status(404).json({
      ok: false,
      error: { code: "NOT_FOUND", message: "Page not found" },
    });
  }
  return res.status(200).json({ ok: true, data: sanitizePage(updated) });
};

const deletePage = async (req, res) => {
  const { id } = req.params;
  const removed = await db.pages.remove(id);
  if (!removed) {
    return res.status(404).json({
      ok: false,
      error: { code: "NOT_FOUND", message: "Page not found" },
    });
  }
  return res.status(200).json({ ok: true, data: sanitizePage(removed) });
};

module.exports = {
  postMessage,
  postPhoto,
  getPosts,
  deletePost,
  getInsights,
  getInsightsHistory,
  getTopPosts,
  getConfig,
  getQueue,
  getPendingReview,
  approveQueueItem,
  addToQueue,
  removeFromQueue,
  retryQueueItem,
  clearQueue,
  publishQueueItem,
  getHistory,
  getSchedules,
  addSchedule,
  updateSchedule,
  removeSchedule,
  getSettings,
  updateSettings,
  exchangeToken,
  refreshToken,
  getAccessToken,
  getPageId,
  isConfigured,
  getPageContext,
  getPages,
  addPage,
  updatePage,
  deletePage,
};
