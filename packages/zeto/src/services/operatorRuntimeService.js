"use strict";

const crypto = require("node:crypto");
const { OperatorRepository } = require("../repositories/operatorRepository");
const {
  transitionOperatorState,
  pauseRequestPolicy,
  TERMINAL_STATES,
  isPausable,
} = require("../domain/operatorStateMachine");
const {
  buildEvent,
  buildStateChanged,
  buildEmergencyStop,
} = require("../domain/operatorEvents");
const {
  sessionCreateSchema,
  commandSchema,
  planSchema,
  planDecisionSchema,
  planRejectSchema,
  cancelSessionSchema,
  emergencyStopSchema,
  sequenceSchema,
  sequenceRunSchema,
} = require("../domain/operatorContracts");
const {
  resolveStepArgs,
  isHighRiskStep,
} = require("../domain/operatorSequences");
const { executeSequenceStep } = require("./operatorSequenceExecutor");

/** Map a persisted sequence step row to the §4.3 shape. */
function mapSequenceStep(row) {
  if (!row) return null;
  return {
    id: row.step_key,
    intent: row.intent,
    args: row.args || {},
    ...(row.risk ? { risk: row.risk } : {}),
    status: row.status,
    result: row.result ?? null,
    error: row.error ?? null,
  };
}

class OperatorRuntimeService {
  constructor({ pool, repository = null }) {
    this.repository = repository || new OperatorRepository(pool);
  }

  async createSession({ mode, capabilities = [], actorId = null }) {
    const input = sessionCreateSchema.parse({ mode, capabilities });
    const session = await this.repository.createSession({
      mode: input.mode,
      capabilities: input.capabilities,
      actorId,
    });
    const event = buildEvent({
      sessionId: session.id,
      generation: session.generation,
      type: "session.started",
      payload: { mode: session.mode },
    });
    const [stored] = await this.repository.appendEvents(session.id, [event]);
    return { session, event: stored };
  }

  async getSession(sessionId) {
    return this.repository.getSession(sessionId);
  }

  /**
   * Apply a guarded transition, emit the mandatory `session.state_changed`
   * event (plus session.ended / emergency.stop on terminal paths), and persist
   * the checkpoint atomically.
   */
  async transition(
    sessionId,
    trigger,
    { actor = "system", correlationId = null, context = {} } = {},
  ) {
    const session = await this.repository.getSession(sessionId);
    if (!session) throw new Error(`Operator session not found: ${sessionId}`);

    const result = transitionOperatorState({
      state: session.state,
      trigger,
      context: {
        previousState: session.previousState,
        resumeState: session.resumeState,
        ...context,
      },
    });

    const events = [
      buildStateChanged({
        sessionId,
        generation: session.generation,
        from: session.state,
        to: result.to,
        trigger,
        actor,
        correlationId,
      }),
    ];

    const checkpointId =
      context.checkpointId ??
      (result.to === "PAUSED" ? crypto.randomUUID() : null);

    const updates = {
      state: result.to,
      previousState: result.checkpoint.previousState,
      resumeState: result.checkpoint.resumeState,
      attempt: context.attempt ?? null,
      checkpointId,
      planId: context.planId ?? null,
      stepId: context.stepId ?? null,
      pendingPause: session.pendingPause ? false : null,
    };
    if (TERMINAL_STATES.includes(result.to)) {
      events.push(
        buildEvent({
          sessionId,
          generation: session.generation,
          type: "session.ended",
          correlationId,
          payload: { from: session.state, to: result.to, trigger, actor },
        }),
      );
      updates.grantsRevoked = true;
      if (result.to === "EMERGENCY_STOPPED") {
        events.push(
          buildEmergencyStop({
            sessionId,
            generation: session.generation,
            actorId: actor === "system" ? null : actor,
            reason: context.reason || "Emergency stop requested",
            source: context.source || "operator",
            activePlanId: session.planId,
            activeStepId: session.stepId,
            grantsRevokedCount: session.grantsRevoked ? 0 : 1,
            toolsCancelledCount: context.toolsCancelledCount ?? 0,
            killSwitchLatched: true,
            correlationId,
          }),
        );
        updates.killSwitchLatched = true;
      }
    }

    const applied = await this.repository.applyTransition(
      sessionId,
      updates,
      events,
    );

    // Deferred pause: if a pause was requested during THINKING/PLANNING and the
    // session has now reached a pausable state, apply it immediately.
    if (
      session.pendingPause &&
      isPausable(result.to) &&
      result.to !== "PAUSED"
    ) {
      return this.transition(sessionId, "pause", { actor, correlationId });
    }

    return {
      session: applied.session,
      events: applied.events,
      transition: { from: session.state, to: result.to, trigger, actor },
    };
  }

