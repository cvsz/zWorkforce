const express = require("express");
const dotenv = require("dotenv");
const path = require("path");
const multer = require("multer");
const os = require("os");
const helmet = require("helmet");
const { rateLimit } = require("express-rate-limit");
const pinoHttp = require("pino-http");
const db = require("./db");
const packageJson = require("../package.json");
const { createPool } = require("./database/pool");
const { migrate } = require("./database/migrate");
const { createV1Router } = require("./api/v1");
const {
  MetricsRegistry,
  collectOperationalMetrics,
} = require("./observability/metrics");
const { readSecret } = require("./security/secrets");
const { buildZarvisState } = require("./zarvisView");

dotenv.config();

const app = express();
const port = process.env.PORT || 5000;
const databasePool = process.env.DATABASE_URL ? createPool() : null;
let ready = false;
const metrics = new MetricsRegistry();

// ── Middleware ────────────────────────────────────────────────────────────────
app.disable("x-powered-by");
app.set("trust proxy", Number(process.env.TRUST_PROXY_HOPS || 0));
app.use(helmet({ contentSecurityPolicy: false }));
app.use(
  pinoHttp({
    level: process.env.LOG_LEVEL || "info",
    autoLogging: {
      ignore: (req) => req.url === "/health" || req.url === "/ready",
    },
    redact: [
      "req.headers.authorization",
      "req.headers.cookie",
      "req.body.password",
      "req.body.token",
    ],
    serializers: {
      req: (req) => ({
        id: req.id,
        method: req.method,
        url: req.url,
        remoteAddress: req.remoteAddress,
      }),
      res: (res) => ({ statusCode: res.statusCode }),
    },
  }),
);
app.use(
  rateLimit({
    windowMs: Number(process.env.RATE_LIMIT_WINDOW_MS || 60000),
    limit: Number(process.env.RATE_LIMIT_MAX || 300),
    standardHeaders: "draft-8",
    legacyHeaders: false,
    skip: (req) => req.path === "/health" || req.path === "/ready",
  }),
);
app.use(express.json({ limit: "1mb" }));
app.use(express.urlencoded({ extended: true, limit: "1mb" }));
app.use((req, res, next) => {
  const timeoutMs = Number(process.env.REQUEST_TIMEOUT_MS || 30000);
  req.setTimeout(timeoutMs);
  res.setTimeout(timeoutMs, () => {
    if (!res.headersSent) {
      res.status(503).json({
        ok: false,
        error: { code: "REQUEST_TIMEOUT", message: "Request timed out" },
      });
    } else {
      res.destroy();
    }
  });
  next();
});
app.use((req, res, next) => {
  const started = process.hrtime.bigint();
  res.once("finish", () => {
    const route =
      req.route?.path ||
      (req.path === "/ready" || req.path === "/health"
        ? req.path
        : "unmatched");
    metrics.observeHttp(
      req.method,
      route,
      res.statusCode,
      Number(process.hrtime.bigint() - started) / 1e9,
    );
  });
  next();
});

// Serve static files from public directory
app.use(express.static(path.join(__dirname, "../public")));

// File upload handling (temp dir, max 10MB)
const upload = multer({
  dest: os.tmpdir(),
  limits: { fileSize: 10 * 1024 * 1024 },
  fileFilter: (req, file, cb) => {
    const allowed = ["image/jpeg", "image/png", "image/gif", "image/webp"];
    if (allowed.includes(file.mimetype)) cb(null, true);
    else cb(new Error("Only image files are allowed"));
  },
});

// ── Auth Middleware & Role Checks ────────────────────────────────────────────
const authMiddleware = async (req, res, next) => {
  // Allow login endpoint without auth
  if (req.path === "/auth/login" || req.path === "/api/auth/login") {
    return next();
  }

  const authHeader = req.headers["authorization"];
  if (!authHeader || !authHeader.startsWith("Bearer ")) {
    return res.status(401).json({
      ok: false,
      error: { code: "UNAUTHORIZED", message: "Authentication required" },
    });
  }

  try {
    const token = authHeader.substring(7);
    const session = await db.sessions.get(token);
    if (!session) {
      return res.status(401).json({
        ok: false,
        error: {
          code: "UNAUTHORIZED",
          message: "Invalid or expired session token",
        },
      });
    }
    req.user = session;
    return next();
  } catch (error) {
    return next(error);
  }
};

const requireRole = (allowedRoles) => {
  return (req, res, next) => {
    if (!req.user || !allowedRoles.includes(req.user.role)) {
      return res.status(403).json({
        ok: false,
        error: {
          code: "FORBIDDEN",
          message: "Access denied: insufficient permissions",
        },
      });
    }
    next();
  };
};

