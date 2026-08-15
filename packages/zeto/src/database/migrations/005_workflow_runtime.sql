ALTER TABLE workflow_steps
  ADD COLUMN IF NOT EXISTS max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 20),
  ADD COLUMN IF NOT EXISTS available_at timestamptz NOT NULL DEFAULT now(),
  ADD COLUMN IF NOT EXISTS worker_id text,
  ADD COLUMN IF NOT EXISTS heartbeat_at timestamptz,
  ADD COLUMN IF NOT EXISTS cost numeric(14,6) NOT NULL DEFAULT 0 CHECK (cost >= 0),
  ADD COLUMN IF NOT EXISTS idempotency_key text;

CREATE UNIQUE INDEX IF NOT EXISTS workflow_steps_idempotency_idx
  ON workflow_steps(idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS workflow_steps_claim_idx
  ON workflow_steps(workflow_run_id, status, available_at, created_at)
  WHERE status IN ('queued','retry_wait');