  async submitCommand({ sessionId, text, audioRef, sequenceId }) {
    const input = commandSchema.parse({ text, audioRef, sequenceId });
    const session = await this.repository.getSession(sessionId);
    if (!session) throw new Error(`Operator session not found: ${sessionId}`);
    const type = input.text ? "text" : input.audioRef ? "voice" : "sequence";
    const correlationId = `cmd_${crypto.randomUUID()}`;
    const command = await this.repository.createCommand({
      sessionId,
      correlationId,
      type,
      text: input.text || null,
      audioRef: input.audioRef || null,
    });
    const events = [
      buildEvent({
        sessionId,
        generation: session.generation,
        type: "input.received",
        correlationId,
        payload: {
          type,
          sequence_id: input.sequenceId || null,
        },
      }),
    ];
    if (input.text) {
      events.push(
        buildEvent({
          sessionId,
          generation: session.generation,
          type: "transcript.final",
          correlationId,
          payload: { text: input.text },
        }),
      );
    }
    const stored = await this.repository.appendEvents(sessionId, events);
    return { command, events: stored, correlationId };
  }

  /**
   * Operator pause. Deterministic per state:
   *   PAUSABLE ∪ RECOVERY → PAUSED (checkpoint created)
   *   LISTENING/TRANSCRIBING/SPEAKING → cancel to IDLE
   *   THINKING/PLANNING → deferred until the next pausable state
   */
  async pause(
    sessionId,
    { actor = "operator", correlationId = null, reason = null } = {},
  ) {
    const session = await this.repository.getSession(sessionId);
    if (!session) throw new Error(`Operator session not found: ${sessionId}`);
    const policy = pauseRequestPolicy(session.state);

    if (policy.behavior === "none") {
      return { session, policy };
    }
    if (policy.behavior === "cancel") {
      return this.transition(sessionId, policy.trigger, {
        actor,
        correlationId,
        context: { reason },
      });
    }
    if (policy.behavior === "defer") {
      const updated = await this.repository.setPendingPause(sessionId, true);
      return { session: updated, policy, deferred: true };
    }
    // behavior === "pause"
    const checkpointId = crypto.randomUUID();
    const result = await this.transition(sessionId, "pause", {
      actor,
      correlationId,
      context: { reason, checkpointId },
    });
    return { session: result.session, policy, checkpointId };
  }

  /**
   * Resume a paused session: PAUSED → REAUTHORIZING → RECOVERING →
   * (persisted resume_state). Re-authorization is granted by the caller path.
   */
  async resume(
    sessionId,
    { actor = "operator", correlationId = null, reauthGranted = true } = {},
  ) {
    let current = await this.transition(sessionId, "resume_requested", {
      actor,
      correlationId,
    });
    if (reauthGranted) {
      current = await this.transition(sessionId, "reauth_granted", {
        actor,
        correlationId,
      });
      current = await this.transition(sessionId, "checkpoint_validated", {
        actor,
        correlationId,
      });
    }
    return current;
  }

  /** Ordinary cancellation — never an emergency. */
  async cancelSession(
    sessionId,
    { actor = "operator", correlationId = null, reason = null } = {},
  ) {
    const input = cancelSessionSchema.parse({ reason: reason || undefined });
    return this.transition(sessionId, "cancel", {
      actor,
      correlationId,
      context: { reason: input.reason },
    });
  }

  /** Emergency stop — terminal, kill-switch latched, grants revoked. */
  async emergencyStop(
    sessionId,
    {
      actor = "operator",
      correlationId = null,
      reason = null,
      source = "operator",
    } = {},
  ) {
    const input = emergencyStopSchema.parse({ reason: reason || undefined });
    return this.transition(sessionId, "emergency_stop", {
      actor,
      correlationId,
      context: { reason: input.reason, source },
    });
  }

