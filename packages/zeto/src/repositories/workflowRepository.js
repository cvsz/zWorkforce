const crypto = require("node:crypto");

class WorkflowRepository {
  constructor(pool) {
    this.pool = pool;
  }

  async createDefinition({ brandId, name, steps }) {
    if (!Array.isArray(steps) || steps.length === 0) {
      throw new Error("Workflow requires at least one step");
    }
    const keys = new Set();
    for (const step of steps) {
      if (!step.key || !step.owner || keys.has(step.key)) {
        throw new Error("Workflow step keys and owners must be unique");
      }
      keys.add(step.key);
    }
    const result = await this.pool.query(
      `INSERT INTO workflows(brand_id, name, definition)
       VALUES ($1, $2, $3) RETURNING *`,
      [brandId, name, JSON.stringify({ steps })],
    );
    return result.rows[0];
  }

  async start(workflowId, input = {}, commandKey) {
    if (!commandKey) throw new Error("Workflow run command key is required");
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const workflow = (
        await client.query(
          "SELECT * FROM workflows WHERE id = $1 AND active = true FOR UPDATE",
          [workflowId],
        )
      ).rows[0];
      if (!workflow) throw new Error("Active workflow not found");
      const runResult = await client.query(
        `INSERT INTO workflow_runs(workflow_id, status, input, started_at, command_key, trace_id)
           VALUES ($1, 'running', $2, now(), $3, $4)
           ON CONFLICT (command_key) WHERE command_key IS NOT NULL DO NOTHING
           RETURNING *`,
        [
          workflowId,
          JSON.stringify(input),
          commandKey,
          input.traceId || crypto.randomBytes(16).toString("hex"),
        ],
      );
      if (!runResult.rowCount) {
        const existing = (
          await client.query(
            "SELECT * FROM workflow_runs WHERE command_key = $1",
            [commandKey],
          )
        ).rows[0];
        if (existing.workflow_id !== workflowId) {
          throw new Error("Workflow command key reused for another workflow");
        }
        await client.query("COMMIT");
        return existing;
      }
      const run = runResult.rows[0];
      for (const [index, step] of workflow.definition.steps.entries()) {
        await client.query(
          `INSERT INTO workflow_steps(
             workflow_run_id, step_key, owner, input, timeout_ms, max_attempts,
             idempotency_key, available_at, step_order
           ) VALUES ($1, $2, $3, $4, $5, $6, $7, now(), $8)`,
          [
            run.id,
            step.key,
            step.owner,
            JSON.stringify(index === 0 ? input : {}),
            step.timeoutMs || 120000,
            step.maxAttempts || 3,
            `${run.id}:${step.key}`,
            index,
          ],
        );
      }
      await client.query("COMMIT");
      return run;
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async claimNext(runId, workerId) {
    const result = await this.pool.query(
      `WITH candidate AS (
         SELECT current.id,
           CASE WHEN current.attempt > 0 THEN current.input
             ELSE COALESCE(previous.output, current.input) END AS artifact
         FROM workflow_steps current
         LEFT JOIN LATERAL (
           SELECT output FROM workflow_steps prior
           WHERE prior.workflow_run_id = current.workflow_run_id
             AND prior.step_order < current.step_order
           ORDER BY prior.step_order DESC LIMIT 1
         ) previous ON true
         WHERE current.workflow_run_id = $1
           AND current.status IN ('queued','retry_wait')
           AND current.available_at <= now()
           AND NOT EXISTS (
             SELECT 1 FROM workflow_steps blocked
             WHERE blocked.workflow_run_id = current.workflow_run_id
               AND blocked.step_order < current.step_order
               AND blocked.status <> 'succeeded'
           )
         ORDER BY current.step_order
         FOR UPDATE OF current SKIP LOCKED LIMIT 1
       )
       UPDATE workflow_steps SET status = 'running', worker_id = $2,
         heartbeat_at = now(), attempt = attempt + 1,
         input = candidate.artifact, updated_at = now()
       FROM candidate WHERE workflow_steps.id = candidate.id
       RETURNING workflow_steps.*`,
      [runId, workerId],
    );
    return result.rows[0] || null;
  }

  async heartbeat(stepId, workerId) {
    return this.#ownedUpdate(
      stepId,
      workerId,
      "heartbeat_at = now(), updated_at = now()",
      [],
    );
  }

