"use strict";

const express = require("express");
const { z } = require("zod");
const {
  OperatorRuntimeService,
} = require("../services/operatorRuntimeService");
const {
  sessionCreateSchema,
  commandSchema,
  planDecisionSchema,
  planRejectSchema,
  cancelSessionSchema,
  emergencyStopSchema,
  sequenceSchema,
  sequenceRunSchema,
  eventEnvelopeSchema,
} = require("../domain/operatorContracts");

const MUTATION_ROLES = ["admin", "editor"];
const OBSERVER_ROLES = ["admin", "editor", "viewer"];

function errorBody(req, code, message, details) {
  return {
    ok: false,
    requestId: req.requestId,
    error: { code, message, ...(details ? { details } : {}) },
  };
}

function parseUuid(value) {
  const parsed = z.string().uuid().safeParse(value);
  if (!parsed.success) return null;
  return parsed.data;
}

function formatSseEvent(event) {
  const envelope = eventEnvelopeSchema.parse({
    event_id: event.event_id,
    session_id: event.session_id,
    generation: event.generation,
    sequence_id: event.sequence_id,
    type: event.type,
    occurred_at:
      event.occurred_at instanceof Date
        ? event.occurred_at.toISOString()
        : event.occurred_at,
    correlation_id: event.correlation_id,
    payload: event.payload || {},
  });
  const data = { ...envelope, ...envelope.payload };
  delete data.payload;
  return `event: ${envelope.type}\ndata: ${JSON.stringify(data)}\n\n`;
}

