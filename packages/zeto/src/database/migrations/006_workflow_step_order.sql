ALTER TABLE workflow_steps
  ADD COLUMN IF NOT EXISTS step_order integer;

WITH ranked AS (
  SELECT id, row_number() OVER (
    PARTITION BY workflow_run_id ORDER BY created_at, id
  ) - 1 AS ordinal
  FROM workflow_steps
)
UPDATE workflow_steps
SET step_order = ranked.ordinal
FROM ranked
WHERE workflow_steps.id = ranked.id AND workflow_steps.step_order IS NULL;

ALTER TABLE workflow_steps
  ALTER COLUMN step_order SET NOT NULL,
  ALTER COLUMN step_order SET DEFAULT 0;

ALTER TABLE workflow_steps
  ADD CONSTRAINT workflow_steps_step_order_nonnegative CHECK (step_order >= 0);

CREATE UNIQUE INDEX IF NOT EXISTS workflow_steps_run_order_idx
  ON workflow_steps(workflow_run_id, step_order);
