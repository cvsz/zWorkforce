from __future__ import annotations

BROWSER_EFFECT_SCHEMA_SQL = r'''
CREATE TABLE IF NOT EXISTS browser_effects3(
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(id),
    idempotency_key TEXT NOT NULL,
    action_sha256 TEXT NOT NULL,
    approval_task_id TEXT NOT NULL REFERENCES tasks2(id),
    status TEXT NOT NULL CHECK(status IN ('not_started','executing','succeeded','failed','unknown','canceled')),
    result_sha256 TEXT NOT NULL DEFAULT '',
    error_code TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT NULL,
    finished_at TEXT NULL,
    UNIQUE(tenant_id,idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_browser_effects3_tenant_status
ON browser_effects3(tenant_id,status,updated_at);
'''
