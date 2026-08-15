const crypto = require("node:crypto");
const express = require("express");
const { z } = require("zod");
const { openApiDocument } = require("./openapi");
const { BrandRepository } = require("../repositories/brandRepository");
const { WorkflowRepository } = require("../repositories/workflowRepository");
const { AnalyticsRepository } = require("../repositories/analyticsRepository");
const {
  MonitoringRepository,
} = require("../repositories/monitoringRepository");
const {
  createDefaultProviderRegistry,
} = require("../providers/providerRegistry");
const {
  FactoryWorkflowService,
} = require("../services/factoryWorkflowService");
const { createOperatorV1Router } = require("./operatorV1");

const brandSchema = z.object({
  name: z.string().trim().min(1).max(120),
  niche: z.string().trim().min(1).max(240),
  colors: z
    .array(z.string().regex(/^#[0-9a-fA-F]{6}$/))
    .max(32)
    .default([]),
  timezone: z.string().trim().min(1).max(100).default("UTC"),
});

const workflowSchema = z.object({
  brandId: z.string().uuid(),
  name: z.string().trim().min(1).max(120),
  steps: z
    .array(
      z.object({
        key: z.string().trim().min(1).max(80),
        owner: z.string().trim().min(1).max(80),
        timeoutMs: z.number().int().min(1000).max(3600000).optional(),
        maxAttempts: z.number().int().min(1).max(20).optional(),
      }),
    )
    .min(1)
    .max(50),
});
const workflowRunSchema = z.object({
  input: z.record(z.string(), z.unknown()).default({}),
});
const dailyMetricSchema = z.object({
  brandId: z.string().uuid(),
  publicationId: z.string().uuid().nullable().optional(),
  platform: z.enum([
    "facebook",
    "instagram",
    "youtube",
    "tiktok",
    "x",
    "linkedin",
  ]),
  date: z.iso.date(),
  metrics: z
    .object({
      followers: z.number().nonnegative().optional(),
      reach: z.number().nonnegative().optional(),
      engagement: z.number().nonnegative().optional(),
    })
    .refine(
      (value) => Object.keys(value).length > 0,
      "At least one metric is required",
    ),
});
const mentionSchema = z.object({
  brandId: z.string().uuid(),
  platform: z.string().trim().min(1).max(40),
  externalId: z.string().trim().min(1).max(240),
  body: z.string().trim().min(1).max(20000),
  occurredAt: z.iso.datetime({ offset: true }),
  metadata: z.record(z.string(), z.unknown()).default({}),
});
const factoryRunSchema = z
  .object({
    brandId: z.string().uuid(),
    brand: z.record(z.string(), z.unknown()),
    idea: z.record(z.string(), z.unknown()),
    palette: z.array(z.string()).min(1),
    platforms: z.array(z.string()).min(1),
    platform: z.enum([
      "facebook",
      "instagram",
      "youtube",
      "tiktok",
      "x",
      "linkedin",
    ]),
    image: z.record(z.string(), z.unknown()),
    video: z.record(z.string(), z.unknown()),
    audio: z.record(z.string(), z.unknown()),
    caption: z.record(z.string(), z.unknown()),
    qaChecks: z.record(z.string(), z.unknown()),
  })
  .passthrough();
const factoryApprovalSchema = z.object({
  decision: z.enum(["approved", "overridden"]),
});

function errorBody(req, code, message, details) {
  return {
    ok: false,
    requestId: req.requestId,
    error: { code, message, ...(details ? { details } : {}) },
  };
}

function createV1Router({
  pool,
  authenticate,
  providerRegistry = createDefaultProviderRegistry(),
}) {
  if (!pool || !authenticate)
    throw new Error("pool and authenticate are required");
  const router = express.Router();
  const brands = new BrandRepository(pool);
  const workflows = new WorkflowRepository(pool);
  const analytics = new AnalyticsRepository(pool);
  const monitoring = new MonitoringRepository(pool);
  const factoryWorkflows = new FactoryWorkflowService({
    pool,
    providerRegistry,
  });

  router.use((req, res, next) => {
    const supplied = req.get("x-request-id");
    req.requestId =
      supplied && /^[A-Za-z0-9._:-]{1,128}$/.test(supplied)
        ? supplied
        : crypto.randomUUID();
    res.set("x-request-id", req.requestId);
    next();
  });
  router.use(async (req, res, next) => {
    try {
      const header = req.get("authorization") || "";
      const token = header.startsWith("Bearer ") ? header.slice(7) : "";
      req.user = token ? await authenticate(token) : null;
      if (!req.user)
        return res
          .status(401)
          .json(errorBody(req, "UNAUTHORIZED", "Authentication required"));
      return next();
    } catch (error) {
      return next(error);
    }
  });

  router.use("/operator", createOperatorV1Router({ pool }));
  router.get("/openapi.json", (_req, res) => res.json(openApiDocument));
  router.get("/providers", (req, res) =>
    res.json({
      ok: true,
      requestId: req.requestId,
      data: providerRegistry.list(),
    }),
  );
  router.post("/factory-runs", async (req, res, next) => {
    try {
      if (!["admin", "editor"].includes(req.user.role)) {
        return res
          .status(403)
          .json(errorBody(req, "FORBIDDEN", "Insufficient permissions"));
      }
      const idempotencyKey = req.get("idempotency-key");
      if (!idempotencyKey || idempotencyKey.length > 200) {
        return res
          .status(400)
          .json(
            errorBody(
              req,
              "IDEMPOTENCY_KEY_REQUIRED",
              "A valid Idempotency-Key header is required",
            ),
          );
      }
      const parsed = factoryRunSchema.safeParse(req.body);
      if (!parsed.success) {
        return res
          .status(422)
          .json(
            errorBody(
              req,
              "VALIDATION_ERROR",
              "Request validation failed",
              parsed.error.issues,
            ),
          );
      }
      providerRegistry.validatePublication(parsed.data.platform, {
        kind: parsed.data.publicationKind || "image",
      });
      const run = await factoryWorkflows.start(parsed.data, {
        idempotencyKey,
        requestId: req.requestId,
      });
      return res.status(202).json({
        ok: true,
        requestId: req.requestId,
        data: run,
      });
    } catch (error) {
      return next(error);
    }
  });
  router.post("/factory-runs/:runId/approve", async (req, res, next) => {
    try {
      if (!["admin", "editor"].includes(req.user.role)) {
        return res
          .status(403)
          .json(errorBody(req, "FORBIDDEN", "Insufficient permissions"));
      }
      const parsed = factoryApprovalSchema.safeParse(req.body);
      if (!parsed.success) {
        return res
          .status(422)
          .json(
            errorBody(
              req,
              "VALIDATION_ERROR",
              "Request validation failed",
              parsed.error.issues,
            ),
          );
      }
      const run = await factoryWorkflows.approve(req.params.runId, {
        decision: parsed.data.decision,
        actorId: req.user.id,
      });
      return res.json({ ok: true, requestId: req.requestId, data: run });
    } catch (error) {
      return next(error);
    }
  });
  router.get("/brands", async (req, res, next) => {
    try {
      const limit = Math.min(Math.max(Number(req.query.limit) || 50, 1), 100);
      const result = await brands.list({
        limit,
        cursor: req.query.cursor || null,
      });
      return res.json({
        ok: true,
        requestId: req.requestId,
        data: result.rows,
        pagination: { limit, nextCursor: result.nextCursor },
      });
    } catch (error) {
      return next(error);
    }
  });
  router.post("/brands", async (req, res, next) => {
    try {
      if (!["admin", "editor"].includes(req.user.role)) {
        return res
          .status(403)
          .json(errorBody(req, "FORBIDDEN", "Insufficient permissions"));
      }
      const idempotencyKey = req.get("idempotency-key");
      if (!idempotencyKey || idempotencyKey.length > 200) {
        return res
          .status(400)
          .json(
            errorBody(
              req,
              "IDEMPOTENCY_KEY_REQUIRED",
              "A valid Idempotency-Key header is required",
            ),
          );
      }
      const parsed = brandSchema.safeParse(req.body);
      if (!parsed.success) {
        const details = parsed.error.issues.map((issue) => ({
          path: issue.path.join("."),
          message: issue.message,
        }));
        return res
          .status(422)
          .json(
            errorBody(
              req,
              "VALIDATION_ERROR",
              "Request validation failed",
              details,
            ),
          );
      }
      const brand = await brands.create(parsed.data, {
        actorId: req.user.id,
        idempotencyKey,
        requestId: req.requestId,
      });
      return res
        .status(201)
        .json({ ok: true, requestId: req.requestId, data: brand });
    } catch (error) {
      return next(error);
    }
  });
  router.post("/workflows", async (req, res, next) => {
    try {
      if (!["admin", "editor"].includes(req.user.role)) {
        return res
          .status(403)
          .json(errorBody(req, "FORBIDDEN", "Insufficient permissions"));
      }
      const parsed = workflowSchema.safeParse(req.body);
      if (!parsed.success) {
        return res
          .status(422)
          .json(
            errorBody(
              req,
              "VALIDATION_ERROR",
              "Request validation failed",
              parsed.error.issues,
            ),
          );
      }
      const workflow = await workflows.createDefinition(parsed.data);
      return res
        .status(201)
        .json({ ok: true, requestId: req.requestId, data: workflow });
    } catch (error) {
      return next(error);
    }
  });
  router.post("/workflows/:workflowId/runs", async (req, res, next) => {
    try {
      if (!["admin", "editor"].includes(req.user.role)) {
        return res
          .status(403)
          .json(errorBody(req, "FORBIDDEN", "Insufficient permissions"));
      }
      const idempotencyKey = req.get("idempotency-key");
      if (!idempotencyKey || idempotencyKey.length > 200) {
        return res
          .status(400)
          .json(
            errorBody(
              req,
              "IDEMPOTENCY_KEY_REQUIRED",
              "A valid Idempotency-Key header is required",
            ),
          );
      }
      const workflowId = z.string().uuid().safeParse(req.params.workflowId);
      const body = workflowRunSchema.safeParse(req.body);
      if (!workflowId.success || !body.success) {
        return res
          .status(422)
          .json(
            errorBody(req, "VALIDATION_ERROR", "Request validation failed"),
          );
      }
      const run = await workflows.start(
        workflowId.data,
        body.data.input,
        idempotencyKey,
      );
      return res
        .status(202)
        .json({ ok: true, requestId: req.requestId, data: run });
    } catch (error) {
      return next(error);
    }
  });
  router.get("/workflow-runs/:runId", async (req, res, next) => {
    try {
      const runId = z.string().uuid().safeParse(req.params.runId);
      if (!runId.success) {
        return res
          .status(422)
          .json(errorBody(req, "VALIDATION_ERROR", "Invalid workflow run ID"));
      }
      const run = await workflows.getRun(runId.data);
      if (!run)
        return res
          .status(404)
          .json(errorBody(req, "NOT_FOUND", "Workflow run not found"));
      return res.json({ ok: true, requestId: req.requestId, data: run });
    } catch (error) {
      return next(error);
    }
  });
  router.get("/workflow-runs", async (req, res, next) => {
    try {
      const brandId = z.string().uuid().safeParse(req.query.brandId);
      const limit = z.coerce
        .number()
        .int()
        .min(1)
        .max(100)
        .default(25)
        .safeParse(req.query.limit);
      if (!brandId.success || !limit.success) {
        return res
          .status(422)
          .json(errorBody(req, "VALIDATION_ERROR", "Invalid workflow query"));
      }
      const runs = await workflows.listRuns({
        brandId: brandId.data,
        limit: limit.data,
      });
      return res.json({
        ok: true,
        requestId: req.requestId,
        data: runs,
        pagination: { limit: limit.data },
      });
    } catch (error) {
      return next(error);
    }
  });
  router.post("/workflow-runs/:runId/cancel", async (req, res, next) => {
    try {
      if (req.user.role !== "admin") {
        return res
          .status(403)
          .json(errorBody(req, "FORBIDDEN", "Insufficient permissions"));
      }
      const runId = z.string().uuid().safeParse(req.params.runId);
      if (!runId.success) {
        return res
          .status(422)
          .json(errorBody(req, "VALIDATION_ERROR", "Invalid workflow run ID"));
      }
      const run = await workflows.cancel(runId.data);
      return res.json({ ok: true, requestId: req.requestId, data: run });
    } catch (error) {
      return next(error);
    }
  });
  router.post("/metrics", async (req, res, next) => {
    try {
      if (!["admin", "editor"].includes(req.user.role)) {
        return res
          .status(403)
          .json(errorBody(req, "FORBIDDEN", "Insufficient permissions"));
      }
      const parsed = dailyMetricSchema.safeParse(req.body);
      if (!parsed.success) {
        return res
          .status(422)
          .json(
            errorBody(
              req,
              "VALIDATION_ERROR",
              "Request validation failed",
              parsed.error.issues,
            ),
          );
      }
      const metric = await analytics.ingestDaily(parsed.data);
      return res
        .status(201)
        .json({ ok: true, requestId: req.requestId, data: metric });
    } catch (error) {
      return next(error);
    }
  });
  router.get("/analytics/control-room", async (req, res, next) => {
    try {
      const brandId = z.string().uuid().safeParse(req.query.brandId);
      const days = z.coerce
        .number()
        .int()
        .min(1)
        .max(365)
        .default(30)
        .safeParse(req.query.days);
      if (!brandId.success || !days.success) {
        return res
          .status(422)
          .json(errorBody(req, "VALIDATION_ERROR", "Invalid analytics query"));
      }
      const report = await analytics.controlRoom(brandId.data, {
        days: days.data,
      });
      return res.json({ ok: true, requestId: req.requestId, data: report });
    } catch (error) {
      return next(error);
    }
  });
  router.post("/mentions", async (req, res, next) => {
    try {
      if (!["admin", "editor"].includes(req.user.role)) {
        return res
          .status(403)
          .json(errorBody(req, "FORBIDDEN", "Insufficient permissions"));
      }
      const parsed = mentionSchema.safeParse(req.body);
      if (!parsed.success) {
        return res
          .status(422)
          .json(
            errorBody(
              req,
              "VALIDATION_ERROR",
              "Request validation failed",
              parsed.error.issues,
            ),
          );
      }
      const mention = await monitoring.ingest(parsed.data);
      return res
        .status(201)
        .json({ ok: true, requestId: req.requestId, data: mention });
    } catch (error) {
      return next(error);
    }
  });
  router.use((error, req, res, _next) => {
    console.error("[v1] request failed", {
      requestId: req.requestId,
      error: error.message,
    });
    return res
      .status(500)
      .json(errorBody(req, "INTERNAL_ERROR", "Internal server error"));
  });
  return router;
}

module.exports = { createV1Router };
