"use strict";

const { z } = require("zod");
const { EVENT_TYPES } = require("./operatorEvents");

/** POST /v1/operator/sessions */
const sessionCreateSchema = z.object({
  mode: z.enum(["chat", "voice", "operator", "automation"]),
  capabilities: z.array(z.string().trim().min(1).max(120)).max(64).default([]),
});

/** POST /v1/operator/sessions/:id/commands */
const commandSchema = z
  .object({
    text: z.string().trim().min(1).max(20000).optional(),
    audioRef: z.string().trim().min(1).max(512).optional(),
    sequenceId: z.string().trim().min(1).max(512).optional(),
  })
  .refine(
    (value) => value.text || value.audioRef || value.sequenceId,
    "One of text, audioRef, or sequenceId is required",
  );

/** Plan step (spec §6.2) */
const planStepSchema = z.object({
  stepId: z.string().trim().min(1).max(80),
  tool: z.string().trim().min(1).max(120),
  args: z.record(z.string(), z.unknown()).default({}),
  risk: z.enum(["none", "low", "medium", "high", "critical"]),
  dependsOn: z.array(z.string().trim().min(1)).default([]),
});

/** Plan (spec §6.2) */
const planSchema = z.object({
  intent: z.string().trim().min(1).max(240),
  steps: z.array(planStepSchema).min(1).max(50),
  policyVerdict: z.enum(["approved", "approval_required", "denied"]),
  estimatedCost: z.number().nonnegative().max(1000000).default(0),
});

/** POST /v1/operator/plans/:id/approve */
const planDecisionSchema = z.object({
  decision: z.enum(["approved", "overridden"]),
});

/** POST /v1/operator/plans/:id/reject */
const planRejectSchema = z.object({
  reason: z.string().trim().min(1).max(2000).default("Rejected by operator"),
});

/** POST /v1/operator/sessions/:id/cancel */
const cancelSessionSchema = z.object({
  reason: z.string().trim().min(1).max(2000).default("Cancelled by operator"),
});

/** POST /v1/operator/sessions/:id/emergency-stop */
const emergencyStopSchema = z.object({
  reason: z.string().trim().min(1).max(2000),
});

/** Sequence step (spec §4.3) */
const sequenceStepSchema = z.object({
  id: z
    .string()
    .trim()
    .regex(/^[A-Za-z][A-Za-z0-9_-]{0,31}$/),
  intent: z.string().trim().min(1).max(120),
  args: z.record(z.string(), z.unknown()).default({}),
  risk: z.enum(["none", "low", "medium", "high", "critical"]).optional(),
});

/** Sequence (spec §4.3) */
const sequenceSchema = z.object({
  name: z.string().trim().min(1).max(120),
  mode: z.enum(["chat", "operator", "automation"]).default("operator"),
  steps: z
    .array(sequenceStepSchema)
    .min(1)
    .max(50)
    .refine(
      (steps) => new Set(steps.map((step) => step.id)).size === steps.length,
      "Step ids must be unique",
    ),
  dryRun: z.boolean().default(false),
});

/** POST /v1/operator/sequences/:id/run */
const sequenceRunSchema = z.object({
  dryRun: z.boolean().default(false),
  sessionId: z.string().uuid().optional(),
  resumeRunId: z.string().uuid().optional(),
  confirmReplay: z.boolean().default(false),
});

/** Event envelope (spec §10) — as persisted; sequence_id is assigned by the store. */
const eventEnvelopeSchema = z.object({
  event_id: z.string().min(1).max(128),
  session_id: z.string().uuid(),
  generation: z.number().int().positive(),
  sequence_id: z.number().int().positive(),
  type: z.enum(EVENT_TYPES),
  occurred_at: z.iso.datetime({ offset: true }),
  correlation_id: z.string().nullable(),
  payload: z.record(z.string(), z.unknown()),
});

module.exports = {
  sessionCreateSchema,
  commandSchema,
  planStepSchema,
  planSchema,
  planDecisionSchema,
  planRejectSchema,
  cancelSessionSchema,
  emergencyStopSchema,
  sequenceStepSchema,
  sequenceSchema,
  sequenceRunSchema,
  eventEnvelopeSchema,
};
