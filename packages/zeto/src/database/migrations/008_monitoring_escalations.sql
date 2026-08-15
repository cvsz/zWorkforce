CREATE TABLE mention_escalations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  mention_id uuid NOT NULL UNIQUE REFERENCES mentions(id) ON DELETE CASCADE,
  severity text NOT NULL CHECK (severity IN ('info','warning','critical')),
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','acknowledged','resolved')),
  reply_draft text,
  handoff text,
  due_at timestamptz NOT NULL,
  resolved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX mention_escalations_due_idx
  ON mention_escalations(status, due_at) WHERE status <> 'resolved';

