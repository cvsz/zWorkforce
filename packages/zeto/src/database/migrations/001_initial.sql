CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL UNIQUE,
  permissions jsonb NOT NULL DEFAULT '[]', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE users (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), role_id uuid REFERENCES roles(id), username text NOT NULL UNIQUE,
  password_hash text NOT NULL, status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','disabled')),
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE brands (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), name text NOT NULL, niche text NOT NULL, colors jsonb NOT NULL DEFAULT '[]',
  timezone text NOT NULL DEFAULT 'UTC', status text NOT NULL DEFAULT 'active' CHECK (status IN ('active','archived')),
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX brands_status_idx ON brands(status);
CREATE TABLE brand_kits (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  voice jsonb NOT NULL DEFAULT '{}', colors jsonb NOT NULL DEFAULT '[]', fonts jsonb NOT NULL DEFAULT '[]', logo_rules jsonb NOT NULL DEFAULT '{}', version integer NOT NULL DEFAULT 1 CHECK(version > 0),
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(brand_id, version)
);
CREATE TABLE provider_credentials (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid REFERENCES brands(id) ON DELETE CASCADE, provider text NOT NULL,
  secret_ref text NOT NULL, scopes jsonb NOT NULL DEFAULT '[]', status text NOT NULL DEFAULT 'active' CHECK(status IN ('active','expired','revoked')),
  expires_at timestamptz, created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(brand_id, provider, secret_ref)
);
CREATE TABLE ideas (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  title text NOT NULL, brief text NOT NULL DEFAULT '', score numeric(5,2) CHECK(score BETWEEN 0 AND 100), status text NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','selected','generating','archived')),
  provenance jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ideas_brand_status_idx ON ideas(brand_id, status);
CREATE TABLE assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE, idea_id uuid REFERENCES ideas(id) ON DELETE SET NULL,
  type text NOT NULL CHECK(type IN ('image','video','audio','caption')), prompt_hash text NOT NULL, seed text, brand_delta_e numeric, lufs numeric, aspect_ratio text,
  tags jsonb NOT NULL DEFAULT '[]', score numeric(5,2) CHECK(score BETWEEN 0 AND 100), status text NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','review','approved','blocked','published')),
  version integer NOT NULL DEFAULT 1 CHECK(version > 0), provenance jsonb NOT NULL DEFAULT '{}', storage_key text,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(brand_id, prompt_hash, version)
);
CREATE INDEX assets_brand_status_idx ON assets(brand_id, status);
CREATE TABLE asset_variants (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), asset_id uuid NOT NULL REFERENCES assets(id) ON DELETE CASCADE, seed text,
  storage_key text, metadata jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE captions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE, asset_id uuid REFERENCES assets(id) ON DELETE SET NULL,
  platform text NOT NULL, body text NOT NULL, hook text, cta text, hashtags jsonb NOT NULL DEFAULT '[]', alt_text text, seo_description text, version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(asset_id, platform, version)
);
CREATE TABLE posts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE, caption_id uuid REFERENCES captions(id) ON DELETE SET NULL,
  asset_ids jsonb NOT NULL DEFAULT '[]', caption text NOT NULL DEFAULT '', hashtags jsonb NOT NULL DEFAULT '[]', platform text NOT NULL,
  slot timestamptz, status text NOT NULL DEFAULT 'queued' CHECK(status IN ('draft','queued','live','failed','cancelled')), permalink text NOT NULL DEFAULT '', retry_count integer NOT NULL DEFAULT 0 CHECK(retry_count >= 0),
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX posts_platform_status_slot_idx ON posts(platform, status, slot);
CREATE TABLE schedules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), post_id uuid NOT NULL REFERENCES posts(id) ON DELETE CASCADE, timezone text NOT NULL,
  slot timestamptz NOT NULL, status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','claimed','completed','cancelled','failed')),
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(post_id, slot)
);
CREATE INDEX schedules_due_idx ON schedules(status, slot);
CREATE TABLE publications (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), post_id uuid NOT NULL REFERENCES posts(id) ON DELETE CASCADE, provider text NOT NULL,
  idempotency_key text NOT NULL UNIQUE, provider_publication_id text, permalink text, status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','publishing','published','retry_wait','failed','cancelled')),
  attempt integer NOT NULL DEFAULT 0, provider_response jsonb NOT NULL DEFAULT '{}', last_error jsonb, published_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX publications_post_status_idx ON publications(post_id, status);
CREATE TABLE metrics_daily (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE, publication_id uuid REFERENCES publications(id) ON DELETE CASCADE,
  platform text NOT NULL, metric_date date NOT NULL, metrics jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(brand_id, publication_id, platform, metric_date)
);
CREATE TABLE mentions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE, platform text NOT NULL,
  external_id text NOT NULL, body text NOT NULL, classification text CHECK(classification IN ('question','complaint','praise','spam','lead')),
  occurred_at timestamptz NOT NULL, metadata jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(platform, external_id)
);
CREATE INDEX mentions_brand_occurred_idx ON mentions(brand_id, occurred_at DESC);
CREATE TABLE sentiment_scores (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), mention_id uuid NOT NULL REFERENCES mentions(id) ON DELETE CASCADE,
  score numeric(5,2) NOT NULL CHECK(score BETWEEN 0 AND 100), model text NOT NULL, rationale text,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(mention_id, model)
);
CREATE TABLE competitors (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name text NOT NULL, handles jsonb NOT NULL DEFAULT '{}', metrics jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(brand_id, name)
);
CREATE TABLE workflows (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name text NOT NULL, definition jsonb NOT NULL, version integer NOT NULL DEFAULT 1, active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(brand_id, name, version)
);
CREATE TABLE workflow_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workflow_id uuid NOT NULL REFERENCES workflows(id), status text NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','paused','succeeded','failed','cancelled')),
  input jsonb NOT NULL DEFAULT '{}', output jsonb NOT NULL DEFAULT '{}', cost numeric(14,6) NOT NULL DEFAULT 0, started_at timestamptz, finished_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX workflow_runs_status_idx ON workflow_runs(status, created_at);
