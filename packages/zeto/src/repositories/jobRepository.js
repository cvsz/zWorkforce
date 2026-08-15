class JobRepository {
  constructor(pool) {
    this.pool = pool;
  }

  async enqueue(job) {
    const result = await this.pool.query(
      `INSERT INTO jobs(type, owner, payload, idempotency_key, workflow_run_id, max_attempts, timeout_ms)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       ON CONFLICT(idempotency_key) DO UPDATE SET idempotency_key = EXCLUDED.idempotency_key
       RETURNING *`,
      [
        job.type,
        job.owner,
        JSON.stringify(job.payload || {}),
        job.idempotencyKey,
        job.workflowRunId || null,
        job.maxAttempts || 3,
        job.timeoutMs || 120000,
      ],
    );
    return result.rows[0];
  }

  async claim(workerId) {
    const result = await this.pool.query(
      `WITH candidate AS (
         SELECT id FROM jobs
         WHERE status IN ('queued','retry_wait') AND available_at <= now()
         ORDER BY available_at, created_at
         FOR UPDATE SKIP LOCKED LIMIT 1
       )
       UPDATE jobs SET status = 'running', worker_id = $1, claimed_at = now(), heartbeat_at = now(),
         attempt = attempt + 1, updated_at = now()
       FROM candidate WHERE jobs.id = candidate.id RETURNING jobs.*`,
      [workerId],
    );
    return result.rows[0] || null;
  }

  async heartbeat(jobId, workerId) {
    const result = await this.pool.query(
      `UPDATE jobs SET heartbeat_at = now(), updated_at = now()
       WHERE id = $1 AND worker_id = $2 AND status = 'running'
       RETURNING *`,
      [jobId, workerId],
    );
    if (!result.rowCount) throw new Error("Job is not owned by this worker");
    return result.rows[0];
  }

  async succeed(jobId, workerId, output = {}) {
    const result = await this.pool.query(
      `UPDATE jobs SET status = 'succeeded', result = $3, worker_id = NULL,
         heartbeat_at = now(), updated_at = now()
       WHERE id = $1 AND worker_id = $2 AND status = 'running'
       RETURNING *`,
      [jobId, workerId, JSON.stringify(output)],
    );
    if (!result.rowCount) throw new Error("Job is not owned by this worker");
    return result.rows[0];
  }

  async fail(jobId, workerId, error, retryDelayMs) {
    const result = await this.pool.query(
      `UPDATE jobs SET
         status = CASE WHEN attempt < max_attempts THEN 'retry_wait' ELSE 'failed' END,
         error = $3,
         available_at = CASE WHEN attempt < max_attempts
           THEN now() + ($4 * interval '1 millisecond') ELSE available_at END,
         worker_id = NULL, updated_at = now()
       WHERE id = $1 AND worker_id = $2 AND status = 'running'
       RETURNING *`,
      [jobId, workerId, JSON.stringify(error || {}), retryDelayMs || 0],
    );
    if (!result.rowCount) throw new Error("Job is not owned by this worker");
    return result.rows[0];
  }

  async cancel(jobId) {
    const result = await this.pool.query(
      `UPDATE jobs SET status = 'cancelled', worker_id = NULL, updated_at = now()
       WHERE id = $1 AND status IN ('queued','running','retry_wait') RETURNING *`,
      [jobId],
    );
    if (!result.rowCount) throw new Error("Job cannot be cancelled");
    return result.rows[0];
  }

  async requeueStuck(staleBefore) {
    const result = await this.pool.query(
      `UPDATE jobs SET
         status = CASE WHEN attempt < max_attempts THEN 'retry_wait' ELSE 'failed' END,
         error = jsonb_build_object('code', 'WORKER_TIMEOUT'),
         available_at = now(), worker_id = NULL, updated_at = now()
       WHERE status = 'running' AND COALESCE(heartbeat_at, claimed_at) < $1
       RETURNING *`,
      [staleBefore],
    );
    return result.rows;
  }
}

module.exports = { JobRepository };