  async succeed(stepId, workerId, output = {}, cost = 0) {
    if (!Number.isFinite(cost) || cost < 0)
      throw new Error("Invalid step cost");
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const step = (
        await client.query(
          `UPDATE workflow_steps SET status = 'succeeded', output = $3, cost = $4,
             worker_id = NULL, heartbeat_at = now(), updated_at = now()
           WHERE id = $1 AND worker_id = $2 AND status = 'running' RETURNING *`,
          [stepId, workerId, JSON.stringify(output), cost],
        )
      ).rows[0];
      if (!step) throw new Error("Workflow step is not owned by this worker");
      const remaining = await client.query(
        `SELECT 1 FROM workflow_steps
         WHERE workflow_run_id = $1 AND status <> 'succeeded' LIMIT 1`,
        [step.workflow_run_id],
      );
      await client.query(
        `UPDATE workflow_runs SET cost = (
           SELECT COALESCE(sum(cost), 0) FROM workflow_steps WHERE workflow_run_id = $1
         ), status = $2,
         output = CASE WHEN $2 = 'succeeded' THEN $3 ELSE output END,
         finished_at = CASE WHEN $2 = 'succeeded' THEN now() ELSE finished_at END,
         updated_at = now() WHERE id = $1`,
        [
          step.workflow_run_id,
          remaining.rowCount ? "running" : "succeeded",
          JSON.stringify(output),
        ],
      );
      await client.query("COMMIT");
      return step;
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async fail(stepId, workerId, error, retryDelayMs = 0, terminal = false) {
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const step = (
        await client.query(
          `UPDATE workflow_steps SET
             status = CASE WHEN $5 OR attempt >= max_attempts THEN 'failed' ELSE 'retry_wait' END,
             error = $3, available_at = now() + ($4 * interval '1 millisecond'),
             worker_id = NULL, updated_at = now()
           WHERE id = $1 AND worker_id = $2 AND status = 'running' RETURNING *`,
          [
            stepId,
            workerId,
            JSON.stringify(error || {}),
            retryDelayMs,
            terminal,
          ],
        )
      ).rows[0];
      if (!step) throw new Error("Workflow step is not owned by this worker");
      if (step.status === "failed") {
        await client.query(
          `UPDATE workflow_runs SET status = 'failed', finished_at = now(), updated_at = now()
           WHERE id = $1`,
          [step.workflow_run_id],
        );
      }
      await client.query("COMMIT");
      return step;
    } catch (error_) {
      await client.query("ROLLBACK");
      throw error_;
    } finally {
      client.release();
    }
  }

  async block(stepId, workerId, output = {}, reason = {}) {
    const result = await this.pool.query(
      `UPDATE workflow_steps SET status = 'blocked', output = $3, error = $4,
         worker_id = NULL, heartbeat_at = now(), updated_at = now()
       WHERE id = $1 AND worker_id = $2 AND status = 'running' RETURNING *`,
      [stepId, workerId, JSON.stringify(output), JSON.stringify(reason)],
    );
    if (!result.rowCount)
      throw new Error("Workflow step is not owned by this worker");
    return result.rows[0];
  }

  async resumeBlocked(runId, stepKey, input = {}) {
    const result = await this.pool.query(
      `UPDATE workflow_steps SET status = 'queued', input = output || $3::jsonb,
         error = NULL, available_at = now(), updated_at = now()
       WHERE workflow_run_id = $1 AND step_key = $2 AND status = 'blocked'
       RETURNING *`,
      [runId, stepKey, JSON.stringify(input)],
    );
    if (!result.rowCount) throw new Error("Blocked workflow step not found");
    return result.rows[0];
  }

  async startSpan(run, step, attributes = {}) {
    const result = await this.pool.query(
      `INSERT INTO workflow_spans(trace_id, workflow_run_id, workflow_step_id, name, status, attributes)
       VALUES ($1, $2, $3, $4, 'running', $5) RETURNING *`,
      [
        run.trace_id,
        run.id,
        step.id,
        step.step_key,
        JSON.stringify(attributes),
      ],
    );
    return result.rows[0];
  }

