ALTER TABLE publication_queue DROP CONSTRAINT publication_queue_status_check;
ALTER TABLE publication_queue
  ADD CONSTRAINT publication_queue_status_check CHECK (
    status IN ('pending_review','pending','publishing','published','retry_wait','failed','error','cancelled')
  ),
  ADD COLUMN attempt integer NOT NULL DEFAULT 0 CHECK (attempt >= 0),
  ADD COLUMN max_attempts integer NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 20),
  ADD COLUMN available_at timestamptz NOT NULL DEFAULT now();

DROP INDEX publication_queue_claim_idx;
CREATE INDEX publication_queue_claim_idx ON publication_queue(status, available_at, created_at)
WHERE status IN ('pending','retry_wait');
