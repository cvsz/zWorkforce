-- M12 Z.A.R.V.I.S. operator runtime (spec §11 persistence model).
-- Sessions own a monotonic per-(session, generation) event sequence;
-- operator_events is the append-only audit stream (no UPDATE/DELETE via app code).

CREATE TABLE operator_sessions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  generation integer NOT NULL DEFAULT 1 CHECK (generation > 0),
  mode text NOT NULL CHECK (mode IN ('chat','voice','operator','automation')),
  capabilities jsonb NOT NULL DEFAULT '[]',
  state text NOT NULL DEFAULT 'IDLE' CHECK (state IN (
    'IDLE','LISTENING','TRANSCRIBING','THINKING','PLANNING','AWAITING_APPROVAL',
    'EXECUTING','VERIFYING','SPEAKING','DEGRADED','RECOVERING','REAUTHORIZING',
    'PAUSED','FAILED','CANCELLED','EMERGENCY_STOPPED'
  )),
  previous_state text,
  resume_state text,
  checkpoint_id text,
  plan_id uuid,
  step_id text,
  attempt integer NOT NULL DEFAULT 0 CHECK (attempt >= 0),
  pending_pause boolean NOT NULL DEFAULT false,
  grants_revoked boolean NOT NULL DEFAULT false,
  kill_switch_latched boolean NOT NULL DEFAULT false,
  last_sequence_id bigint NOT NULL DEFAULT 0 CHECK (last_sequence_id >= 0),
  actor_id uuid REFERENCES users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX operator_sessions_state_idx ON operator_sessions(state, created_at);

CREATE TABLE operator_commands (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES operator_sessions(id) ON DELETE CASCADE,
  correlation_id text NOT NULL,
  type text NOT NULL CHECK (type IN ('text','voice','sequence')),
  text text,
  audio_ref text,
  status text NOT NULL DEFAULT 'received'
    CHECK (status IN ('received','routing','planned','executing','completed','failed','cancelled')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX operator_commands_session_idx ON operator_commands(session_id, created_at);

CREATE TABLE operator_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id text NOT NULL UNIQUE,
  session_id uuid NOT NULL REFERENCES operator_sessions(id) ON DELETE CASCADE,
  generation integer NOT NULL CHECK (generation > 0),
  sequence_id bigint NOT NULL CHECK (sequence_id > 0),
  type text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  correlation_id text,
  payload jsonb NOT NULL DEFAULT '{}',
  UNIQUE (session_id, generation, sequence_id)
);
CREATE INDEX operator_events_replay_idx ON operator_events(session_id, generation, sequence_id);
CREATE INDEX operator_events_session_ts_type_idx ON operator_events(session_id, occurred_at, type);

CREATE TABLE operator_plans (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES operator_sessions(id) ON DELETE CASCADE,
  generation integer NOT NULL CHECK (generation > 0),
  intent text NOT NULL,
  policy_verdict text NOT NULL CHECK (policy_verdict IN ('approved','approval_required','denied')),
  estimated_cost numeric(14,6) NOT NULL DEFAULT 0 CHECK (estimated_cost >= 0),
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending','approved','rejected','executing','completed','failed','cancelled')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX operator_plans_session_idx ON operator_plans(session_id, created_at);

CREATE TABLE operator_plan_steps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  plan_id uuid NOT NULL REFERENCES operator_plans(id) ON DELETE CASCADE,
  step_key text NOT NULL,
  tool text NOT NULL,
  args jsonb NOT NULL DEFAULT '{}',
  risk text NOT NULL CHECK (risk IN ('none','low','medium','high','critical')),
  depends_on jsonb NOT NULL DEFAULT '[]',
  status text NOT NULL DEFAULT 'queued'
    CHECK (status IN ('queued','running','succeeded','failed','cancelled')),
  attempt integer NOT NULL DEFAULT 0 CHECK (attempt >= 0),
  result jsonb,
  error jsonb,
  verification text CHECK (verification IN ('passed','failed','pending')),
  idempotency_key text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (plan_id, step_key)
);

CREATE TABLE tool_executions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id uuid NOT NULL REFERENCES operator_sessions(id) ON DELETE CASCADE,
  generation integer NOT NULL CHECK (generation > 0),
  plan_id uuid REFERENCES operator_plans(id) ON DELETE SET NULL,
  step_id uuid REFERENCES operator_plan_steps(id) ON DELETE SET NULL,
  tool text NOT NULL,
  action text,
  args jsonb NOT NULL DEFAULT '{}',
  risk text,
  approval text CHECK (approval IN ('approved','denied','not_required')),
  idempotency_key text NOT NULL,
  status text NOT NULL DEFAULT 'running' CHECK (status IN ('running','succeeded','failed','cancelled')),
  response jsonb,
  duration_ms integer,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (session_id, generation, idempotency_key)
);

CREATE TABLE verification_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  step_id uuid REFERENCES operator_plan_steps(id) ON DELETE CASCADE,
  execution_id uuid REFERENCES tool_executions(id) ON DELETE CASCADE,
  status text NOT NULL CHECK (status IN ('passed','failed','pending')),
  evidence jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX verification_evidence_step_idx ON verification_evidence(step_id);

-- Mutable operational tables are audited via the shared trigger; operator_events
-- is itself the immutable audit stream and is intentionally not double-logged.
CREATE TRIGGER operator_sessions_audit AFTER INSERT OR UPDATE OR DELETE ON operator_sessions
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER operator_commands_audit AFTER INSERT OR UPDATE OR DELETE ON operator_commands
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER operator_plans_audit AFTER INSERT OR UPDATE OR DELETE ON operator_plans
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER operator_plan_steps_audit AFTER INSERT OR UPDATE OR DELETE ON operator_plan_steps
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER tool_executions_audit AFTER INSERT OR UPDATE OR DELETE ON tool_executions
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
CREATE TRIGGER verification_evidence_audit AFTER INSERT OR UPDATE OR DELETE ON verification_evidence
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
