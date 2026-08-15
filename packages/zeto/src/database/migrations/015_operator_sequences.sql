-- M12 Z.A.R.V.I.S. Sequence Builder (spec §4.3, §9, §11).
-- Sequences are named, ordered multi-step command definitions; runs execute
-- steps sequentially with durable per-step state, scoped idempotency and
-- partial-failure resume.

CREATE TABLE operator_sequences (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  mode text NOT NULL CHECK (mode IN ('chat','operator','automation')),
  dry_run boolean NOT NULL DEFAULT false,
  created_by uuid REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX operator_sequences_created_idx ON operator_sequences(created_at DESC);

CREATE TABLE operator_sequence_steps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sequence_id uuid NOT NULL REFERENCES operator_sequences(id) ON DELETE CASCADE,
  step_key text NOT NULL,
  position integer NOT NULL CHECK (position > 0),
  intent text NOT NULL,
  args jsonb NOT NULL DEFAULT '{}',
  risk text NOT NULL DEFAULT 'none' CHECK (risk IN ('none','low','medium','high','critical')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (sequence_id, step_key),
  UNIQUE (sequence_id, position)
);

CREATE TABLE operator_sequence_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  sequence_id uuid NOT NULL REFERENCES operator_sequences(id) ON DELETE CASCADE,
  session_id uuid NOT NULL REFERENCES operator_sessions(id) ON DELETE CASCADE,
  dry_run boolean NOT NULL DEFAULT false,
  status text NOT NULL DEFAULT 'running'
    CHECK (status IN ('running','succeeded','failed','cancelled')),
  current_step text,
  error jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX operator_sequence_runs_seq_idx ON operator_sequence_runs(sequence_id, created_at DESC);
CREATE INDEX operator_sequence_runs_session_idx ON operator_sequence_runs(session_id, created_at DESC);

-- Per-step execution state. Idempotency is scoped per run: UNIQUE(run_id,
-- step_key) means replaying the same step within the same run returns the
-- stored result (the frozen idempotency contract on tool_executions applies
-- to plan-step executions; sequence run steps are scoped to their run).
CREATE TABLE operator_sequence_run_steps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id uuid NOT NULL REFERENCES operator_sequence_runs(id) ON DELETE CASCADE,
  step_key text NOT NULL,
  position integer NOT NULL CHECK (position > 0),
  intent text NOT NULL,
  args jsonb NOT NULL DEFAULT '{}',
  risk text NOT NULL DEFAULT 'none' CHECK (risk IN ('none','low','medium','high','critical')),
  status text NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
  result jsonb,
  error jsonb,
  idempotency_key text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (run_id, step_key)
);

-- Mutable operational tables are audited via the shared trigger.
CREATE TRIGGER operator_sequences_audit AFTER INSERT OR UPDATE OR DELETE ON operator_sequences
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER operator_sequence_steps_audit AFTER INSERT OR UPDATE OR DELETE ON operator_sequence_steps
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER operator_sequence_runs_audit AFTER INSERT OR UPDATE OR DELETE ON operator_sequence_runs
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER operator_sequence_run_steps_audit AFTER INSERT OR UPDATE OR DELETE ON operator_sequence_run_steps
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