// Mount Auth globally for all /api endpoints
app.use("/api", authMiddleware);

// ── Controllers ───────────────────────────────────────────────────────────────
const fb = require("./fbController");
const scheduler = require("./scheduler");

// ── Routes ────────────────────────────────────────────────────────────────────

// Health
app.get("/health", (req, res) => {
  res.status(200).json({
    ok: true,
    service: "zeto",
    version: packageJson.version,
    environment: process.env.NODE_ENV || "development",
    uptime: Math.floor(process.uptime()),
    scheduler: scheduler.getStatus(),
  });
});

app.get("/ready", async (_req, res) => {
  if (!databasePool || !ready) return res.status(503).json({ ready: false });
  try {
    await databasePool.query("SELECT 1");
    return res.status(200).json({ ready: true });
  } catch {
    return res.status(503).json({ ready: false });
  }
});

app.get("/metrics", async (req, res, next) => {
  try {
    const expected = readSecret("METRICS_TOKEN");
    const supplied = (req.get("authorization") || "").replace(/^Bearer /, "");
    if (!expected || supplied !== expected)
      return res.status(401).send("Unauthorized\n");
    const snapshot = await collectOperationalMetrics(databasePool);
    return res.type("text/plain; version=0.0.4").send(metrics.render(snapshot));
  } catch (error) {
    return next(error);
  }
});

// Auth Endpoints
app.post("/api/auth/login", async (req, res, next) => {
  const { username, password } = req.body;
  if (!username || !password) {
    return res.status(400).json({
      ok: false,
      error: { message: "Username and password are required" },
    });
  }
  try {
    const user = await db.users.getByUsername(username);
    if (!user || !db.users.verifyPassword(user, password)) {
      return res.status(401).json({
        ok: false,
        error: { message: "Invalid username or password" },
      });
    }
    const token = await db.sessions.create(user.id, user.role);
    return res.status(200).json({
      ok: true,
      data: {
        token,
        user: {
          id: user.id,
          username: user.username,
          role: user.role,
        },
      },
    });
  } catch (error) {
    return next(error);
  }
});

app.post("/api/auth/logout", async (req, res, next) => {
  try {
    const authHeader = req.headers["authorization"];
    if (authHeader && authHeader.startsWith("Bearer ")) {
      const token = authHeader.substring(7);
      await db.sessions.remove(token);
    }
    return res
      .status(200)
      .json({ ok: true, message: "Logged out successfully" });
  } catch (error) {
    return next(error);
  }
});

app.get("/api/auth/me", (req, res) => {
  if (!req.user) {
    return res
      .status(401)
      .json({ ok: false, error: { message: "Not logged in" } });
  }
  return res.status(200).json({ ok: true, data: { role: req.user.role } });
});

// Facebook API
app.post(
  "/api/facebook/post-message",
  requireRole(["admin", "editor"]),
  fb.postMessage,
);
app.post(
  "/api/facebook/post-photo",
  requireRole(["admin", "editor"]),
  upload.single("image"),
  fb.postPhoto,
);
app.get(
  "/api/facebook/posts",
  requireRole(["admin", "editor", "viewer"]),
  fb.getPosts,
);
app.delete(
  "/api/facebook/posts/:postId",
  requireRole(["admin", "editor"]),
  fb.deletePost,
);
app.get(
  "/api/facebook/insights",
  requireRole(["admin", "editor", "viewer"]),
  fb.getInsights,
);
app.get(
  "/api/facebook/insights/history",
  requireRole(["admin", "editor", "viewer"]),
  fb.getInsightsHistory,
);
app.get(
  "/api/facebook/posts/top",
  requireRole(["admin", "editor", "viewer"]),
  fb.getTopPosts,
);
app.get(
  "/api/facebook/config",
  requireRole(["admin", "editor", "viewer"]),
  fb.getConfig,
);
app.post(
  "/api/facebook/exchange-token",
  requireRole(["admin"]),
  fb.exchangeToken,
);
app.post(
  "/api/facebook/refresh-token",
  requireRole(["admin"]),
  fb.refreshToken,
);