function createOperatorV1Router({ pool }) {
  const runtime = new OperatorRuntimeService({ pool });
  const router = express.Router();

  const requireRoles = (roles) => (req, res, next) => {
    if (!req.user || !roles.includes(req.user.role)) {
      return res
        .status(403)
        .json(
          errorBody(
            req,
            "FORBIDDEN",
            "Access denied: insufficient permissions",
          ),
        );
    }
    return next();
  };

  /** POST /v1/operator/sessions */
  router.post(
    "/sessions",
    requireRoles(MUTATION_ROLES),
    async (req, res, next) => {
      try {
        const input = sessionCreateSchema.parse(req.body);
        const { session, event } = await runtime.createSession({
          mode: input.mode,
          capabilities: input.capabilities,
          actorId: req.user.userId ?? req.user.id ?? null,
        });
        return res.status(201).json({
          ok: true,
          requestId: req.requestId,
          data: {
            session,
            sequence_id: event?.sequence_id ?? 0,
          },
        });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** GET /v1/operator/sessions/:id — session snapshot for reload/reconnect restore. */
  router.get(
    "/sessions/:id",
    requireRoles(OBSERVER_ROLES),
    async (req, res, next) => {
      try {
        const sessionId = parseUuid(req.params.id);
        if (!sessionId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid session ID"));
        }
        const session = await runtime.getSession(sessionId);
        if (!session) {
          return res
            .status(404)
            .json(errorBody(req, "NOT_FOUND", "Operator session not found"));
        }
        return res.json({ ok: true, requestId: req.requestId, data: session });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** GET /v1/operator/sessions/:id/events — SSE, resumable via Last-Event-ID. */
  router.get(
    "/sessions/:id/events",
    requireRoles(OBSERVER_ROLES),
    async (req, res, next) => {
      let session;
      try {
        const sessionId = parseUuid(req.params.id);
        if (!sessionId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid session ID"));
        }
        session = await runtime.getSession(sessionId);
        if (!session) {
          return res
            .status(404)
            .json(errorBody(req, "NOT_FOUND", "Operator session not found"));
        }
      } catch (error) {
        return next(error);
      }

      const rawLast = req.get("last-event-id") || req.query.lastEventId || "0";
      const lastEventId = /^\d+$/.test(String(rawLast)) ? Number(rawLast) : 0;

      res.set({
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      });
      res.flushHeaders();
      // The global request timeout would kill a long-lived SSE stream.
      req.setTimeout(0);
      res.setTimeout(0);

      let lastSeen = lastEventId;
      let closed = false;
      let pollTimer = null;
      let heartbeat = null;
      const close = () => {
        closed = true;
        if (pollTimer) clearInterval(pollTimer);
        if (heartbeat) clearInterval(heartbeat);
        res.end();
      };
      res.on("close", close);
      req.on("close", close);

      const sendNewEvents = async () => {
        if (closed) return;
        const events = await runtime.eventsAfter(session.id, lastSeen);
        for (const event of events) {
          if (closed) return;
          res.write(formatSseEvent(event));
          lastSeen = event.sequence_id;
        }
      };

      try {
        await sendNewEvents(); // replay persisted events > Last-Event-ID, in order
      } catch (error) {
        res.write(
          `event: error\ndata: ${JSON.stringify({ message: error.message })}\n\n`,
        );
        return close();
      }

      pollTimer = setInterval(
        () => sendNewEvents().catch(() => {}),
        Number(process.env.OPERATOR_SSE_POLL_MS || 1000),
      );
      heartbeat = setInterval(() => {
        if (!closed) res.write(": keep-alive\n\n");
      }, 15000);
      return undefined;
    },
  );

  /** POST /v1/operator/sessions/:id/commands */
  router.post(
    "/sessions/:id/commands",
    requireRoles(MUTATION_ROLES),
    async (req, res, next) => {
      try {
        const sessionId = parseUuid(req.params.id);
        if (!sessionId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid session ID"));
        }
        const input = commandSchema.parse(req.body);
        const result = await runtime.submitCommand({
          sessionId,
          actorId: req.user.userId ?? req.user.id ?? null,
          text: input.text,
          audioRef: input.audioRef,
          sequenceId: input.sequenceId,
        });
        return res.status(201).json({
          ok: true,
          requestId: req.requestId,
          data: {
            command_id: result.command.id,
            plan_id: null, // plan produced by the planner slice, not command intake
            correlation_id: result.correlationId,
          },
        });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** POST /v1/operator/sessions/:id/cancel */
  router.post(
    "/sessions/:id/cancel",
    requireRoles(MUTATION_ROLES),
    async (req, res, next) => {
      try {
        const sessionId = parseUuid(req.params.id);
        if (!sessionId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid session ID"));
        }
        const input = cancelSessionSchema.parse(req.body || {});
        await runtime.cancelSession(sessionId, {
          actor: req.user.userId ?? req.user.id ?? "operator",
          reason: input.reason,
        });
        return res.json({
          ok: true,
          requestId: req.requestId,
          data: { status: "cancelling" },
        });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** POST /v1/operator/sessions/:id/pause */
  router.post(
    "/sessions/:id/pause",
    requireRoles(MUTATION_ROLES),
    async (req, res, next) => {
      try {
        const sessionId = parseUuid(req.params.id);
        if (!sessionId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid session ID"));
        }
        const result = await runtime.pause(sessionId, {
          actor: req.user.userId ?? req.user.id ?? "operator",
          reason: req.body?.reason || null,
        });
        return res.json({
          ok: true,
          requestId: req.requestId,
          data: {
            state: result.session.state,
            policy: result.policy,
            deferred: result.deferred || false,
          },
        });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** POST /v1/operator/sessions/:id/resume */
  router.post(
    "/sessions/:id/resume",
    requireRoles(MUTATION_ROLES),
    async (req, res, next) => {
      try {
        const sessionId = parseUuid(req.params.id);
        if (!sessionId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid session ID"));
        }
        const result = await runtime.resume(sessionId, {
          actor: req.user.userId ?? req.user.id ?? "operator",
        });
        return res.json({
          ok: true,
          requestId: req.requestId,
          data: { state: result.session.state },
        });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** POST /v1/operator/sessions/:id/emergency-stop */
  router.post(
    "/sessions/:id/emergency-stop",
    requireRoles(["admin"]),
    async (req, res, next) => {
      try {
        const sessionId = parseUuid(req.params.id);
        if (!sessionId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid session ID"));
        }
        const input = emergencyStopSchema.parse(req.body);
        const result = await runtime.emergencyStop(sessionId, {
          actor: req.user.userId ?? req.user.id ?? "operator",
          reason: input.reason,
        });
        return res.json({
          ok: true,
          requestId: req.requestId,
          data: {
            state: result.session.state,
            killSwitchLatched: result.session.killSwitchLatched,
          },
        });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** GET /v1/operator/plans/:id */
  router.get(
    "/plans/:id",
    requireRoles(OBSERVER_ROLES),
    async (req, res, next) => {
      try {
        const planId = parseUuid(req.params.id);
        if (!planId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid plan ID"));
        }
        const plan = await runtime.getPlan(planId);
        if (!plan) {
          return res
            .status(404)
            .json(errorBody(req, "NOT_FOUND", "Operator plan not found"));
        }
        return res.json({ ok: true, requestId: req.requestId, data: plan });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** POST /v1/operator/plans/:id/approve */
  router.post(
    "/plans/:id/approve",
    requireRoles(MUTATION_ROLES),
    async (req, res, next) => {
      try {
        const planId = parseUuid(req.params.id);
        if (!planId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid plan ID"));
        }
        const input = planDecisionSchema.parse(req.body);
        const result = await runtime.approvePlan(planId, {
          actor: req.user.userId ?? req.user.id ?? "operator",
          actorId: req.user.userId ?? req.user.id ?? null,
          decision: input.decision,
        });
        return res.json({ ok: true, requestId: req.requestId, data: result });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** GET /v1/operator/sequences — list saved sequences (§4.3, §9). */
  router.get(
    "/sequences",
    requireRoles(OBSERVER_ROLES),
    async (req, res, next) => {
      try {
        const sequences = await runtime.listSequences();
        return res.json({
          ok: true,
          requestId: req.requestId,
          data: sequences,
        });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** POST /v1/operator/sequences — save a sequence (§4.3). */
  router.post(
    "/sequences",
    requireRoles(MUTATION_ROLES),
    async (req, res, next) => {
      try {
        const input = sequenceSchema.parse(req.body);
        const sequence = await runtime.createSequence({
          name: input.name,
          mode: input.mode,
          dryRun: input.dryRun,
          steps: input.steps,
          actorId: req.user.userId ?? req.user.id ?? null,
        });
        return res.status(201).json({
          ok: true,
          requestId: req.requestId,
          data: sequence,
        });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** GET /v1/operator/sequences/:id — sequence detail with steps. */
  router.get(
    "/sequences/:id",
    requireRoles(OBSERVER_ROLES),
    async (req, res, next) => {
      try {
        const sequenceId = parseUuid(req.params.id);
        if (!sequenceId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid sequence ID"));
        }
        const sequence = await runtime.getSequence(sequenceId);
        if (!sequence) {
          return res
            .status(404)
            .json(errorBody(req, "NOT_FOUND", "Operator sequence not found"));
        }
        return res.json({ ok: true, requestId: req.requestId, data: sequence });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** PUT /v1/operator/sequences/:id — save/reorder steps of a sequence. */
  router.put(
    "/sequences/:id",
    requireRoles(MUTATION_ROLES),
    async (req, res, next) => {
      try {
        const sequenceId = parseUuid(req.params.id);
        if (!sequenceId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid sequence ID"));
        }
        const input = sequenceSchema.parse(req.body);
        const sequence = await runtime.updateSequence(sequenceId, input);
        return res.json({ ok: true, requestId: req.requestId, data: sequence });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** DELETE /v1/operator/sequences/:id */
  router.delete(
    "/sequences/:id",
    requireRoles(MUTATION_ROLES),
    async (req, res, next) => {
      try {
        const sequenceId = parseUuid(req.params.id);
        if (!sequenceId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid sequence ID"));
        }
        await runtime.deleteSequence(sequenceId);
        return res.json({
          ok: true,
          requestId: req.requestId,
          data: { deleted: true },
        });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** POST /v1/operator/sequences/:id/run — run or dry-run a sequence (§9). */
  router.post(
    "/sequences/:id/run",
    requireRoles(MUTATION_ROLES),
    async (req, res, next) => {
      try {
        const sequenceId = parseUuid(req.params.id);
        if (!sequenceId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid sequence ID"));
        }
        const input = sequenceRunSchema.parse(req.body || {});
        const result = await runtime.runSequence({
          sequenceId,
          sessionId: input.sessionId,
          dryRun: input.dryRun,
          resumeRunId: input.resumeRunId,
          confirmReplay: input.confirmReplay,
          actorId: req.user.userId ?? req.user.id ?? null,
        });
        return res.status(201).json({
          ok: true,
          requestId: req.requestId,
          data: {
            run_id: result.run.id,
            status: result.run.status,
            session_id: result.session.id,
            current_step: result.run.currentStep,
            error: result.run.error,
          },
        });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** GET /v1/operator/sequence-runs/:id — run + per-step results (§4.3 resume). */
  router.get(
    "/sequence-runs/:id",
    requireRoles(OBSERVER_ROLES),
    async (req, res, next) => {
      try {
        const runId = parseUuid(req.params.id);
        if (!runId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid run ID"));
        }
        const run = await runtime.getSequenceRun(runId);
        if (!run) {
          return res
            .status(404)
            .json(
              errorBody(req, "NOT_FOUND", "Operator sequence run not found"),
            );
        }
        return res.json({ ok: true, requestId: req.requestId, data: run });
      } catch (error) {
        return next(error);
      }
    },
  );

  /** POST /v1/operator/plans/:id/reject */
  router.post(
    "/plans/:id/reject",
    requireRoles(MUTATION_ROLES),
    async (req, res, next) => {
      try {
        const planId = parseUuid(req.params.id);
        if (!planId) {
          return res
            .status(422)
            .json(errorBody(req, "VALIDATION_ERROR", "Invalid plan ID"));
        }
        const input = planRejectSchema.parse(req.body || {});
        const result = await runtime.rejectPlan(planId, {
          actor: req.user.userId ?? req.user.id ?? "operator",
          actorId: req.user.userId ?? req.user.id ?? null,
          reason: input.reason,
        });
        return res.json({ ok: true, requestId: req.requestId, data: result });
      } catch (error) {
        return next(error);
      }
    },
  );

  router.use((error, req, res, _next) => {
    if (error instanceof z.ZodError) {
      return res.status(422).json(
        errorBody(
          req,
          "VALIDATION_ERROR",
          "Request validation failed",
          error.issues.map((issue) => ({
            path: issue.path.join("."),
            message: issue.message,
          })),
        ),
      );
    }
    if (error.code === "INVALID_TRANSITION") {
      return res
        .status(409)
        .json(errorBody(req, "INVALID_TRANSITION", error.message));
    }
    if (error.code === "CONFIRMATION_REQUIRED") {
      return res
        .status(409)
        .json(errorBody(req, "CONFIRMATION_REQUIRED", error.message));
    }
    if (error.message.includes("not found")) {
      return res.status(404).json(errorBody(req, "NOT_FOUND", error.message));
    }
    console.error("[v1/operator] request failed", {
      requestId: req.requestId,
      error: error.message,
    });
    return res
      .status(400)
      .json(errorBody(req, "OPERATOR_ERROR", error.message));
  });

  return router;
}

module.exports = { createOperatorV1Router };