CREATE TABLE workflow_steps (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workflow_run_id uuid NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
  step_key text NOT NULL, owner text NOT NULL, status text NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','retry_wait','succeeded','failed','cancelled','blocked')),
  attempt integer NOT NULL DEFAULT 0, input jsonb NOT NULL DEFAULT '{}', output jsonb NOT NULL DEFAULT '{}', error jsonb, timeout_ms integer NOT NULL DEFAULT 120000,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(workflow_run_id, step_key)
);
CREATE TABLE approvals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), asset_id uuid NOT NULL REFERENCES assets(id) ON DELETE CASCADE, actor_id uuid REFERENCES users(id) ON DELETE SET NULL,
  decision text NOT NULL CHECK(decision IN ('pending','approved','rejected','overridden')), score numeric(5,2), breakdown jsonb NOT NULL DEFAULT '{}', reasons jsonb NOT NULL DEFAULT '[]', remediation jsonb NOT NULL DEFAULT '[]',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX approvals_asset_created_idx ON approvals(asset_id, created_at DESC);
CREATE TABLE model_routes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid REFERENCES brands(id) ON DELETE CASCADE, task text NOT NULL,
  provider text NOT NULL, model text NOT NULL, priority integer NOT NULL, max_cost numeric(14,6), enabled boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), UNIQUE(brand_id, task, priority)
);
CREATE TABLE cost_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid REFERENCES brands(id) ON DELETE SET NULL, workflow_run_id uuid REFERENCES workflow_runs(id) ON DELETE SET NULL,
  provider text NOT NULL, model text NOT NULL, task text NOT NULL, input_units bigint NOT NULL DEFAULT 0, output_units bigint NOT NULL DEFAULT 0,
  estimated_cost numeric(14,6) NOT NULL DEFAULT 0, latency_ms integer, quality_score numeric(5,2), fallback_reason text,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX cost_events_brand_created_idx ON cost_events(brand_id, created_at DESC);
CREATE TABLE alerts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), brand_id uuid NOT NULL REFERENCES brands(id) ON DELETE CASCADE, type text NOT NULL,
  dedupe_key text NOT NULL, severity text NOT NULL CHECK(severity IN ('info','warning','critical')), status text NOT NULL DEFAULT 'open' CHECK(status IN ('open','acknowledged','resolved')),
  payload jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now(), resolved_at timestamptz,
  UNIQUE(brand_id, dedupe_key)
);
CREATE TABLE audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), actor_id uuid REFERENCES users(id) ON DELETE SET NULL, action text NOT NULL,
  resource_type text NOT NULL, resource_id uuid, request_id text NOT NULL, before_state jsonb, after_state jsonb,
  metadata jsonb NOT NULL DEFAULT '{}', created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX audit_events_resource_idx ON audit_events(resource_type, resource_id, created_at DESC);
CREATE INDEX audit_events_created_idx ON audit_events(created_at DESC);
CREATE TABLE idempotency_keys (
  key text PRIMARY KEY, scope text NOT NULL, request_hash text NOT NULL, response jsonb,
  resource_id uuid, created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL DEFAULT now() + interval '24 hours'
);
CREATE INDEX idempotency_keys_expires_idx ON idempotency_keys(expires_at);
CREATE TABLE jobs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(), workflow_run_id uuid REFERENCES workflow_runs(id) ON DELETE CASCADE,
  type text NOT NULL CHECK(type IN ('generate','qa','publish','monitor','report')), status text NOT NULL DEFAULT 'queued' CHECK(status IN ('queued','running','succeeded','retry_wait','failed','cancelled')),
  attempt integer NOT NULL DEFAULT 0, max_attempts integer NOT NULL DEFAULT 3 CHECK(max_attempts BETWEEN 1 AND 20), timeout_ms integer NOT NULL DEFAULT 120000,
  idempotency_key text NOT NULL UNIQUE, owner text NOT NULL, worker_id text, payload jsonb NOT NULL DEFAULT '{}', result jsonb,
  error jsonb, available_at timestamptz NOT NULL DEFAULT now(), claimed_at timestamptz, heartbeat_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(), updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX jobs_claim_idx ON jobs(status, available_at, created_at) WHERE status IN ('queued','retry_wait');

COMMENT ON TABLE audit_events IS 'Retain at least 7 years; append-only application policy';
COMMENT ON TABLE idempotency_keys IS 'Delete expired rows after response replay window';
COMMENT ON TABLE jobs IS 'Archive terminal jobs after operational retention period';