// Queue
app.get("/api/queue", requireRole(["admin", "editor", "viewer"]), fb.getQueue);
app.get(
  "/api/queue/pending-review",
  requireRole(["admin", "editor", "viewer"]),
  fb.getPendingReview,
);
app.post("/api/queue", requireRole(["admin", "editor"]), fb.addToQueue);
app.delete("/api/queue", requireRole(["admin", "editor"]), fb.clearQueue);
app.delete(
  "/api/queue/:id",
  requireRole(["admin", "editor"]),
  fb.removeFromQueue,
);
app.post(
  "/api/queue/:id/publish",
  requireRole(["admin", "editor"]),
  fb.publishQueueItem,
);
app.post(
  "/api/queue/:id/retry",
  requireRole(["admin", "editor"]),
  fb.retryQueueItem,
);
app.post(
  "/api/queue/:id/approve",
  requireRole(["admin", "editor"]),
  fb.approveQueueItem,
);

// Post History
app.get(
  "/api/history",
  requireRole(["admin", "editor", "viewer"]),
  fb.getHistory,
);

// Schedules
app.get(
  "/api/schedules",
  requireRole(["admin", "editor", "viewer"]),
  fb.getSchedules,
);
app.post("/api/schedules", requireRole(["admin", "editor"]), fb.addSchedule);
app.patch(
  "/api/schedules/:id",
  requireRole(["admin", "editor"]),
  fb.updateSchedule,
);
app.delete(
  "/api/schedules/:id",
  requireRole(["admin", "editor"]),
  fb.removeSchedule,
);

// Settings
app.get(
  "/api/settings",
  requireRole(["admin", "editor", "viewer"]),
  fb.getSettings,
);
app.patch("/api/settings", requireRole(["admin"]), fb.updateSettings);

// Pages
app.get("/api/pages", requireRole(["admin", "editor", "viewer"]), fb.getPages);
app.post("/api/pages", requireRole(["admin"]), fb.addPage);
app.patch("/api/pages/:id", requireRole(["admin"]), fb.updatePage);
app.delete("/api/pages/:id", requireRole(["admin"]), fb.deletePage);

// ── AI Content Generator API ────────────────────────────────────────────────
const {
  generateContent,
  getTopics,
  getFormats,
} = require("./contentGenerator");
const { runAiAutoPost } = require("./aiAutoPoster");

/**
 * GET /api/ai/topics
 */
app.get(
  "/api/ai/topics",
  requireRole(["admin", "editor", "viewer"]),
  (req, res) => {
    return res.status(200).json({ ok: true, data: getTopics() });
  },
);

/**
 * GET /api/ai/formats
 */
app.get(
  "/api/ai/formats",
  requireRole(["admin", "editor", "viewer"]),
  (req, res) => {
    return res.status(200).json({ ok: true, data: getFormats() });
  },
);

/**
 * POST /api/ai/generate
 */
app.post(
  "/api/ai/generate",
  requireRole(["admin", "editor"]),
  async (req, res) => {
    try {
      const { tag, format, withImage, provider } = req.body;
      const content = await generateContent({
        tag,
        format,
        withImage: withImage !== false,
        provider: provider || "auto",
      });
      return res.status(200).json({ ok: true, data: content });
    } catch (e) {
      return res.status(500).json({
        ok: false,
        error: { code: "GENERATION_ERROR", message: e.message },
      });
    }
  },
);

/**
 * POST /api/ai/generate-and-post
 */
app.post(
  "/api/ai/generate-and-post",
  requireRole(["admin", "editor"]),
  async (req, res) => {
    try {
      const { tag, format, withImage, provider, dryRun } = req.body;
      const result = await runAiAutoPost({
        tag,
        format,
        withImage,
        provider,
        dryRun,
      });
      return res.status(200).json({ ok: true, data: result });
    } catch (e) {
      return res
        .status(500)
        .json({ ok: false, error: { code: "POST_ERROR", message: e.message } });
    }
  },
);

/**
 * PATCH /api/ai/settings
 */
app.patch(
  "/api/ai/settings",
  requireRole(["admin"]),
  async (req, res, next) => {
    const allowed = [
      "enabled",
      "topicTag",
      "postFormat",
      "withImage",
      "provider",
      "intervalHours",
    ];
    const updates = {};
    for (const k of allowed) {
      if (req.body[k] !== undefined) updates[k] = req.body[k];
    }

    try {
      const current = await db.settings.get();
      const aiSettings = { ...(current.aiAutoPoster || {}), ...updates };
      await db.settings.update({ aiAutoPoster: aiSettings });

      if ("enabled" in updates) {
        await scheduler.setAiAutoPosterEnabled(updates.enabled);
      }

      return res.status(200).json({ ok: true, data: aiSettings });
    } catch (error) {
      return next(error);
    }
  },
);

/**
 * GET /api/ai/settings
 */