  /**
   * Persist a typed plan and route PLANNING per its policy verdict:
   *   approval_required → AWAITING_APPROVAL
   *   approved          → EXECUTING
   *   denied            → CANCELLED
   */
  async createPlan({
    sessionId,
    correlationId = null,
    intent,
    steps,
    policyVerdict,
    estimatedCost = 0,
  }) {
    const input = planSchema.parse({
      intent,
      steps,
      policyVerdict,
      estimatedCost,
    });
    const session = await this.repository.getSession(sessionId);
    if (!session) throw new Error(`Operator session not found: ${sessionId}`);

    const { plan } = await this.repository.createPlan({
      sessionId,
      generation: session.generation,
      intent: input.intent,
      policyVerdict: input.policyVerdict,
      estimatedCost: input.estimatedCost,
      steps: input.steps,
    });

    const events = [
      buildEvent({
        sessionId,
        generation: session.generation,
        type: "plan.created",
        correlationId,
        payload: { plan_id: plan.id, verdict: input.policyVerdict },
      }),
    ];
    await this.repository.appendEvents(sessionId, events);

    if (input.policyVerdict === "approved") {
      const result = await this.transition(sessionId, "auto_approved", {
        actor: "zarvis",
        correlationId,
        context: { planId: plan.id },
      });
      await this.repository.updatePlanStatus(plan.id, "executing");
      return { plan, session: result.session };
    }
    if (input.policyVerdict === "denied") {
      const result = await this.transition(sessionId, "plan_rejected", {
        actor: "zarvis",
        correlationId,
        context: { planId: plan.id },
      });
      await this.repository.updatePlanStatus(plan.id, "rejected");
      return { plan, session: result.session };
    }
    const result = await this.transition(sessionId, "require_approval", {
      actor: "zarvis",
      correlationId,
      context: { planId: plan.id },
    });
    return { plan, session: result.session };
  }

  async approvePlan(
    planId,
    {
      actor = "operator",
      actorId = null,
      correlationId = null,
      decision = "approved",
    } = {},
  ) {
    const input = planDecisionSchema.parse({ decision });
    const plan = await this.repository.getPlan(planId);
    if (!plan) throw new Error(`Operator plan not found: ${planId}`);
    if (plan.status !== "pending")
      throw new Error(`Operator plan ${planId} is not pending approval`);

    const session = await this.repository.getSession(plan.sessionId);
    if (!session)
      throw new Error(`Operator session not found: ${plan.sessionId}`);
    if (session.state !== "AWAITING_APPROVAL")
      throw new Error(
        `Session ${plan.sessionId} is not awaiting approval (state=${session.state})`,
      );

    const events = [
      buildEvent({
        sessionId: plan.sessionId,
        generation: plan.generation,
        type: "plan.approved",
        correlationId,
        payload: {
          plan_id: plan.id,
          verdict: input.decision,
          actor_id: actorId,
        },
      }),
    ];
    await this.repository.appendEvents(plan.sessionId, events);

    const result = await this.transition(
      plan.sessionId,
      input.decision === "overridden" ? "policy_override" : "approve",
      {
        actor,
        correlationId,
        context: { planId: plan.id },
      },
    );
    await this.repository.updatePlanStatus(plan.id, "approved");
    const updatedPlan = await this.repository.getPlanWithSteps(plan.id);
    return { plan: updatedPlan, session: result.session };
  }

  async rejectPlan(
    planId,
    {
      actor = "operator",
      actorId = null,
      correlationId = null,
      reason = null,
    } = {},
  ) {
    const input = planRejectSchema.parse({ reason: reason || undefined });
    const plan = await this.repository.getPlan(planId);
    if (!plan) throw new Error(`Operator plan not found: ${planId}`);
    if (plan.status !== "pending")
      throw new Error(`Operator plan ${planId} is not pending approval`);

    const session = await this.repository.getSession(plan.sessionId);
    if (!session)
      throw new Error(`Operator session not found: ${plan.sessionId}`);
    if (session.state !== "AWAITING_APPROVAL")
      throw new Error(
        `Session ${plan.sessionId} is not awaiting approval (state=${session.state})`,
      );

    const events = [
      buildEvent({
        sessionId: plan.sessionId,
        generation: plan.generation,
        type: "plan.rejected",
        correlationId,
        payload: { plan_id: plan.id, reason: input.reason, actor_id: actorId },
      }),
    ];
    await this.repository.appendEvents(plan.sessionId, events);

    const result = await this.transition(plan.sessionId, "reject", {
      actor,
      correlationId,
      context: { planId: plan.id, reason: input.reason },
    });
    await this.repository.updatePlanStatus(plan.id, "rejected");
    const updatedPlan = await this.repository.getPlanWithSteps(plan.id);
    return { plan: updatedPlan, session: result.session };
  }

  async getPlan(planId) {
    return this.repository.getPlanWithSteps(planId);
  }

  /** Ordered events for SSE resume: sequence_id > lastSequenceId. */
  async eventsAfter(sessionId, lastSequenceId = 0, limit = 1000) {
    return this.repository.listEventsAfter(sessionId, lastSequenceId, limit);
  }

