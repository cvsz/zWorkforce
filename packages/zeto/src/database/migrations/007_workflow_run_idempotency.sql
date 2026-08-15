ALTER TABLE workflow_runs ADD COLUMN IF NOT EXISTS command_key text;
CREATE UNIQUE INDEX IF NOT EXISTS workflow_runs_command_key_idx
  ON workflow_runs(command_key) WHERE command_key IS NOT NULL;