app.get(
  "/api/ai/settings",
  requireRole(["admin", "editor", "viewer"]),
  async (req, res, next) => {
    try {
      const settings = await db.settings.get();
      return res
        .status(200)
        .json({ ok: true, data: settings.aiAutoPoster || { enabled: true } });
    } catch (error) {
      return next(error);
    }
  },
);

// ── Google Drive Media Library API ───────────────────────────────────────────
const googleDrive = require("./googleDrive");

/**
 * GET /api/google-drive/images
 */
app.get(
  "/api/google-drive/images",
  requireRole(["admin", "editor", "viewer"]),
  async (req, res) => {
    try {
      const limit = Math.min(parseInt(req.query.limit || "20", 10), 100);
      const files = await googleDrive.listFilesFromGoogleDrive(limit);
      return res.status(200).json({ ok: true, data: files });
    } catch (e) {
      return res.status(500).json({ ok: false, error: { message: e.message } });
    }
  },
);

// Scheduler control
app.post("/api/scheduler/trigger", requireRole(["admin"]), async (req, res) => {
  try {
    await scheduler.autoPostToPage();
    return res
      .status(200)
      .json({ ok: true, message: "Manual trigger executed" });
  } catch (e) {
    return res.status(500).json({ ok: false, error: { message: e.message } });
  }
});

app.post("/api/scheduler/restart", requireRole(["admin"]), (req, res) => {
  const { cron } = req.body;
  const ok = scheduler.restartDefaultJob(cron);
  if (ok)
    return res
      .status(200)
      .json({ ok: true, message: `Default job restarted with ${cron}` });
  return res
    .status(400)
    .json({ ok: false, error: { message: "Invalid cron expression" } });
});

if (databasePool) {
  app.use(
    "/v1",
    createV1Router({
      pool: databasePool,
      authenticate: async (token) => db.sessions.get(token),
    }),
  );
}

// ── Z.A.R.V.I.S. operator view ────────────────────────────────────────────────
app.get("/zarvis", (req, res) => {
  res.sendFile(path.join(__dirname, "../public/zarvis.html"));
});

app.get(
  "/api/zarvis/state",
  requireRole(["admin", "editor", "viewer"]),
  async (req, res, next) => {
    try {
      const data = await buildZarvisState({ db, scheduler });
      return res.status(200).json({ ok: true, data });
    } catch (error) {
      return next(error);
    }
  },
);

app.get(
  "/v1/zarvis/state",
  requireRole(["admin", "editor", "viewer"]),
  async (req, res, next) => {
    try {
      const data = await buildZarvisState({ db, scheduler });
      return res.status(200).json({ ok: true, data });
    } catch (error) {
      return next(error);
    }
  },
);

// Catch-all: serve SPA
app.get("*", (req, res) => {
  res.sendFile(path.join(__dirname, "../public/index.html"));
});

// ── Error Handler ─────────────────────────────────────────────────────────────
app.use((err, req, res, _next) => {
  console.error("[error]", err.message);
  if (err.code === "LIMIT_FILE_SIZE") {
    return res.status(413).json({
      ok: false,
      error: { code: "FILE_TOO_LARGE", message: "File too large (max 10MB)" },
    });
  }
  return res.status(500).json({
    ok: false,
    error: { code: "INTERNAL_ERROR", message: err.message },
  });
});

// ── Start ─────────────────────────────────────────────────────────────────────
async function start() {
  if (!databasePool) throw new Error("DATABASE_URL is required");
  if (process.env.NODE_ENV === "production" && !readSecret("METRICS_TOKEN")) {
    throw new Error("METRICS_TOKEN is required in production");
  }
  await migrate(databasePool);
  db.configure(databasePool);
  await db.users.seedInitialAdmin();
  await scheduler.initJobs();
  ready = true;
  const server = app.listen(port, () => {
    console.log(`Zeto server listening on http://localhost:${port}`);
  });
  let stopping = false;
  const shutdown = async (signal) => {
    if (stopping) return;
    stopping = true;
    ready = false;
    scheduler.stopAll();
    const forceTimer = setTimeout(
      () => process.exit(1),
      Number(process.env.SHUTDOWN_TIMEOUT_MS || 10000),
    );
    forceTimer.unref();
    server.close(async (error) => {
      if (databasePool) await databasePool.end();
      if (error) {
        console.error("[shutdown] failed", { signal, error: error.message });
        process.exit(1);
      }
      process.exit(0);
    });
  };
  process.once("SIGTERM", () => shutdown("SIGTERM"));
  process.once("SIGINT", () => shutdown("SIGINT"));
  return server;
}

if (require.main === module) {
  start().catch((error) => {
    console.error("[startup] failed", error);
    process.exit(1);
  });
}

module.exports = { app, start };