  // ── Sequence Builder (spec §4.3, §9) ──────────────────────────────────────

  async createSequence({ name, mode, dryRun, steps, actorId = null }) {
    const input = sequenceSchema.parse({ name, mode, dryRun, steps });
    const created = await this.repository.createSequence({
      ...input,
      createdBy: actorId,
    });
    return {
      ...created.sequence,
      steps: created.steps.map(mapSequenceStep),
    };
  }

  async listSequences() {
    return this.repository.listSequences();
  }

  async getSequence(sequenceId) {
    const sequence = await this.repository.getSequenceWithSteps(sequenceId);
    if (!sequence) return null;
    return { ...sequence, steps: sequence.steps.map(mapSequenceStep) };
  }

  async updateSequence(sequenceId, { name, mode, dryRun, steps }) {
    const input = sequenceSchema.parse({ name, mode, dryRun, steps });
    const updated = await this.repository.updateSequence(sequenceId, input);
    if (!updated) throw new Error(`Operator sequence not found: ${sequenceId}`);
    return {
      ...updated.sequence,
      steps: updated.steps.map(mapSequenceStep),
    };
  }

  async deleteSequence(sequenceId) {
    const deleted = await this.repository.deleteSequence(sequenceId);
    if (!deleted) throw new Error(`Operator sequence not found: ${sequenceId}`);
    return { deleted: true };
  }

  async getSequenceRun(runId) {
    const run = await this.repository.getSequenceRunWithSteps(runId);
    if (!run) return null;
    return { ...run, steps: run.steps.map(mapSequenceStep) };
  }