  async finishSpan(spanId, status, { attributes = {}, error = null } = {}) {
    if (!["succeeded", "failed", "blocked"].includes(status))
      throw new Error("Invalid terminal span status");
    const result = await this.pool.query(
      `UPDATE workflow_spans SET status = $2, attributes = attributes || $3::jsonb,
         error = $4, finished_at = now(), updated_at = now()
       WHERE id = $1 AND status = 'running' RETURNING *`,
      [spanId, status, JSON.stringify(attributes), JSON.stringify(error)],
    );
    if (!result.rowCount) throw new Error("Running workflow span not found");
    return result.rows[0];
  }

  async cancel(runId) {
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const run = (
        await client.query(
          `UPDATE workflow_runs SET status = 'cancelled', finished_at = now(), updated_at = now()
           WHERE id = $1 AND status IN ('queued','running','paused') RETURNING *`,
          [runId],
        )
      ).rows[0];
      if (!run) throw new Error("Workflow run cannot be cancelled");
      await client.query(
        `UPDATE workflow_steps SET status = 'cancelled', worker_id = NULL, updated_at = now()
         WHERE workflow_run_id = $1 AND status IN ('queued','running','retry_wait','blocked')`,
        [runId],
      );
      await client.query("COMMIT");
      return run;
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async requeueStuck(staleBefore) {
    const client = await this.pool.connect();
    try {
      await client.query("BEGIN");
      const result = await client.query(
        `UPDATE workflow_steps SET
           status = CASE WHEN attempt < max_attempts THEN 'retry_wait' ELSE 'failed' END,
           error = jsonb_build_object('code', 'WORKER_TIMEOUT'),
           available_at = now(), worker_id = NULL, updated_at = now()
         WHERE status = 'running' AND heartbeat_at < $1 RETURNING *`,
        [staleBefore],
      );
      await client.query(
        `UPDATE workflow_runs run SET status = 'failed', finished_at = now(), updated_at = now()
         WHERE run.status = 'running' AND EXISTS (
           SELECT 1 FROM workflow_steps step
           WHERE step.workflow_run_id = run.id AND step.status = 'failed'
         )`,
      );
      await client.query("COMMIT");
      return result.rows;
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }

  async getRun(runId) {
    const run = (
      await this.pool.query("SELECT * FROM workflow_runs WHERE id = $1", [
        runId,
      ])
    ).rows[0];
    if (!run) return null;
    run.steps = (
      await this.pool.query(
        "SELECT * FROM workflow_steps WHERE workflow_run_id = $1 ORDER BY step_order",
        [runId],
      )
    ).rows;
    run.spans = (
      await this.pool.query(
        "SELECT * FROM workflow_spans WHERE workflow_run_id = $1 ORDER BY started_at, id",
        [runId],
      )
    ).rows;
    return run;
  }

  async listRuns({ brandId, limit = 25 }) {
    const result = await this.pool.query(
      `SELECT run.*, workflow.name AS workflow_name,
         count(step.id)::integer AS step_count,
         count(step.id) FILTER (WHERE step.status = 'succeeded')::integer AS succeeded_steps,
         count(step.id) FILTER (WHERE step.status = 'blocked')::integer AS blocked_steps
       FROM workflow_runs run
       JOIN workflows workflow ON workflow.id = run.workflow_id
       LEFT JOIN workflow_steps step ON step.workflow_run_id = run.id
       WHERE workflow.brand_id = $1
       GROUP BY run.id, workflow.name
       ORDER BY run.created_at DESC, run.id DESC LIMIT $2`,
      [brandId, Math.min(Math.max(limit, 1), 100)],
    );
    return result.rows;
  }

  async #ownedUpdate(stepId, workerId, setters, values) {
    const params = [stepId, workerId, ...values];
    const result = await this.pool.query(
      `UPDATE workflow_steps SET ${setters}
       WHERE id = $1 AND worker_id = $2 AND status = 'running' RETURNING *`,
      params,
    );
    if (!result.rowCount)
      throw new Error("Workflow step is not owned by this worker");
    return result.rows[0];
  }
}

module.exports = { WorkflowRepository };
