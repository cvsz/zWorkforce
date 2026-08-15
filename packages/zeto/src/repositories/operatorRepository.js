"use strict";

const { IDLE } = require("../domain/operatorStateMachine");

function mapSession(row) {
  if (!row) return null;
  return {
    id: row.id,
    generation: row.generation,
    mode: row.mode,
    capabilities: row.capabilities || [],
    state: row.state,
    previousState: row.previous_state,
    resumeState: row.resume_state,
    checkpointId: row.checkpoint_id,
    planId: row.plan_id,
    stepId: row.step_id,
    attempt: row.attempt,
    pendingPause: row.pending_pause,
    grantsRevoked: row.grants_revoked,
    killSwitchLatched: row.kill_switch_latched,
    lastSequenceId: Number(row.last_sequence_id),
    actorId: row.actor_id,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function mapEvent(row) {
  if (!row) return null;
  return {
    event_id: row.event_id,
    session_id: row.session_id,
    generation: row.generation,
    sequence_id: Number(row.sequence_id),
    type: row.type,
    occurred_at: row.occurred_at,
    correlation_id: row.correlation_id,
    payload: row.payload || {},
  };
}

function mapPlan(row) {
  if (!row) return null;
  return {
    id: row.id,
    sessionId: row.session_id,
    generation: row.generation,
    intent: row.intent,
    policyVerdict: row.policy_verdict,
    estimatedCost: Number(row.estimated_cost),
    status: row.status,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function mapSequence(row) {
  if (!row) return null;
  return {
    id: row.id,
    name: row.name,
    mode: row.mode,
    dryRun: row.dry_run,
    createdBy: row.created_by,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function mapSequenceRun(row) {
  if (!row) return null;
  return {
    id: row.id,
    sequenceId: row.sequence_id,
    sessionId: row.session_id,
    dryRun: row.dry_run,
    status: row.status,
    currentStep: row.current_step,
    error: row.error || null,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

class OperatorRepository {
  constructor(pool) {
    this.pool = pool;
  }

  async createSession({ mode, capabilities = [], actorId = null }) {
    const result = await this.pool.query(
      `INSERT INTO operator_sessions(generation, mode, capabilities, state, actor_id)
       VALUES (1, $1, $2, $3, $4) RETURNING *`,
      [mode, JSON.stringify(capabilities), IDLE, actorId],
    );
    return mapSession(result.rows[0]);
  }

  async getSession(sessionId) {
    const result = await this.pool.query(
      "SELECT * FROM operator_sessions WHERE id = $1",
      [sessionId],
    );
    return mapSession(result.rows[0]);
  }

  /** Most recent non-terminal session for an actor (for sequence run intake). */
  async findLatestSession({ actorId = null, excludeTerminal = true } = {}) {
    const result = await this.pool.query(
      `SELECT * FROM operator_sessions
       WHERE ($1::uuid IS NULL OR actor_id = $1)
         AND ($2::boolean = false OR state NOT IN ('FAILED','CANCELLED','EMERGENCY_STOPPED'))
       ORDER BY created_at DESC LIMIT 1`,
      [actorId, excludeTerminal],
    );
    return mapSession(result.rows[0]);
  }

  /**
   * Atomically reserve the next `count` sequence ids for (session_id, generation)
   * and return the first reserved id. Must run on the caller's transaction
   * client so the reservation is atomic with the event inserts. The
   * UNIQUE(session_id, generation, sequence_id) constraint backstops monotonicity.
   */
  async #reserveSequence(client, sessionId, count) {
    const result = await client.query(
      `UPDATE operator_sessions
         SET last_sequence_id = last_sequence_id + $2, updated_at = now()
       WHERE id = $1 RETURNING last_sequence_id`,
      [sessionId, count],
    );
    if (!result.rowCount)
      throw new Error(`Operator session not found: ${sessionId}`);
    return Number(result.rows[0].last_sequence_id) - count + 1;
  }

  /**
   * Apply a state transition: update the session state/checkpoint and append
   * the emitted events with monotonic sequence ids — all in one transaction so
   * state and events never diverge.
   */
  async applyTransition(sessionId, updates, events) {
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const startSequence = await this.#reserveSequence(
        client,
        sessionId,
        events.length,
      );
      const session = await client.query(
        `UPDATE operator_sessions SET
           state = $2,
           previous_state = $3,
           resume_state = $4,
           checkpoint_id = COALESCE($5, checkpoint_id),
           plan_id = COALESCE($6, plan_id),
           step_id = COALESCE($7, step_id),
           attempt = COALESCE($8, attempt),
           pending_pause = COALESCE($9, pending_pause),
           grants_revoked = COALESCE($10, grants_revoked),
           kill_switch_latched = COALESCE($11, kill_switch_latched),
           updated_at = now()
         WHERE id = $1 RETURNING *`,
        [
          sessionId,
          updates.state,
          updates.previousState ?? null,
          updates.resumeState ?? null,
          updates.checkpointId ?? null,
          updates.planId ?? null,
          updates.stepId ?? null,
          updates.attempt ?? null,
          updates.pendingPause ?? null,
          updates.grantsRevoked ?? null,
          updates.killSwitchLatched ?? null,
        ],
      );
      if (!session.rowCount)
        throw new Error(`Operator session not found: ${sessionId}`);
      const stored = [];
      for (let index = 0; index < events.length; index += 1) {
        const event = events[index];
        const inserted = await client.query(
          `INSERT INTO operator_events(
             event_id, session_id, generation, sequence_id, type,
             occurred_at, correlation_id, payload
           ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *`,
          [
            event.event_id,
            sessionId,
            event.generation,
            startSequence + index,
            event.type,
            event.occurred_at,
            event.correlation_id,
            JSON.stringify(event.payload || {}),
          ],
        );
        stored.push(mapEvent(inserted.rows[0]));
      }
      await client.query("COMMIT");
      return { session: mapSession(session.rows[0]), events: stored };
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  /** Mark a deferred pause so it is applied at the next pausable state. */
  async setPendingPause(sessionId, pendingPause) {
    const result = await this.pool.query(
      `UPDATE operator_sessions SET pending_pause = $2, updated_at = now()
       WHERE id = $1 RETURNING *`,
      [sessionId, pendingPause],
    );
    return mapSession(result.rows[0]);
  }

  /** Append events without a state change (e.g. session.started). */
  async appendEvents(sessionId, events) {
    if (!events.length) return [];
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const startSequence = await this.#reserveSequence(
        client,
        sessionId,
        events.length,
      );
      const stored = [];
      for (let index = 0; index < events.length; index += 1) {
        const event = events[index];
        const inserted = await client.query(
          `INSERT INTO operator_events(
             event_id, session_id, generation, sequence_id, type,
             occurred_at, correlation_id, payload
           ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *`,
          [
            event.event_id,
            sessionId,
            event.generation,
            startSequence + index,
            event.type,
            event.occurred_at,
            event.correlation_id,
            JSON.stringify(event.payload || {}),
          ],
        );
        stored.push(mapEvent(inserted.rows[0]));
      }
      await client.query("COMMIT");
      return stored;
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  /** Ordered replay for SSE/WebSocket resume: sequence_id > lastSequenceId. */
  async listEventsAfter(sessionId, lastSequenceId = 0, limit = 1000) {
    const result = await this.pool.query(
      `SELECT * FROM operator_events
       WHERE session_id = $1 AND sequence_id > $2
       ORDER BY sequence_id ASC
       LIMIT $3`,
      [sessionId, lastSequenceId, limit],
    );
    return result.rows.map(mapEvent);
  }

  async createCommand({
    sessionId,
    correlationId,
    type,
    text = null,
    audioRef = null,
  }) {
    const result = await this.pool.query(
      `INSERT INTO operator_commands(session_id, correlation_id, type, text, audio_ref, status)
       VALUES ($1, $2, $3, $4, $5, 'received') RETURNING *`,
      [sessionId, correlationId, type, text, audioRef],
    );
    return result.rows[0];
  }

  async getCommand(commandId) {
    const result = await this.pool.query(
      "SELECT * FROM operator_commands WHERE id = $1",
      [commandId],
    );
    return result.rows[0] || null;
  }

  async createPlan({
    sessionId,
    generation,
    intent,
    policyVerdict,
    estimatedCost,
    steps,
  }) {
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const plan = await client.query(
        `INSERT INTO operator_plans(session_id, generation, intent, policy_verdict, estimated_cost, status)
         VALUES ($1, $2, $3, $4, $5, 'pending') RETURNING *`,
        [sessionId, generation, intent, policyVerdict, estimatedCost],
      );
      const planRow = plan.rows[0];
      const storedSteps = [];
      for (const step of steps) {
        const stepRow = await client.query(
          `INSERT INTO operator_plan_steps(
             plan_id, step_key, tool, args, risk, depends_on, status, idempotency_key
           ) VALUES ($1, $2, $3, $4, $5, $6, 'queued', $7) RETURNING *`,
          [
            planRow.id,
            step.stepId,
            step.tool,
            JSON.stringify(step.args || {}),
            step.risk,
            JSON.stringify(step.dependsOn || []),
            `${sessionId}:${generation}:${planRow.id}:${step.stepId}`,
          ],
        );
        storedSteps.push(stepRow.rows[0]);
      }
      await client.query("COMMIT");
      return { plan: mapPlan(planRow), steps: storedSteps };
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async getPlan(planId) {
    const result = await this.pool.query(
      "SELECT * FROM operator_plans WHERE id = $1",
      [planId],
    );
    return mapPlan(result.rows[0]);
  }

  async getPlanWithSteps(planId) {
    const plan = await this.getPlan(planId);
    if (!plan) return null;
    const steps = await this.pool.query(
      "SELECT * FROM operator_plan_steps WHERE plan_id = $1 ORDER BY step_key",
      [planId],
    );
    return { ...plan, steps: steps.rows };
  }

  async updatePlanStatus(planId, status) {
    const result = await this.pool.query(
      `UPDATE operator_plans SET status = $2, updated_at = now()
       WHERE id = $1 RETURNING *`,
      [planId, status],
    );
    return mapPlan(result.rows[0]);
  }

  /**
   * Idempotent tool execution: UNIQUE(session_id, generation, idempotency_key)
   * — replaying the same step within the same session/generation returns the
   * stored row instead of creating a duplicate.
   */
  async recordToolExecution({
    sessionId,
    generation,
    planId = null,
    stepId = null,
    tool,
    action,
    args = {},
    risk,
    approval = "not_required",
    idempotencyKey,
  }) {
    const result = await this.pool.query(
      `INSERT INTO tool_executions(
         session_id, generation, plan_id, step_id, tool, action, args, risk,
         approval, idempotency_key, status
       ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'running')
       ON CONFLICT (session_id, generation, idempotency_key) DO NOTHING
       RETURNING *`,
      [
        sessionId,
        generation,
        planId,
        stepId,
        tool,
        action || null,
        JSON.stringify(args),
        risk || null,
        approval,
        idempotencyKey,
      ],
    );
    if (result.rowCount) return result.rows[0];
    const existing = await this.pool.query(
      `SELECT * FROM tool_executions
       WHERE session_id = $1 AND generation = $2 AND idempotency_key = $3`,
      [sessionId, generation, idempotencyKey],
    );
    return existing.rows[0] || null;
  }

  async finishToolExecution(
    executionId,
    { status, response = null, durationMs = null },
  ) {
    const result = await this.pool.query(
      `UPDATE tool_executions SET status = $2, response = COALESCE($3, response),
         duration_ms = COALESCE($4, duration_ms), updated_at = now()
       WHERE id = $1 RETURNING *`,
      [
        executionId,
        status,
        response ? JSON.stringify(response) : null,
        durationMs,
      ],
    );
    return result.rows[0] || null;
  }

  async recordVerificationEvidence({
    stepId = null,
    executionId = null,
    status,
    evidence = {},
  }) {
    const result = await this.pool.query(
      `INSERT INTO verification_evidence(step_id, execution_id, status, evidence)
       VALUES ($1, $2, $3, $4) RETURNING *`,
      [stepId, executionId, status, JSON.stringify(evidence)],
    );
    return result.rows[0];
  }

  // ── Sequence Builder (spec §4.3) ──────────────────────────────────────────

  async createSequence({ name, mode, dryRun, steps, createdBy = null }) {
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const sequence = await client.query(
        `INSERT INTO operator_sequences(name, mode, dry_run, created_by)
         VALUES ($1, $2, $3, $4) RETURNING *`,
        [name, mode, dryRun, createdBy],
      );
      const sequenceRow = sequence.rows[0];
      const storedSteps = [];
      for (let index = 0; index < steps.length; index += 1) {
        const step = steps[index];
        const row = await client.query(
          `INSERT INTO operator_sequence_steps(
             sequence_id, step_key, position, intent, args, risk
           ) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
          [
            sequenceRow.id,
            step.id,
            index + 1,
            step.intent,
            JSON.stringify(step.args || {}),
            step.risk ?? "none",
          ],
        );
        storedSteps.push(row.rows[0]);
      }
      await client.query("COMMIT");
      return { sequence: mapSequence(sequenceRow), steps: storedSteps };
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async listSequences() {
    const result = await this.pool.query(
      `SELECT s.*, count(st.id)::int AS step_count
       FROM operator_sequences s
       LEFT JOIN operator_sequence_steps st ON st.sequence_id = s.id
       GROUP BY s.id
       ORDER BY s.created_at DESC`,
    );
    return result.rows.map((row) => ({
      ...mapSequence(row),
      stepCount: row.step_count,
    }));
  }

  async getSequence(sequenceId) {
    const result = await this.pool.query(
      "SELECT * FROM operator_sequences WHERE id = $1",
      [sequenceId],
    );
    return mapSequence(result.rows[0]);
  }

  async getSequenceWithSteps(sequenceId) {
    const sequence = await this.getSequence(sequenceId);
    if (!sequence) return null;
    const steps = await this.pool.query(
      `SELECT * FROM operator_sequence_steps
       WHERE sequence_id = $1 ORDER BY position ASC`,
      [sequenceId],
    );
    return { ...sequence, steps: steps.rows };
  }

  async updateSequence(sequenceId, { name, mode, dryRun, steps }) {
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const sequence = await client.query(
        `UPDATE operator_sequences
         SET name = $2, mode = $3, dry_run = $4, updated_at = now()
         WHERE id = $1 RETURNING *`,
        [sequenceId, name, mode, dryRun],
      );
      if (!sequence.rowCount) return null;
      await client.query(
        "DELETE FROM operator_sequence_steps WHERE sequence_id = $1",
        [sequenceId],
      );
      const storedSteps = [];
      for (let index = 0; index < steps.length; index += 1) {
        const step = steps[index];
        const row = await client.query(
          `INSERT INTO operator_sequence_steps(
             sequence_id, step_key, position, intent, args, risk
           ) VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
          [
            sequenceId,
            step.id,
            index + 1,
            step.intent,
            JSON.stringify(step.args || {}),
            step.risk ?? "none",
          ],
        );
        storedSteps.push(row.rows[0]);
      }
      await client.query("COMMIT");
      return { sequence: mapSequence(sequence.rows[0]), steps: storedSteps };
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async deleteSequence(sequenceId) {
    const result = await this.pool.query(
      "DELETE FROM operator_sequences WHERE id = $1 RETURNING id",
      [sequenceId],
    );
    return Boolean(result.rowCount);
  }

  /** Create a run + queued run-steps. Step idempotency is scoped per run. */
  async createSequenceRun({ sequenceId, sessionId, dryRun }) {
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const run = await client.query(
        `INSERT INTO operator_sequence_runs(sequence_id, session_id, dry_run, status)
         VALUES ($1, $2, $3, 'running') RETURNING *`,
        [sequenceId, sessionId, dryRun],
      );
      const runRow = run.rows[0];
      const steps = await client.query(
        `SELECT * FROM operator_sequence_steps
         WHERE sequence_id = $1 ORDER BY position ASC`,
        [sequenceId],
      );
      const runSteps = [];
      for (const step of steps.rows) {
        const row = await client.query(
          `INSERT INTO operator_sequence_run_steps(
             run_id, step_key, position, intent, args, risk, status, idempotency_key
           ) VALUES ($1, $2, $3, $4, $5, $6, 'queued', $7) RETURNING *`,
          [
            runRow.id,
            step.step_key,
            step.position,
            step.intent,
            JSON.stringify(step.args || {}),
            step.risk ?? "none",
            `${runRow.id}:${step.step_key}`,
          ],
        );
        runSteps.push(row.rows[0]);
      }
      await client.query("COMMIT");
      return { run: mapSequenceRun(runRow), steps: runSteps };
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async getSequenceRun(runId) {
    const result = await this.pool.query(
      "SELECT * FROM operator_sequence_runs WHERE id = $1",
      [runId],
    );
    return mapSequenceRun(result.rows[0]);
  }

  async getSequenceRunWithSteps(runId) {
    const run = await this.getSequenceRun(runId);
    if (!run) return null;
    const steps = await this.pool.query(
      `SELECT * FROM operator_sequence_run_steps
       WHERE run_id = $1 ORDER BY position ASC`,
      [runId],
    );
    return { ...run, steps: steps.rows };
  }

  async updateSequenceRun(runId, { status, currentStep = null, error = null }) {
    const result = await this.pool.query(
      `UPDATE operator_sequence_runs SET status = $2,
         current_step = COALESCE($3, current_step),
         error = COALESCE($4, error),
         updated_at = now()
       WHERE id = $1 RETURNING *`,
      [runId, status, currentStep, error ? JSON.stringify(error) : null],
    );
    return mapSequenceRun(result.rows[0]);
  }

  /**
   * Update one run-step. Run steps are pre-created at run start (UNIQUE(run_id,
   * step_key)), so replay within the same run updates the stored row rather
   * than creating a duplicate — the scoped idempotency contract (§4.3).
   */
  async setSequenceRunStep(
    runId,
    stepKey,
    { status, result = null, error = null },
  ) {
    const resultRow = await this.pool.query(
      `UPDATE operator_sequence_run_steps
       SET status = $3,
           result = COALESCE($4, result),
           error = COALESCE($5, error),
           updated_at = now()
       WHERE run_id = $1 AND step_key = $2
       RETURNING *`,
      [
        runId,
        stepKey,
        status,
        result !== null ? JSON.stringify(result) : null,
        error !== null ? JSON.stringify(error) : null,
      ],
    );
    if (!resultRow.rowCount)
      throw new Error(`Sequence run step not found: ${runId}:${stepKey}`);
    return resultRow.rows[0];
  }
}

module.exports = { OperatorRepository };