  /**
   * Run a sequence (spec §4.3): sequential steps, `s<N>.result` arg
   * resolution, per-run idempotency, dry-run, and partial-failure stop with
   * resume. Replay after failure requires operator confirmation for
   * high-risk steps.
   */
  async runSequence({
    sequenceId,
    sessionId = null,
    dryRun = false,
    resumeRunId = null,
    confirmReplay = false,
    actorId = null,
  }) {
    const input = sequenceRunSchema.parse({
      dryRun,
      sessionId: sessionId || undefined,
      resumeRunId: resumeRunId || undefined,
      confirmReplay,
    });
    const sequence = await this.repository.getSequenceWithSteps(sequenceId);
    if (!sequence)
      throw new Error(`Operator sequence not found: ${sequenceId}`);

    if (input.resumeRunId) {
      return this.#resumeSequenceRun({
        sequence,
        resumeRunId: input.resumeRunId,
        confirmReplay: input.confirmReplay,
      });
    }

    let session =
      (input.sessionId &&
        (await this.repository.getSession(input.sessionId))) ||
      (await this.repository.findLatestSession({ actorId }));
    if (!session) {
      const created = await this.createSession({
        mode: sequence.mode,
        actorId,
      });
      session = created.session;
    }
    return this.#startSequenceRun({
      sequence,
      session,
      dryRun: input.dryRun,
    });
  }

  async #startSequenceRun({ sequence, session, dryRun }) {
    const { run } = await this.repository.createSequenceRun({
      sequenceId: sequence.id,
      sessionId: session.id,
      dryRun,
    });
    const correlationId = `run_${run.id}`;
    const events = [
      buildEvent({
        sessionId: session.id,
        generation: session.generation,
        type: "input.received",
        correlationId,
        payload: {
          type: "sequence",
          sequence_id: sequence.id,
          run_id: run.id,
          dry_run: dryRun,
        },
      }),
    ];
    const storedEvents = [
      ...(await this.repository.appendEvents(session.id, events)),
    ];

    const resultsById = {};
    for (let index = 0; index < sequence.steps.length; index += 1) {
      const step = sequence.steps[index];
      const outcome = await this.#executeSequenceStep({
        run,
        step,
        session,
        resultsById,
        dryRun,
        correlationId,
      });
      storedEvents.push(...outcome.events);
      if (outcome.failed) {
        const failed = await this.repository.updateSequenceRun(run.id, {
          status: "failed",
          currentStep: step.step_key,
          error: { step: step.step_key, message: outcome.error.message },
        });
        return { run: failed, session, events: storedEvents };
      }
    }
    const succeeded = await this.repository.updateSequenceRun(run.id, {
      status: "succeeded",
    });
    return { run: succeeded, session, events: storedEvents };
  }

  async #resumeSequenceRun({ sequence, resumeRunId, confirmReplay }) {
    const existing = await this.repository.getSequenceRunWithSteps(resumeRunId);
    if (!existing)
      throw new Error(`Operator sequence run not found: ${resumeRunId}`);
    if (existing.sequenceId !== sequence.id)
      throw new Error(
        `Sequence run ${resumeRunId} does not belong to sequence ${sequence.id}`,
      );
    if (existing.status !== "failed")
      throw new Error(
        `Sequence run ${resumeRunId} is not resumable (status=${existing.status})`,
      );

    const session = await this.repository.getSession(existing.sessionId);
    if (!session)
      throw new Error(`Operator session not found: ${existing.sessionId}`);

    const byKey = new Map(existing.steps.map((step) => [step.step_key, step]));
    const resultsById = {};
    let resumeFrom = null;
    for (const step of sequence.steps) {
      const stored = byKey.get(step.step_key);
      if (stored && stored.status === "succeeded") {
        resultsById[step.step_key] = stored.result;
        continue;
      }
      resumeFrom = step;
      break;
    }
    if (!resumeFrom) {
      const completed = await this.repository.updateSequenceRun(resumeRunId, {
        status: "succeeded",
      });
      return { run: completed, session, events: [] };
    }

    // High-risk replay requires operator confirmation (§4.3).
    if (isHighRiskStep(resumeFrom) && !confirmReplay) {
      const error = new Error(
        `Replaying step ${resumeFrom.step_key} requires operator confirmation (high-risk)`,
      );
      error.code = "CONFIRMATION_REQUIRED";
      throw error;
    }

    await this.repository.updateSequenceRun(resumeRunId, { status: "running" });
    const correlationId = `run_${resumeRunId}`;
    const storedEvents = [];
    for (const step of sequence.steps) {
      const stored = byKey.get(step.step_key);
      if (stored && stored.status === "succeeded") continue;
      const outcome = await this.#executeSequenceStep({
        run: existing,
        step,
        session,
        resultsById,
        dryRun: existing.dryRun,
        correlationId,
      });
      storedEvents.push(...outcome.events);
      if (outcome.failed) {
        const failed = await this.repository.updateSequenceRun(resumeRunId, {
          status: "failed",
          currentStep: step.step_key,
          error: { step: step.step_key, message: outcome.error.message },
        });
        return { run: failed, session, events: storedEvents };
      }
    }
    const completed = await this.repository.updateSequenceRun(resumeRunId, {
      status: "succeeded",
    });
    return { run: completed, session, events: storedEvents };
  }

  async #executeSequenceStep({
    run,
    step,
    session,
    resultsById,
    dryRun,
    correlationId,
  }) {
    const started = buildEvent({
      sessionId: session.id,
      generation: session.generation,
      type: "step.started",
      correlationId,
      payload: {
        plan_id: null,
        step_id: step.step_key,
        tool: step.intent,
        run_id: run.id,
        sequence_id: run.sequenceId,
      },
    });
    await this.repository.setSequenceRunStep(run.id, step.step_key, {
      status: "running",
    });
    try {
      const args = resolveStepArgs(step.args, resultsById, step.step_key);
      const result = await executeSequenceStep({
        intent: step.intent,
        args,
        context: { session, repository: this.repository, dryRun },
      });
      resultsById[step.step_key] = result;
      await this.repository.setSequenceRunStep(run.id, step.step_key, {
        status: "succeeded",
        result,
      });
      const finished = buildEvent({
        sessionId: session.id,
        generation: session.generation,
        type: "step.finished",
        correlationId,
        payload: {
          plan_id: null,
          step_id: step.step_key,
          tool: step.intent,
          result,
          run_id: run.id,
          sequence_id: run.sequenceId,
        },
      });
      const stored = await this.repository.appendEvents(session.id, [
        started,
        finished,
      ]);
      return { failed: false, events: stored };
    } catch (error) {
      await this.repository.setSequenceRunStep(run.id, step.step_key, {
        status: "failed",
        error: { message: error.message, code: error.code ?? null },
      });
      const failed = buildEvent({
        sessionId: session.id,
        generation: session.generation,
        type: "step.failed",
        correlationId,
        payload: {
          plan_id: null,
          step_id: step.step_key,
          tool: step.intent,
          error: error.message,
          run_id: run.id,
          sequence_id: run.sequenceId,
        },
      });
      const stored = await this.repository.appendEvents(session.id, [
        started,
        failed,
      ]);
      return { failed: true, error, events: stored };
    }
  }
}

module.exports = { OperatorRuntimeService };
