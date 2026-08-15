CREATE TABLE app_settings (
  singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
  data jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE facebook_pages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  facebook_page_id text NOT NULL UNIQUE,
  name text NOT NULL,
  access_token_encrypted text,
  user_access_token_encrypted text,
  enabled boolean NOT NULL DEFAULT true,
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE publication_queue (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  page_id uuid REFERENCES facebook_pages(id) ON DELETE CASCADE,
  message text NOT NULL,
  image_url text,
  link text,
  source text,
  status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending_review','pending','publishing','published','error','cancelled')),
  provider_post_id text,
  permalink text,
  error text,
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX publication_queue_claim_idx ON publication_queue(status, created_at);
CREATE INDEX publication_queue_page_idx ON publication_queue(page_id, created_at DESC);

CREATE TABLE post_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  page_id uuid REFERENCES facebook_pages(id) ON DELETE SET NULL,
  status text NOT NULL,
  message text,
  source text,
  provider_post_id text,
  error text,
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX post_history_page_created_idx ON post_history(page_id, created_at DESC);

CREATE TABLE operational_schedules (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  page_id uuid REFERENCES facebook_pages(id) ON DELETE CASCADE,
  name text NOT NULL,
  cron text NOT NULL,
  message text NOT NULL,
  image_url text,
  enabled boolean NOT NULL DEFAULT true,
  metadata jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX operational_schedules_enabled_idx ON operational_schedules(enabled);

CREATE TABLE user_sessions (
  token_hash text PRIMARY KEY,
  user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL
);
CREATE INDEX user_sessions_expiry_idx ON user_sessions(expires_at);

COMMENT ON TABLE user_sessions IS 'Delete expired sessions continuously; raw bearer tokens are never stored';
