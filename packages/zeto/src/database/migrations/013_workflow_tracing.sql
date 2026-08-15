ALTER TABLE workflow_runs
  ADD COLUMN IF NOT EXISTS trace_id text;

UPDATE workflow_runs SET trace_id = replace(gen_random_uuid()::text, '-', '')
WHERE trace_id IS NULL;

ALTER TABLE workflow_runs ALTER COLUMN trace_id SET NOT NULL;
CREATE INDEX IF NOT EXISTS workflow_runs_trace_idx ON workflow_runs(trace_id);

CREATE TABLE IF NOT EXISTS workflow_spans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  trace_id text NOT NULL,
  workflow_run_id uuid NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
  workflow_step_id uuid REFERENCES workflow_steps(id) ON DELETE CASCADE,
  name text NOT NULL,
  status text NOT NULL CHECK(status IN ('running','succeeded','failed','blocked')),
  started_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  attributes jsonb NOT NULL DEFAULT '{}',
  error jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS workflow_spans_trace_idx
  ON workflow_spans(trace_id, started_at);
