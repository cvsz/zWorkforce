CREATE TABLE alert_evaluations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  brand_id uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  alert_id uuid UNIQUE REFERENCES alerts(id) ON DELETE SET NULL,
  rule_type text NOT NULL,
  dedupe_key text NOT NULL UNIQUE,
  predicted_positive boolean NOT NULL,
  actual_positive boolean,
  actor_id uuid REFERENCES users(id) ON DELETE SET NULL,
  notes text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER alert_evaluations_audit AFTER INSERT OR UPDATE OR DELETE ON alert_evaluations
FOR EACH ROW EXECUTE FUNCTION write_operational_audit();
